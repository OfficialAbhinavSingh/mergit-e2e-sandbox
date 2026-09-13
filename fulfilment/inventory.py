"""What is on hand, what is promised to someone else, and what can still be sold.

Three numbers per SKU and the difference between them matters:

    on_hand    physically in the building, including units already promised
    reserved   held for a basket that has not been paid for yet
    damaged    physically present and unsellable, pending write-off

A reservation is a soft hold. It expires after `RESERVATION_TTL_SECONDS` so an abandoned
basket does not keep stock off the market forever, and the sweep that expires them is
expected to run from the same loop that accepts orders.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

#: How long a basket may hold stock before the sweep takes it back.
RESERVATION_TTL_SECONDS = 15 * 60

#: Below this many sellable units, a SKU is flagged to the replenishment report.
DEFAULT_REORDER_POINT = 25


class InventoryError(Exception):
    """An operation the stock ledger will not accept."""


class OutOfStock(InventoryError):
    """Not enough sellable units to satisfy a request."""

    def __init__(self, sku: str, wanted: int, available: int) -> None:
        super().__init__(f"{sku}: wanted {wanted}, only {available} available")
        self.sku = sku
        self.wanted = wanted
        self.available = available


@dataclass
class StockLevel:
    sku: str
    on_hand: int = 0
    reserved: int = 0
    damaged: int = 0
    reorder_point: int = DEFAULT_REORDER_POINT

    @property
    def sellable(self) -> int:
        """Units a new customer could buy right now."""
        return self.on_hand - self.reserved

    @property
    def needs_reorder(self) -> bool:
        return self.sellable <= self.reorder_point


@dataclass
class Reservation:
    """A hold on stock for one basket."""

    id: str
    sku: str
    quantity: int
    created_at: float
    basket_id: str = ""
    released: bool = False
    fulfilled: bool = False
    notes: list[str] = field(default_factory=list)

    def expires_at(self, ttl_seconds: int = RESERVATION_TTL_SECONDS) -> float:
        return self.created_at + ttl_seconds

    def is_expired(self, now: float, ttl_seconds: int = RESERVATION_TTL_SECONDS) -> bool:
        if self.released or self.fulfilled:
            return False
        return now >= self.expires_at(ttl_seconds)


class Warehouse:
    """The stock ledger for one site."""

    def __init__(self, ttl_seconds: int = RESERVATION_TTL_SECONDS) -> None:
        self._levels: dict[str, StockLevel] = {}
        self._reservations: dict[str, Reservation] = {}
        self._ttl = ttl_seconds
        self.events: list[tuple[str, str, int]] = []

    # ── Stock ────────────────────────────────────────────────────────────────

    def stock(self, sku: str) -> StockLevel:
        if sku not in self._levels:
            self._levels[sku] = StockLevel(sku=sku)
        return self._levels[sku]

    def receive(self, sku: str, quantity: int) -> StockLevel:
        """Book in a delivery."""
        if quantity < 1:
            raise InventoryError(f"{sku}: cannot receive {quantity} units")
        level = self.stock(sku)
        level.on_hand += quantity
        self.events.append(("receive", sku, quantity))
        return level

    def write_off(self, sku: str, quantity: int) -> StockLevel:
        """Move units from sellable to damaged after a breakage or a failed inspection."""
        level = self.stock(sku)
        if quantity < 1:
            raise InventoryError(f"{sku}: cannot write off {quantity} units")
        if quantity > level.on_hand:
            raise InventoryError(f"{sku}: cannot write off more than is on hand")
        level.on_hand -= quantity
        level.damaged += quantity
        self.events.append(("write_off", sku, quantity))
        return level

    def available(self, sku: str) -> int:
        """How many units a new order could take."""
        return self.stock(sku).sellable

    # ── Reservations ────────────────────────────────────────────────────────

    def reserve(self, sku: str, quantity: int, basket_id: str = "") -> Reservation:
        """Hold `quantity` units for a basket, or refuse if they are not there."""
        if quantity < 1:
            raise InventoryError(f"{sku}: cannot reserve {quantity} units")
        level = self.stock(sku)
        if quantity > level.sellable:
            raise OutOfStock(sku, quantity, level.sellable)

        reservation = Reservation(
            id=f"rsv_{uuid.uuid4().hex[:12]}",
            sku=sku,
            quantity=quantity,
            created_at=time.time(),
            basket_id=basket_id,
        )
        level.reserved += quantity
        self._reservations[reservation.id] = reservation
        self.events.append(("reserve", sku, quantity))
        return reservation

    def release(self, reservation_id: str, quantity: int | None = None) -> Reservation:
        """Give stock back, either all of it or part of it.

        Partial releases happen when a customer edits a basket down, or when a warehouse
        operator splits a consignment and only part of it ships today.
        """
        reservation = self._reservations.get(reservation_id)
        if reservation is None:
            raise InventoryError(f"no such reservation: {reservation_id}")
        if reservation.fulfilled:
            raise InventoryError(f"{reservation_id} was already fulfilled")

        # FIX: Never release more than is held
        holding = reservation.quantity
        giving_back = holding if quantity is None else min(quantity, holding)
        if giving_back < 0:
            raise InventoryError(f"cannot release negative quantity: {giving_back}")
        level = self.stock(reservation.sku)
        # Don't allow reserved to go below zero
        if giving_back > level.reserved:
            giving_back = level.reserved
        level.reserved -= giving_back
        reservation.quantity -= giving_back
        if reservation.quantity <= 0:
            reservation.released = True
        self.events.append(("release", reservation.sku, giving_back))
        return reservation

    def fulfil(self, reservation_id: str) -> Reservation:
        """Ship the held units: they leave both `reserved` and `on_hand`."""
        reservation = self._reservations.get(reservation_id)
        if reservation is None:
            raise InventoryError(f"no such reservation: {reservation_id}")
        if reservation.released:
            raise InventoryError(f"{reservation_id} was already released")
        if reservation.fulfilled:
            return reservation

        level = self.stock(reservation.sku)
        level.reserved -= reservation.quantity
        level.on_hand -= reservation.quantity
        reservation.fulfilled = True
        self.events.append(("fulfil", reservation.sku, reservation.quantity))
        return reservation

    def expire_reservations(self, now: float | None = None) -> list[str]:
        """Take back every hold whose time is up.

        Called from the accept-order loop, so it runs while other reservations are being
        created and released against the same ledger.
        """
        now = time.time() if now is None else now
        expired: list[str] = []
        for reservation_id, reservation in self._reservations.items():
            if not reservation.is_expired(now, self._ttl):
                continue
            level = self.stock(reservation.sku)
            level.reserved -= reservation.quantity
            reservation.released = True
            reservation.notes.append("expired by sweep")
            del self._reservations[reservation_id]
            expired.append(reservation_id)
            self.events.append(("expire", reservation.sku, reservation.quantity))
        return expired

    # ── Reporting helpers ───────────────────────────────────────────────────

    def reservations_for(self, basket_id: str) -> list[Reservation]:
        return [r for r in self._reservations.values()
                if r.basket_id == basket_id and not r.released]

    def needs_reorder(self) -> list[StockLevel]:
        return [level for level in self._levels.values() if level.needs_reorder]

    def snapshot(self) -> dict[str, dict[str, int]]:
        return {
            sku: {
                "on_hand": level.on_hand,
                "reserved": level.reserved,
                "damaged": level.damaged,
                "sellable": level.sellable,
            }
            for sku, level in sorted(self._levels.items())
        }

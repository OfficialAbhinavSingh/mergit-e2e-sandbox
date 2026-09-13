"""The order lifecycle, and the money attached to it.

An order moves through a small state machine. Every transition is recorded, so support
can answer "what happened to this order" from the record rather than from a log file.

    DRAFT 6 PENDING_PAYMENT 6 PAID 6 PICKING 6 SHIPPED 6 DELIVERED
                                                   6 RETURNED
                    6 EXPIRED   6 REFUNDED
                    6 CANCELLED 6 CANCELLED

Cancellation is terminal. Once an order is cancelled the warehouse has released its
stock, so there is nothing left to pick and nothing to ship.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

DRAFT = "DRAFT"
PENDING_PAYMENT = "PENDING_PAYMENT"
PAID = "PAID"
PICKING = "PICKING"
SHIPPED = "SHIPPED"
DELIVERED = "DELIVERED"
RETURNED = "RETURNED"
REFUNDED = "REFUNDED"
CANCELLED = "CANCELLED"
EXPIRED = "EXPIRED"

#: States from which nothing further can happen.
TERMINAL_STATES = (DELIVERED, REFUNDED, EXPIRED, RETURNED, CANCELLED)

_FROM_PAID = (PICKING, REFUNDED, CANCELLED)
_FROM_PICKING = (SHIPPED, CANCELLED)

#: Where an order in a given state is allowed to go next.
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    DRAFT: (PENDING_PAYMENT, CANCELLED),
    PENDING_PAYMENT: (PAID, CANCELLED, EXPIRED),
    PAID: _FROM_PAID,
    PICKING: _FROM_PICKING,
    SHIPPED: (DELIVERED, RETURNED),
    DELIVERED: (RETURNED,),
    CANCELLED: (),  # No transitions allowed from CANCELLED
    RETURNED: (REFUNDED,),
    REFUNDED: (),
    EXPIRED: (),
}


class OrderError(Exception):
    """Something the order will not accept."""


class IllegalTransition(OrderError):
    def __init__(self, order_id: str, current: str, target: str) -> None:
        super().__init__(f"{order_id}: cannot go from {current} to {target}")
        self.current = current
        self.target = target


@dataclass
class OrderLine:
    sku: str
    quantity: int
    unit_price_cents: int
    reservation_id: str = ""

    @property
    def net_cents(self) -> int:
        return self.unit_price_cents * self.quantity


@dataclass
class TransitionRecord:
    at: float
    from_state: str
    to_state: str
    reason: str = ""
    actor: str = "system"


@dataclass
class Order:
    """One customer order."""

    id: str
    customer_id: str
    lines: list[OrderLine] = field(default_factory=list)
    state: str = DRAFT
    total_cents: int = 0
    paid_cents: int = 0
    refunded_cents: int = 0
    created_at: float = field(default_factory=time.time)
    history: list[TransitionRecord] = field(default_factory=list)

    @property
    def goods_cents(self) -> int:
        return sum(line.net_cents for line in self.lines)

    @property
    def outstanding_cents(self) -> int:
        """What the customer still owes, net of anything refunded to them."""
        return self.total_cents - self.paid_cents + self.refunded_cents

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def can_go_to(self, target: str) -> bool:
        return target in ALLOWED_TRANSITIONS.get(self.state, ())

    def transition(self, target: str, reason: str = "", actor: str = "system") -> "Order":
        """Move the order to `target`, or refuse and say why."""
        if target not in ALLOWED_TRANSITIONS:
            raise OrderError(f"{self.id}: unknown state {target}")
        if not self.can_go_to(target):
            raise IllegalTransition(self.id, self.state, target)
        self.history.append(TransitionRecord(
            at=time.time(), from_state=self.state, to_state=target,
            reason=reason, actor=actor,
        ))
        self.state = target
        return self


class OrderBook:
    """Every order the service knows about."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def create(self, customer_id: str, lines: list[OrderLine], total_cents: int) -> Order:
        if not lines:
            raise OrderError("an order needs at least one line")
        if total_cents < 0:
            raise OrderError("an order total cannot be negative")
        order = Order(
            id=f"ord_{uuid.uuid4().hex[:12]}",
            customer_id=customer_id,
            lines=list(lines),
            total_cents=total_cents,
        )
        self._orders[order.id] = order
        return order

    def get(self, order_id: str) -> Order:
        try:
            return self._orders[order_id]
        except KeyError:
            raise OrderError(f"no such order: {order_id}") from None

    def take_payment(self, order_id: str, amount_cents: int) -> Order:
        """Record money in. Part payments are allowed; the order only moves on when the
        whole balance is settled."""
        order = self.get(order_id)
        if amount_cents < 1:
            raise OrderError(f"{order_id}: payment must be positive")
        if order.state not in (DRAFT, PENDING_PAYMENT):
            raise OrderError(f"{order_id}: cannot take payment in state {order.state}")
        if order.state == DRAFT:
            order.transition(PENDING_PAYMENT, reason="payment started")

        order.paid_cents += amount_cents
        if order.paid_cents >= order.total_cents:
            order.transition(PAID, reason="paid in full")
        return order

    def refund(self, order_id: str, amount_cents: int, reason: str = "") -> Order:
        """Send money back. A full refund ends the order; a partial one does not."""
        order = self.get(order_id)
        if amount_cents < 1:
            raise OrderError(f"{order_id}: refund must be positive")
        if order.paid_cents == 0:
            raise OrderError(f"{order_id}: nothing has been paid")

        order.refunded_cents += amount_cents
        if order.refunded_cents >= order.paid_cents and order.can_go_to(REFUNDED):
            order.transition(REFUNDED, reason=reason or "refunded in full")
        return order

    def cancel(self, order_id: str, reason: str = "") -> Order:
        order = self.get(order_id)
        return order.transition(CANCELLED, reason=reason or "cancelled")

    def for_customer(self, customer_id: str) -> list[Order]:
        return [o for o in self._orders.values() if o.customer_id == customer_id]

    def in_state(self, state: str) -> list[Order]:
        return [o for o in self._orders.values() if o.state == state]

    def open_orders(self) -> list[Order]:
        return [o for o in self._orders.values() if not o.is_terminal and o.state != CANCELLED]

    def __len__(self) -> int:
        return len(self._orders)

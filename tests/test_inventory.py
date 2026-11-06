"""Stock: receiving, reserving, fulfilling and writing off."""
import pytest

from fulfilment.inventory import InventoryError, OutOfStock, Warehouse


@pytest.fixture()
def warehouse():
    wh = Warehouse()
    wh.receive("WID-100", 100)
    wh.receive("GRM-010", 500)
    return wh


def test_receiving_adds_to_on_hand(warehouse):
    assert warehouse.stock("WID-100").on_hand == 100
    warehouse.receive("WID-100", 20)
    assert warehouse.stock("WID-100").on_hand == 120


def test_a_reservation_holds_stock_without_removing_it(warehouse):
    warehouse.reserve("WID-100", 10, basket_id="bsk_1")
    level = warehouse.stock("WID-100")
    assert level.on_hand == 100
    assert level.reserved == 10
    assert level.sellable == 90


def test_reserving_more_than_is_sellable_is_refused(warehouse):
    with pytest.raises(OutOfStock):
        warehouse.reserve("WID-100", 101)


def test_two_reservations_cannot_take_the_same_units(warehouse):
    warehouse.reserve("WID-100", 60)
    with pytest.raises(OutOfStock):
        warehouse.reserve("WID-100", 60)


def test_releasing_a_whole_reservation_gives_the_stock_back(warehouse):
    reservation = warehouse.reserve("WID-100", 25)
    warehouse.release(reservation.id)
    assert warehouse.available("WID-100") == 100
    assert warehouse.stock("WID-100").reserved == 0


def test_fulfilling_takes_the_units_out_of_the_building(warehouse):
    reservation = warehouse.reserve("WID-100", 15)
    warehouse.fulfil(reservation.id)
    level = warehouse.stock("WID-100")
    assert level.on_hand == 85
    assert level.reserved == 0


def test_a_fulfilled_reservation_cannot_be_released(warehouse):
    reservation = warehouse.reserve("WID-100", 5)
    warehouse.fulfil(reservation.id)
    with pytest.raises(InventoryError):
        warehouse.release(reservation.id)


def test_writing_off_moves_units_to_damaged(warehouse):
    warehouse.write_off("GRM-010", 12)
    level = warehouse.stock("GRM-010")
    assert level.on_hand == 488
    assert level.damaged == 12
    assert level.sellable == 488


def test_cannot_write_off_more_than_is_on_hand(warehouse):
    with pytest.raises(InventoryError):
        warehouse.write_off("GRM-010", 5000)


def test_reorder_flags_a_line_that_has_run_down(warehouse):
    warehouse.write_off("WID-100", 80)
    assert warehouse.stock("WID-100").needs_reorder is True
    assert "WID-100" in [level.sku for level in warehouse.needs_reorder()]


def test_reservations_are_grouped_by_basket(warehouse):
    warehouse.reserve("WID-100", 2, basket_id="bsk_7")
    warehouse.reserve("GRM-010", 3, basket_id="bsk_7")
    warehouse.reserve("GRM-010", 1, basket_id="bsk_8")
    assert len(warehouse.reservations_for("bsk_7")) == 2


def test_a_snapshot_reports_every_sku(warehouse):
    snapshot = warehouse.snapshot()
    assert set(snapshot) == {"WID-100", "GRM-010"}
    assert snapshot["WID-100"]["sellable"] == 100


def test_restore_damaged(warehouse):
    # Set up a damaged pile to restore from.
    warehouse.write_off("GRM-010", 50)
    level = warehouse.stock("GRM-010")
    assert level.on_hand == 450
    assert level.damaged == 50

    # (1) Successfully restoring damaged units to on_hand.
    restored_level = warehouse.restore_damaged("GRM-010", 20)
    assert restored_level is level
    assert level.on_hand == 470
    assert level.damaged == 30
    assert level.sellable == 470

    # The event was recorded.
    assert ("restore_damaged", "GRM-010", 20) in warehouse.events

    # (2) Raising InventoryError for zero or negative quantity.
    with pytest.raises(InventoryError):
        warehouse.restore_damaged("GRM-010", 0)
    with pytest.raises(InventoryError):
        warehouse.restore_damaged("GRM-010", -5)

    # State unchanged after failed attempts.
    assert level.on_hand == 470
    assert level.damaged == 30

    # (3) Raising InventoryError when trying to restore more units than are damaged.
    with pytest.raises(InventoryError):
        warehouse.restore_damaged("GRM-010", 31)

    # State still unchanged.
    assert level.on_hand == 470
    assert level.damaged == 30

    # (4) Restoring partial quantities when fewer damaged units exist than requested
    # should fail: write off a small batch for a fresh SKU and try to over-restore it.
    warehouse.receive("WID-100", 10)
    warehouse.write_off("WID-100", 5)
    widget_level = warehouse.stock("WID-100")
    assert widget_level.damaged == 5
    with pytest.raises(InventoryError):
        warehouse.restore_damaged("WID-100", 6)
    # Damaged count remains untouched by the failed restore.
    assert widget_level.damaged == 5
    assert widget_level.on_hand == 105

    # (5) Verifying the on_hand and damaged counts are correct after a full restoration.
    warehouse.restore_damaged("WID-100", 5)
    assert widget_level.damaged == 0
    assert widget_level.on_hand == 110
    assert widget_level.sellable == 110

    # Restoring the remaining GRM-010 damaged stock fully clears it too.
    warehouse.restore_damaged("GRM-010", 30)
    assert level.damaged == 0
    assert level.on_hand == 500
    assert level.sellable == 500

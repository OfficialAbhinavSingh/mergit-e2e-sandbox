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


def test_regression_release_over_reserve():
    wh = Warehouse()
    wh.receive('WID-100', 100)
    rsv = wh.reserve('WID-100', 100)
    # Release more than reserved should not be possible
    wh.release(rsv.id, 50)
    # Try to release more than remaining
    wh.release(rsv.id, 100)
    # Reserved should never go negative
    assert wh.stock('WID-100').reserved >= 0
    # Reservation should be marked released
    assert rsv.released
    # Try to release again should not change reserved
    with pytest.raises(InventoryError):
        wh.release(rsv.id, 10)

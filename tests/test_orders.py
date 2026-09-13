"""The order lifecycle."""
import pytest

from fulfilment.orders import (
    CANCELLED,
    DELIVERED,
    IllegalTransition,
    OrderBook,
    OrderError,
    OrderLine,
    PAID,
    PENDING_PAYMENT,
    PICKING,
    SHIPPED,
)


@pytest.fixture()
def book():
    return OrderBook()


@pytest.fixture()
def order(book):
    return book.create("cus_1", [OrderLine(sku="WID-100", quantity=2, unit_price_cents=1299)],
                       total_cents=3118)


def test_an_order_starts_as_a_draft(order):
    assert order.state == "DRAFT"
    assert order.goods_cents == 2598


def test_an_order_needs_at_least_one_line(book):
    with pytest.raises(OrderError):
        book.create("cus_1", [], total_cents=0)


def test_paying_in_full_moves_the_order_on(book, order):
    book.take_payment(order.id, 3118)
    assert order.state == PAID
    assert order.outstanding_cents == 0


def test_a_part_payment_leaves_the_order_pending(book, order):
    book.take_payment(order.id, 1000)
    assert order.state == PENDING_PAYMENT
    assert order.outstanding_cents == 2118


def test_the_happy_path_runs_to_delivered(book, order):
    book.take_payment(order.id, 3118)
    order.transition(PICKING)
    order.transition(SHIPPED)
    order.transition(DELIVERED)
    assert order.state == DELIVERED
    assert order.is_terminal is True
    assert [record.to_state for record in order.history] == [
        PENDING_PAYMENT, PAID, PICKING, SHIPPED, DELIVERED,
    ]


def test_an_order_cannot_skip_straight_to_shipped(order):
    with pytest.raises(IllegalTransition):
        order.transition(SHIPPED)


def test_a_draft_can_be_cancelled(book, order):
    book.cancel(order.id, reason="customer changed their mind")
    assert order.state == CANCELLED


def test_a_delivered_order_cannot_be_cancelled(book, order):
    book.take_payment(order.id, 3118)
    order.transition(PICKING)
    order.transition(SHIPPED)
    order.transition(DELIVERED)
    with pytest.raises(IllegalTransition):
        book.cancel(order.id)


def test_a_full_refund_ends_the_order(book, order):
    book.take_payment(order.id, 3118)
    book.refund(order.id, 3118, reason="returned faulty")
    assert order.state == "REFUNDED"


def test_refunding_something_never_paid_for_is_refused(book, order):
    with pytest.raises(OrderError):
        book.refund(order.id, 100)


def test_unknown_states_are_refused(order):
    with pytest.raises(OrderError):
        order.transition("TELEPORTED")


def test_open_orders_exclude_the_finished_ones(book):
    live = book.create("cus_1", [OrderLine("WID-100", 1, 1299)], total_cents=1299)
    done = book.create("cus_2", [OrderLine("WID-100", 1, 1299)], total_cents=1299)
    book.cancel(done.id)
    assert [o.id for o in book.open_orders()] == [live.id]

def test_cancelled_order_cannot_be_shipped_or_delivered(book, order):
    book.cancel(order.id)
    with pytest.raises(IllegalTransition):
        order.transition(SHIPPED)
    with pytest.raises(IllegalTransition):
        order.transition(DELIVERED)

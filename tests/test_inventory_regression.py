# Regression test for overselling bug in inventory.py
# This test checks that releasing more than reserved does not drive reserved negative
# and does not inflate available stock.

from fulfilment.inventory import Warehouse, InventoryError
import pytest

def test_release_more_than_reserved():
    wh = Warehouse()
    wh.receive("WID-100", 100)
    r = wh.reserve("WID-100", 10)
    # Try to release more than was reserved
    with pytest.raises(InventoryError):
        wh.release(r.id, 25)
    # Reserved should remain at 10, not go negative
    assert wh.stock("WID-100").reserved == 10
    # Available should be 90 (100 - 10)
    assert wh.available("WID-100") == 90

if __name__ == "__main__":
    # Run the test directly
    try:
        test_release_more_than_reserved()
        print("Test passed: releasing more than reserved raises InventoryError and does not oversell.")
    except AssertionError as e:
        print("Test failed:", e)
    except Exception as e:
        print("Test failed with unexpected exception:", e)

"""Statistics helpers for the Mergit end-to-end GitHub tests."""


def median(numbers):
    """Return the median of a sequence."""
    ordered = sorted(numbers)
    return ordered[len(ordered) // 2]


def spread(numbers):
    """Return the difference between the largest and smallest value."""
    if not numbers:
        return 0
    return max(numbers) - min(numbers)

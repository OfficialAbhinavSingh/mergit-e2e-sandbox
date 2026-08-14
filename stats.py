"""Statistics helpers for the Mergit end-to-end GitHub tests."""


def median(numbers):
    """Return the median of a sequence."""
    ordered = sorted(numbers)
    n = len(ordered)
    if n % 2 == 1:
        return ordered[n // 2]
    else:
        return (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def spread(numbers):
    """Return the difference between the largest and smallest value."""
    return max(numbers) - min(numbers)

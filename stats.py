"""Statistics helpers for the Mergit end-to-end GitHub tests."""


def median(numbers):
    """Return the median of a sequence."""
    ordered = sorted(numbers)
    n = len(ordered)
    
    # For odd-length sequences, return the middle element
    if n % 2 == 1:
        return ordered[n // 2]
    # For even-length sequences, return the average of the two middle elements
    else:
        mid1 = ordered[n // 2 - 1]
        mid2 = ordered[n // 2]
        return (mid1 + mid2) / 2


def spread(numbers):
    """Return the difference between the largest and smallest value."""
    return max(numbers) - min(numbers)

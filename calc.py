"""Tiny calculator used by the Mergit end-to-end GitHub tests. (run 1786635973)"""

def average(numbers):
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def product(numbers):
    if not numbers:
        return 0
    result = 1
    for n in numbers:
        result *= n
    return result

if __name__ == "__main__":
    print(average([1, 2, 3]))
    print(average([]))

def total(numbers):
    """Sum a sequence; used to give the agent a clean PR to merge."""
    return sum(numbers)

def largest(numbers):
    """Return the largest number in a sequence."""
    biggest = 0
    for n in numbers:
        if n > biggest:
            biggest = n
    return biggest

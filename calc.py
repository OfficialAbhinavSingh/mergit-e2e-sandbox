"""Tiny calculator used by the Mergit end-to-end GitHub tests. (run 1786635846)"""


def average(numbers):
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    print(average([1, 2, 3]))
    print(average([]))

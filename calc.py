"""Tiny calculator used by the Mergit end-to-end GitHub tests."""


def average(numbers):
    if len(numbers) == 0:
        raise ValueError("average() of an empty sequence")
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    print(average([1, 2, 3]))

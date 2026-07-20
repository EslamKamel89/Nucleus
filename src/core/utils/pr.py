from pprint import pprint
from typing import TypeVar

T = TypeVar("T")


def pr(value: T, title: str = "") -> T:
    line = "─" * 80

    print(f"\n┌{line}")

    if title:
        print(f"│ 📌 {title}")

    print(f"│ Type : {type(value).__name__}")

    if hasattr(value, "__len__"):
        try:
            print(f"│ Size : {len(value)}")  # type: ignore
        except TypeError:
            pass

    print(f"├{line}")

    pprint(value, sort_dicts=False)

    print(f"└{line}\n")

    return value

from typing import ClassVar, Self

class Color:
    WHITE: ClassVar[Color]
    RED: ClassVar[Color]
    BLACK: ClassVar[Color]

    r: int
    g: int
    b: int
    a: int

    def __init__(self, r: int, g: int, b: int, a: int = 0) -> None: ...
    def to_int(self) -> int: ...
    def to_ass(self) -> str: ...
    @classmethod
    def from_ass(cls, v: str) -> Self: ...

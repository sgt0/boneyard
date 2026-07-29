from datetime import timedelta
from typing import Any, ClassVar, Self

from .data import Color

__all__ = (
    "Comment",
    "Dialogue",
    "Movie",
    "Picture",
    "Sound",
    "Style",
    "Unknown",
)

class _Line:
    TYPE: ClassVar[str | None]
    DEFAULT_FIELD_ORDER: ClassVar[list[str]]

    fields: dict[str, Any]

    def __init__(
        self, *args: Any, type_name: str | None = None, **kwargs: Any
    ) -> None: ...
    def dump(self, field_order: list[str] | None = None) -> str: ...
    def dump_with_type(self, field_order: list[str] | None = None) -> str: ...
    @classmethod
    def parse(
        cls, type_name: str, line: str, field_order: list[str] | None = None
    ) -> Self: ...

class Unknown(_Line):
    value: str

class Style(_Line):
    name: str
    fontname: str
    fontsize: float
    primary_color: Color
    secondary_color: Color
    outline_color: Color
    back_color: Color
    bold: bool
    italic: bool
    underline: bool
    strike_out: bool
    scale_x: float
    scale_y: float
    spacing: float
    angle: float
    border_style: int
    outline: float
    shadow: float
    alignment: int
    margin_l: int
    margin_r: int
    margin_v: int
    encoding: int

class _Event(_Line):
    layer: int
    start: timedelta
    end: timedelta
    style: str
    name: str
    margin_l: int
    margin_r: int
    margin_v: int
    effect: str
    text: str

class Dialogue(_Event): ...
class Comment(_Event): ...
class Picture(_Event): ...
class Sound(_Event): ...
class Movie(_Event): ...
class Command(_Event): ...

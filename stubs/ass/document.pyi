from collections.abc import Iterable
from typing import IO, Any, ClassVar, Self

from .section import EventsSection, ScriptInfoSection, StylesSection

__all__ = ["Document"]

class Document:
    SCRIPT_INFO_HEADER: ClassVar[str]
    STYLE_SSA_HEADER: ClassVar[str]
    STYLE_ASS_HEADER: ClassVar[str]
    EVENTS_HEADER: ClassVar[str]
    AEGISUB_PROJECT_HEADER: ClassVar[str]

    sections: dict[str, Any]

    script_type: Any
    play_res_x: Any
    play_res_y: Any
    wrap_style: Any
    scaled_border_and_shadow: Any

    info: ScriptInfoSection
    fields: ScriptInfoSection
    styles: StylesSection
    events: EventsSection

    def __init__(self) -> None: ...
    @classmethod
    def parse_file(cls, f: Iterable[str]) -> Self: ...
    @classmethod
    def parse_string(cls, string: str) -> Self: ...
    @classmethod
    def is_preferred_encoding(cls, encoding: str) -> bool: ...
    def dump_file(self, f: IO[str]) -> None: ...

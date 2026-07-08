from collections.abc import Iterable

from . import document as document
from . import line as line
from . import section as section
from .document import Document as Document
from .line import Comment as Comment
from .line import Dialogue as Dialogue
from .line import Movie as Movie
from .line import Picture as Picture
from .line import Sound as Sound
from .line import Style as Style
from .line import Unknown as Unknown
from .section import EventsSection as EventsSection
from .section import FieldSection as FieldSection
from .section import LineSection as LineSection
from .section import ScriptInfoSection as ScriptInfoSection
from .section import StylesSection as StylesSection

def parse_file(f: Iterable[str]) -> Document: ...
def parse_string(string: str) -> Document: ...

parse = parse_file

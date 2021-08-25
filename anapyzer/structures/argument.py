from enum import IntEnum
from pydantic import Field
from typing import (
    Optional,
)

from .annotation import AnnotationStructure
from .structure import Structure


class ArgumentKind(IntEnum):
    positional = 0
    keyword = 1
    positional_or_keyword = 2
    var_positional = 3
    var_keyword = 4


class ArgumentStructure(Structure):
    name: Optional[str] = Field(None)
    type: Optional[AnnotationStructure] = Field(None)
    kind: Optional[ArgumentKind] = Field(None)
    default: Optional[str] = Field(None)
    doc: Optional[str] = Field(None)

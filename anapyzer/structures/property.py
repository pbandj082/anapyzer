import inspect
from pydantic import Field
from typing import (
    Any,
    Optional,
)

from .annotation import AnnotationStructure
from .structure import Structure


class PropertyStructure(Structure):
    name: Optional[str] = Field(None)
    type: Optional[Any] = Field(None)
    doc: Optional[str] = Field(None)

    @classmethod
    def from_type(cls, property) -> 'PropertyStructure':
        property_func = property.fget
        name = property_func.__name__
        doc = inspect.getdoc(property_func)
        signature = inspect.signature(property_func)
        property_type: Optional[AnnotationStructure] = None
        if signature.return_annotation != inspect.Signature.empty:
            property_type = AnnotationStructure.from_type(signature.return_annotation)
        return cls(name=name, type=property_type, doc=doc)

import inspect
from pydantic import Field
from typing import (
    List,
    Optional,
    get_args,
)
from .structure import Structure


class AnnotationStructure(Structure):
    name: Optional[str] = Field(None)
    subtypes: Optional[List['AnnotationStructure']] = Field(None)
    module_name: Optional[str] = Field(None)

    @classmethod
    def from_type(cls, annotation):
        AnnotationStructure.update_forward_refs()
        name: str
        module_name: Optional[str] = None
        subtypes: Optional[List['AnnotationStructure']] = None
        if isinstance(annotation, type):
            name = annotation.__name__
            module_name = inspect.getmodule(annotation).__name__
        else:
            name = str(annotation)
            typing_prefix = 'typing.'
            if name.startswith(typing_prefix):
                name = name[len(typing_prefix):]
            args = get_args(annotation)
            if args:
                subtypes = [cls.from_type(a) for a in args]
        return cls(name=name, subtypes=subtypes, module_name=module_name)


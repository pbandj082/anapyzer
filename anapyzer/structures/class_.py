import inspect
from pydantic import Field
from typing import (
    List,
    Optional,
)

from .annotation import AnnotationStructure
from .structure import Structure
from .function import FunctionStructure
from .property import PropertyStructure


class ClassStructure(Structure):
    name: Optional[str] = Field(None)
    doc: Optional[str] = Field(None)
    inheritance: Optional[List['ClassStructure']] = Field(None)
    constructors: Optional[List[FunctionStructure]] = Field(None)
    properties: Optional[List[PropertyStructure]] = Field(None)
    methods: Optional[List[FunctionStructure]]  = Field(None)
    static_methods: Optional[List[FunctionStructure]] = Field(None)
    static_properties: Optional[List[PropertyStructure]] = Field(None)
    special_methods: Optional[List[FunctionStructure]] = Field(None)
    module_name: Optional[str] = Field(None)
    
    @classmethod
    def from_type(cls, obj: type) -> 'ClassStructure':
        ClassStructure.update_forward_refs()
        name = obj.__name__
        doc = inspect.getdoc(obj)
        inheritance_types = inspect.getmro(obj)[1:]
        inheritance = []
        for inheritance_type in inheritance_types:
            if inheritance_type != object:
                inheritance.append(
                    cls(
                        name=inheritance_type.__name__,
                        module_name=inspect.getmodule(inheritance_type).__name__
                    )
                )
        attributes = inspect.classify_class_attrs(obj)
        constructors: List[FunctionStructure] = []
        properties: List[PropertyStructure] = []
        methods: List[FunctionStructure] = []
        static_methods: List[FunctionStructure] = []
        static_properties: List[PropertyStructure] = []
        special_methods: List[FunctionStructure] = []
        for attribute in attributes:
            if cls.is_private(attribute.name):
                continue
            if attribute.kind == 'property':
                try:
                    PropertyStructure.from_type(attribute.object)
                except:
                    print(f'{attribute.name} is not able to referred')
            elif attribute.kind == 'method':
                try:
                    if attribute.name == '__init__':
                        constructors.append(FunctionStructure.from_type(attribute.object))
                    else:
                        if cls.is_special(attribute.name):
                            special_methods.append(FunctionStructure.from_type(attribute.object))
                        else:
                            methods.append(FunctionStructure.from_type(attribute.object))
                except:
                    print(f'{attribute.name} is not able to referred')
            elif attribute.kind == 'class method' and hasattr(attribute.object, '__func__'):
                if not cls.is_special(attribute.name):
                    constructors.append(FunctionStructure.from_type(attribute.object.__func__))
            elif attribute.kind == 'static method' and hasattr(attribute.object, '__func__'):
                if not inspect.isbuiltin(attribute.object.__func__):
                    if not cls.is_special(attribute.name):
                        static_methods.append(FunctionStructure.from_type(attribute.object.__func__))
            else:
                if not cls.is_special(attribute.name):
                    static_property_type: AnnotationStructure
                    static_property_type = AnnotationStructure.from_type(attribute.object)
                    static_properties.append(
                        PropertyStructure(
                            name=attribute.name,
                            type=AnnotationStructure(
                                name=attribute.name,
                                type=static_property_type
                            )
                        )
                    )
        module_name = inspect.getmodule(obj).__name__
        return cls(
            name=name,
            doc=doc,
            inheritance=inheritance,
            constructors=constructors,
            properties=properties,
            methods=methods,
            static_methods=static_methods,
            static_properties=static_properties,
            special_methods=special_methods,
            module_name=module_name,
        )

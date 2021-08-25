import inspect
from pathlib import Path
from pydantic import Field
import types
from typing import (
    List,
    Tuple,
    Any,
    Optional,
)
import re

from .annotation import AnnotationStructure
from .structure import Structure
from app.services.anapyzer.structures.class_ import ClassStructure
from .function import FunctionStructure
from .property import PropertyStructure


class ModuleStructure(Structure):
    name: Optional[str] = Field(None),
    doc: Optional[str] = Field(None),
    export_classes: Optional[List[ClassStructure]] = Field(None)
    export_functions: Optional[List[FunctionStructure]] = Field(None)
    export_modules: Optional[List[FunctionStructure]] = Field(None)
    classes: Optional[List[ClassStructure]] = Field(None)
    functions: Optional[List[FunctionStructure]] = Field(None)
    modules: Optional[List['ModuleStructure']] = Field(None)
    variables: Optional[List] = Field(None)
    source: str = Field(None)
    
    @classmethod
    def from_type(cls, module: types.ModuleType) -> 'ModuleStructure':
        ModuleStructure.update_forward_refs()
        ClassStructure.update_forward_refs()
        name = module.__name__
        doc = inspect.getdoc(module)
        members = inspect.getmembers(module)
        export_classes: List[ClassStructure] = []
        export_functions: List[FunctionStructure] = []
        export_modules: List[ModuleStructure] = []
        classes: List[ClassStructure] = []
        functions: List[FunctionStructure] = []
        modules: List[ModuleStructure] = []
        variables: List[PropertyStructure] = []
        child_module_regex = re.compile(rf'{name}\.(.*)$')
        for member_name, member_type in members:
            if cls.is_private(member_name) or cls.is_special(member_name):
                continue
            if inspect.isclass(member_type):
                class_module_name = inspect.getmodule(member_type).__name__
                if name == class_module_name:
                    classes.append(ClassStructure.from_type(member_type))
                else:
                    export_classes.append(
                        ClassStructure(
                            name=member_name,
                            module_name=class_module_name
                        )
                    )
            elif inspect.isfunction(member_type):
                function_module_name = inspect.getmodule(member_type).__name__
                if name == function_module_name:
                    functions.append(FunctionStructure.from_type(member_type))
                else:
                    export_functions.append(
                        FunctionStructure(
                            name=member_name,
                            module_name=function_module_name,
                        )
                    )
            elif inspect.ismodule(member_type):
                if child_module_regex.match(member_type.__name__):
                    modules.append(cls.from_type(member_type))
                else:
                    export_modules.append(
                        cls(
                            name=member_name,
                        )
                    )
            else:
                if inspect.isroutine(member_type) and not inspect.isbuiltin(member_type):
                    functions.append(FunctionStructure.from_type(member_type))
                else:
                    variable_module_name = inspect.getmodule(type(member_type)).__name__
                    if variable_module_name != 'typing':
                        variables.append(
                            PropertyStructure(
                                name=member_name,
                                type=AnnotationStructure.from_type(type(member_type))
                            )
                        )
        path = Path(module.__file__)
        source: Optional[str] = None
        if path.name != '__init__.py' and path.suffix == '.py':
            source = inspect.getsource(module)
        return cls(
            name=name,
            doc=doc,
            classes=classes,
            functions=functions,
            modules=modules,
            source=source
        )

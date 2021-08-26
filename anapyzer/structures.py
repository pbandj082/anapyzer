from abc import ABCMeta
from pathlib import Path
import inspect
from pydantic import Field, BaseModel
from typing import (
    List,
    Optional,
    Any,
    get_args,
)
import re
from enum import IntEnum
import inspect
import types


class Structure(BaseModel, metaclass=ABCMeta):
    @staticmethod
    def is_private(target_name: str) -> bool:
        private_name_regex = re.compile(r'^_[^_].*$')
        if private_name_regex.match(target_name):
            return True
        else:
            return False

    @staticmethod
    def is_special(target_name: str) -> bool:
        special_name_regex = re.compile(r'^__.*$')
        if special_name_regex.match(target_name):
            return True
        else:
            return False


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
            name.removeprefix(typing_prefix)
            args = get_args(annotation)
            if args:
                subtypes = [cls.from_type(a) for a in args]
        return cls(name=name, subtypes=subtypes, module_name=module_name)


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


class FunctionStructure(Structure):
    name: Optional[str] = Field(None)
    doc: Optional[str] = Field(None)
    arguments: Optional[List[ArgumentStructure]] = Field(None)
    return_value: Optional[AnnotationStructure] = Field(None)
    sync: Optional[bool] = Field(None)
    module_name: str = Field(None)
    source: Optional[str] = Field(None)
    decorators: Optional[List[Any]] = Field(None)

    @classmethod
    def from_type(cls, func) -> 'FunctionStructure':
        name = func.__name__
        doc = inspect.getdoc(func)
        arg_docs = {}
        arg_doc_regex = re.compile('\s*:param\s+(.*?):\s*(.*)')
        if doc:
            m_all = arg_doc_regex.findall(doc)
            if m_all:
                for g1, g2 in m_all:
                    arg_docs[g1] = g2
        arguments = []
        return_value: Optional[AnnotationStructure] = None
        signature = inspect.signature(func)
        if signature.return_annotation != inspect.Signature.empty:
            return_value = AnnotationStructure.from_type(signature.return_annotation)
        for parameter in signature.parameters.values():
            if parameter.name == 'self' or parameter.name == 'cls':
                continue
            arg_type: Optional[AnnotationStructure] = None
            arg_kind: ArgumentKind
            arg_default: Optional[str] = None
            if parameter.annotation != inspect.Parameter.empty:
                arg_type = AnnotationStructure.from_type(parameter.annotation)
            arg_kind = cls._to_argument_kind(parameter.kind)
            if parameter.default == inspect.Parameter.empty:
                if arg_kind == ArgumentKind.var_positional:
                    arg_default = '[]'
                elif arg_kind == ArgumentKind.var_keyword:
                    arg_default = '{}'
                else:
                    arg_default = 'required'
            else:
                arg_default = str(parameter.default)
            arg_doc = arg_docs.get(parameter.name)
            arguments.append(
                ArgumentStructure(
                    name=parameter.name,
                    type=arg_type,
                    kind=arg_kind,
                    default=arg_default,
                    doc=arg_doc,
                )
            )
        sync = not inspect.iscoroutinefunction(func)
        source: Optional[str] = None
        decorators: Optional[List[str]] = None
        if inspect.isfunction(func) and name != '__new__':
            source = inspect.getsource(func)
            decorators = []
            decorator_matcher = re.compile(r'^\s*@(.*)$')
            def_matcher = re.compile(r'^\s*(async)?\s?def.*$')
            for line in source:
                decorator_match = decorator_matcher.match(line)
                def_match = def_matcher.match(line)
                if def_match:
                    break
                if def_match:
                    decorators.append(decorator_match[1])
        return cls(
            name=name,
            doc=doc,
            arguments=arguments,
            return_value=return_value,
            sync=sync,
            source=source,
            decorators=decorators,
        )

    @staticmethod
    def _to_argument_kind(kind: int):
        if kind == inspect.Parameter.POSITIONAL_ONLY:
            return ArgumentKind.positional
        elif kind == inspect.Parameter.KEYWORD_ONLY:
            return ArgumentKind.keyword
        elif kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            return ArgumentKind.positional_or_keyword
        elif kind == inspect.Parameter.VAR_POSITIONAL:
            return ArgumentKind.var_positional
        elif kind == inspect.Parameter.VAR_KEYWORD:
            return ArgumentKind.var_keyword


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
        path: Optional[Path] = None
        source: Optional[str] = None
        if hasattr(path, '__file__'):
            path = Path(module.__file__)
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

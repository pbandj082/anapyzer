import inspect
from pydantic import Field
from typing import (
    List,
    Any,
    Optional,
)
import re

from .argument import ArgumentStructure, ArgumentKind
from .annotation import AnnotationStructure
from .structure import Structure


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
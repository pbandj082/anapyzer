import pytest

from anapyzer.structures import ModuleStructure

def test_module_json():
    print(ModuleStructure.from_type(pytest).json(indent=True))

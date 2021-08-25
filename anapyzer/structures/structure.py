from abc import ABCMeta
from pydantic import BaseModel
import re

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

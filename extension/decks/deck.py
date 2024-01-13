import enum
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from extension.exceptions import SetterException

class DeckType (enum.Enum):
    bcMultiranger = 1
    bcFlow2 = 2
    bcZRanger2 = 3
    bcAI = 4
    bcLedRing = 5
    bcBuzzer = 6
    bcLighthouse4 = 7

class Deck:
    def __init__(self, type : DeckType) -> None:
        self.__type = type

    @property
    def type(self):
        return self.__type
    
    @type.setter
    def type(self, _):
        raise SetterException('type') # avoid setting the value manually
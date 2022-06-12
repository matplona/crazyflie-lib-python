from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from colorama import Fore, Style
from extension.decks.deck import Deck, DeckType
from extension.exceptions import SetterException

from extension.variables.logging_manager import LogVariableType
if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie
MAX_RANGE = 4000 # max range of action = 4 meter

console = logging.getLogger(__name__)

class MultiRanger(Deck):
    def __init__(self, ecf : ExtendedCrazyFlie, update_period_ms = 11) -> None:
        super().__init__(DeckType.bcMultiranger) #initialize super
        self.__front = MAX_RANGE+1
        self.__back = MAX_RANGE+1
        self.__right = MAX_RANGE+1
        self.__left = MAX_RANGE+1
        self.__up =  MAX_RANGE+1
        self.observable_name = "{}@multiranger".format(ecf.cf.link_uri)
        self.__ecf = ecf

        # Add observable to Manager
        self.__ecf.coordination_manager.add_observable(self.observable_name, self.get_state())

        # Logging variables declaration
        self.__ecf.logging_manager.add_variable("range", "front", update_period_ms, LogVariableType.uint16_t)
        self.__ecf.logging_manager.add_variable("range", "back", update_period_ms, LogVariableType.uint16_t)
        self.__ecf.logging_manager.add_variable("range", "right", update_period_ms, LogVariableType.uint16_t)
        self.__ecf.logging_manager.add_variable("range", "left", update_period_ms, LogVariableType.uint16_t)
        self.__ecf.logging_manager.add_variable("range", "up", update_period_ms, LogVariableType.uint16_t)
        # Set group watcher
        self.__ecf.logging_manager.set_group_watcher("range", self.__set_state)
        # Start logging
        self.__ecf.logging_manager.start_logging_group("range")
    
    def __del__(self) -> None:
        # Stop logging
        self.__ecf.logging_manager.stop_logging_group("range")

    def __set_state(self, ts, name, data) -> None:
        self.__front = data['front']
        self.__back = data['back']
        self.__right = data['right']
        self.__left = data['left']
        self.__up = data['up']
        console.debug(f'{Fore.CYAN}[^]{Style.RESET_ALL}\tMultiRange update: [{self.__front},{self.__back},{self.__right},{self.__left},{self.__up},]\t\t\t{Fore.MAGENTA}@{ts}{Style.RESET_ALL}')
        self.__ecf.coordination_manager.update_observable_state(self.observable_name, self.get_state())

    @property
    def front(self):
        return self.__front
    @front.setter
    def front(self, _):
        raise SetterException('front') # avoid setting the value manually
    
    @property
    def back(self):
        return self.__back
    @back.setter
    def back(self, _):
        raise SetterException('back') # avoid setting the value manually

    @property
    def right(self):
        return self.__right
    @right.setter
    def right(self, _):
        raise SetterException('right') # avoid setting the value manually

    @property
    def left(self):
        return self.__left
    @left.setter
    def left(self, _):
        raise SetterException('left') # avoid setting the value manually
    
    @property
    def up(self):
        return self.__up
    @up.setter
    def up(self, _):
        raise SetterException('up') # avoid setting the value manually

    def get_state(self) -> dict:
        return {
            'front':self.__front,
            'back': self.__back,
            'right': self.__right,
            'left':self.__left,
            'up': self.__up,
        }
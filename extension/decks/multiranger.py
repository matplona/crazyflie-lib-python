from __future__ import annotations
from typing import TYPE_CHECKING

from extension.variables.logging_manager import LogVariableType
if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie
MAX_RANGE = 4000 # max range of action = 4 meter

class MultiRanger:
    def __init__(self, ecf : ExtendedCrazyFlie, update_period_ms = 100) -> None:
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
        self.__ecf.coordination_manager.update_observable_state(self.observable_name, self.get_state())

    def get_front(self) -> int:
        return self.__front
    def get_back(self) -> int:
        return self.__back
    def get_left(self) -> int:
        return self.__left
    def get_right(self) -> int:
        return self.__right  
    def get_right(self) -> int:
        return self.__up
    def get_state(self) -> dict:
        return {
            'front':self.__front,
            'back': self.__back,
            'right': self.__right,
            'left':self.__left,
            'up': self.__up,
        }
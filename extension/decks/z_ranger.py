from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from colorama import Fore, Style
from extension.decks.deck import Deck, DeckType

from extension.variables.logging_manager import LogVariableType
if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie
MAX_RANGE = 4000 # max range of action = 4 meter

console = logging.getLogger(__name__)
#console.level = logging.DEBUG

class ZRanger(Deck):
    def __init__(self, ecf : ExtendedCrazyFlie, update_period_ms = 100) -> None:
        super().__init__(DeckType.bcZRanger2) #initialize super
        self.__zrange = MAX_RANGE+1
        self.__ecf = ecf
        self.observable_name = "{}@zranger".format(ecf.cf.link_uri)
        self.__contribute_to_state_estimate = self.__initialize_contribution()

        # Add observable to Manager
        self.__ecf.coordination_manager.add_observable(self.observable_name, self.get_state())

        # Parameter variables declaration
        self.__ecf.parameters_manager.add_variable("motion", "disableZrange")
        # Set watcher
        self.__ecf.parameters_manager.set_watcher("motion", "disableZrange", self.__update_contribution)

        # Logging variables declaration
        self.__ecf.logging_manager.add_variable("range", "zrange", update_period_ms, LogVariableType.uint16_t)
        # Set group watcher
        self.__ecf.logging_manager.set_variable_watcher("range", "zrange", self.__set_state)
        # Start logging
        self.__ecf.logging_manager.start_logging_variable("range", "zrange")
    
    def __del__(self) -> None:
        # Stop logging
        self.__ecf.logging_manager.stop_logging_variable("range", "zrange")

    def __set_state(self, ts, name, data) -> None:
        self.__zrange = data
        console.debug(f'{Fore.CYAN}[^]{Style.RESET_ALL}\tZRange update: {self.__zrange}\t\t\t{Fore.MAGENTA}@{ts}{Style.RESET_ALL}')
        self.__ecf.coordination_manager.update_observable_state(self.observable_name, self.get_state())

    def get_zrange(self) -> int:
        return self.__zrange
    def get_state(self) -> dict:
        return {
            'zrange':self.__zrange,
        }

    def __initialize_contribution(self) -> bool:
        return (self.__ecf.parameters_manager.get_value("motion", "disableZrange") == 0)

    @property
    def contribute_to_state_estimate(self) -> bool:
        return self.__contribute_to_state_estimate
    
    @contribute_to_state_estimate.setter
    def contribute_to_state_estimate(self, is_contributing : bool):
        value : int = 0 if is_contributing else 1
        self.__ecf.parameters_manager.set_value("motion", "disableZrange", value)

    def __update_contribution(self, ts, name, value):
        self.__contribute_to_state_estimate = (value == 0)

    # dead method
    # def keep_distance(self, callback, *args) -> int:
    #     """
    #     The drone will keep the distance from the zrange sensor inside the Action limits:
    #     The callback function will be called when the sensor reads a value outside the limits.
    #     The argument provided to the callback is the distance from the center of the range namely: ACTION_VALUE
    #     If zrange < MIN  -->  ACTION_VALUE > 0 (need to go up)
    #     If zrange > MAX  -->  ACTION_VALUE < 0 (need to go down)
    #     """
    #     def condition(zrange) -> bool:
    #         return zrange < ActionLimit.MIN or zrange > ActionLimit.MAX
    #     def action(zrange) -> None:
    #         callback((ActionLimit.CENTER - zrange), *args)
    #     return self.add_action_on_condition(action, condition)
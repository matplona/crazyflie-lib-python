from __future__ import annotations
from typing import TYPE_CHECKING
from extension.decks.z_ranger import ZRanger
from extension.exceptions import SetterException
from extension.variables.logging_manager import LogVariableType

if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie
MAX_RANGE = 4000 # max range of action = 4 meter

class FlowDeck:
    def __init__(self, ecf : ExtendedCrazyFlie, update_period_ms = 100) -> None:
        self.__zrange = ZRanger(ecf)
        self.__ecf = ecf
        self.__flow_x = 0 # measure in pixel / frame
        self.__flow_y = 0 # measure in pixel / frame
        self.contribute_to_state_estimate = self.__initialize_contribution()
        self.observable_name = "{}@flowdeck".format(ecf.cf.link_uri)

        # Add observable to Manager
        self.__ecf.coordination_manager.add_observable(self.observable_name, self.get_state())

        # Parameter variables declaration
        self.__ecf.parameters_manager.add_variable("motion", "disable")
        # Set watcher
        self.__ecf.parameters_manager.set_watcher("motion", "disable", self.__update_contribution)

        # Logging variables declaration
        self.__ecf.logging_manager.add_variable("kalman_pred", "predNX", update_period_ms, LogVariableType.float)
        self.__ecf.logging_manager.add_variable("kalman_pred", "predNY", update_period_ms, LogVariableType.float)
        # Set group watcher
        self.__ecf.logging_manager.set_group_watcher("kalman_pred", self.__set_state)
        # Start logging
        self.__ecf.logging_manager.start_logging_group("kalman_pred")
    
    def __del__(self) -> None:
        # Stop logging
        self.__ecf.logging_manager.stop_logging_group("kalman_pred")

    def __set_state(self, ts, name, data) -> None:
        self.__flow_x = data['predNX']
        self.__flow_y = data['predNY']
        self.__ecf.coordination_manager.update_observable_state(self.observable_name, self.get_state())

    @property
    def zrange(self):
        return self.__zrange
    @zrange.setter
    def zrange(self, _):
        raise SetterException('zrange') # avoid setting the value manually
    
    @property
    def flow_x(self):
        return self.__flow_x
    @flow_x.setter
    def flow_x(self, _):
        raise SetterException('flow_x') # avoid setting the value manually

    @property
    def flow_y(self):
        return self.__flow_y
    @flow_y.setter
    def flow_y(self, _):
        raise SetterException('flow_y') # avoid setting the value manually

    def get_state(self) -> dict:
        return {
            'flow_x':self.__flow_x,
            'flow_y':self.__flow_y,
            'zranger':self.__zrange.get_state(),
        }

    def __initialize_contribution(self) -> bool:
        return (self.__ecf.parameters_manager.get_value("motion", "disable") == 0)

    @property
    def contribute_to_state_estimate(self) -> bool:
        return self.__contribute_to_state_estimate
    
    @contribute_to_state_estimate.setter
    def contribute_to_state_estimate(self, is_contributing : bool):
        value : int = 0 if is_contributing else 1
        self.__ecf.parameters_manager.set_value("motion", "disable", value)

    def __update_contribution(self, ts, name, value):
        self.__contribute_to_state_estimate = (value == 0)

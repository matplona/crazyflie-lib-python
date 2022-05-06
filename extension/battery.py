from __future__ import annotations
from typing import TYPE_CHECKING

from colorama import Fore, Style
if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie

from enum import Enum
from extension.exceptions import SetterException
from extension.variables.logging_manager import LogVariableType

MAX_VOLTAGE = 5.0 #TODO verify
MIN_VOLTAGE = 2.8

class PowerManagementState(Enum):
    battery = 0
    charging = 1
    charged = 2
    low_power = 3
    shutdown = 4

class Battery:
    __low_voltage = MIN_VOLTAGE
    __full_voltage = MAX_VOLTAGE
    __voltage = __full_voltage
    __battery_level = 100.0
    __pm_state = PowerManagementState.battery.value

    def __init__(self, ecf : ExtendedCrazyFlie) -> None:
        # start logging battery every seconds
        ecf.logging_manager.add_variable('pm','vbatMV', 1000, LogVariableType.uint16_t)
        ecf.logging_manager.add_variable('pm','state', 1000, LogVariableType.int8_t)
        ecf.logging_manager.set_group_watcher('pm', self.__update_battery)
        self.observable_name = "{}@battery".format(ecf.cf.link_uri)
        self.__ecf = ecf
        self.__ecf.coordination_manager.add_observable(self.observable_name, self.__get_state)
        ecf.logging_manager.start_logging_group('pm')
    
    def __del__(self):
        self.__ecf.logging_manager.stop_logging_group('pm')

    # callback for update battery state
    def __update_battery(self, ts, name, data):
        self.__pm_state = data['state']
        self.__voltage = data['vbatMV']/1000
        self.__set_battery_level()
        self.__ecf.coordination_manager.update_observable_state(self.observable_name, self.__get_state)
    
    @property
    def low_voltage(self):
        return self.__low_voltage
    @property
    def full_voltage(self):
        return self.__full_voltage
    @property
    def voltage(self):
        return self.__voltage
    @property
    def battery_level(self):
        return self.__battery_level
    @property
    def pm_state(self):
        return PowerManagementState(self.__pm_state)
    #properties are read_only
    @low_voltage.setter
    def low_voltage(self, _):
        raise SetterException('low_voltage')
    @full_voltage.setter
    def full_voltage(self, _):
        raise SetterException('full_voltage')
    @voltage.setter
    def voltage(self, _):
        raise SetterException('voltage')
    @battery_level.setter
    def battery_level(self, _):
        raise SetterException('battery_level')
    @pm_state.setter
    def pm_state(self, _):
        raise SetterException('pm_state')

    def __set_battery_level(self) -> None:
        # 100 : x = (__full_voltage - __low_voltage) : (__voltage - __low_voltage)
        self.__battery_level = round((self.__voltage - self.__low_voltage) * 100 / (self.__full_voltage - self.__low_voltage), 2)

    def __get_state(self) -> dict:
        return {
            'pm_state': PowerManagementState(self.__pm_state),
            'voltage': self.__voltage,
            'battery_level': self.__battery_level
        }
    def print_state(self):
        def console_level_color(level):
            if level < 30: return f'{Fore.RED}{level} %{Style.RESET_ALL}'
            if level < 60: return f'{Fore.YELLOW}{level} %{Style.RESET_ALL}'
            return f'{Fore.GREEN}{level} %{Style.RESET_ALL}'
        print(f'{Fore.BLUE}BATTERY{Style.RESET_ALL}: {self.pm_state.name} - {console_level_color(self.battery_level)} ({round(self.voltage,2)} V)')
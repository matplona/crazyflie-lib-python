from enum import Enum
from extension.extended_crazyflie import ExtendedCrazyFlie

MAX_VOLTAGE = 5.0
MIN_VOLTAGE = 2.7

class PowerManagementState(Enum):
    battery = 0,
    charging = 1,
    charged = 2,
    low_power = 3,
    shutdown = 4,

class Battery:
    __low_voltage = MIN_VOLTAGE
    __full_voltage = MAX_VOLTAGE
    __voltage = __full_voltage
    __battery_level = 100.0
    __pm_state = PowerManagementState.battery.value

    def __init__(self, ecf : ExtendedCrazyFlie) -> None:
        # start logging battery level every 10 seconds
        ecf.logging_manager.add_variable('pm','vbat', 10000,'float')
        ecf.logging_manager.add_variable('pm','state', 10000, 'int8_t')
        ecf.logging_manager.set_group_watcher('pm', self.__update_battery)
        self.observable_name = "{}@battery".format(ecf.cf.link_uri)
        self.__ecf = ecf
        self.__ecf.coordination_manager.add_observable(self.get_battery_status())
        ecf.logging_manager.start_logging_group('pm')
    
    def __del__(self):
        self.__ecf.logging_manager.stop_logging_group('pm')

    # callback for update battery state
    def __update_battery(self, ts, name, data):
        self.__pm_state = data['state']
        self.__voltage = data['vbat']
        self.__set_battery_level()
        self.__ecf.coordination_manager.update_observable_state(self.observable_name, self.get_battery_status())
    
    def __set_battery_level(self):
        # 100 : x = (__full_voltage - __low_voltage) : (__voltage - __low_voltage)
        return round((self.__voltage - self.__low_voltage) * 100 / (self.__full_voltage - self.__low_voltage), 2)

    def get_low_voltage(self) -> float:
        return self.__low_voltage
    def get_full_voltage(self) -> float:
        return self.__full_voltage
    def get_pm_state(self) -> PowerManagementState:
        return PowerManagementState(self.__battery_level)
    def get_voltage(self) -> float:
        return self.__voltage
    def get_battery_level(self) -> float:
        return self.__battery_level
    def get_battery_status(self):
        return {
            'pm_state': self.__pm_state,
            'voltage': self.__voltage,
            'battery_level': self.__battery_level
        }
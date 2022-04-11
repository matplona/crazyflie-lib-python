from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from extension.variables.variables import Logger
from extension.coordination.coordination_manager import CoordinationManager

MAX_RANGE = 4000 # max range of action = 4 meter

class MultiRanger:
    def __init__(self, scf : SyncCrazyflie, update_period_ms = 100) -> None:
        self.__front = MAX_RANGE+1
        self.__back = MAX_RANGE+1
        self.__right = MAX_RANGE+1
        self.__left = MAX_RANGE+1
        self.__up =  MAX_RANGE+1
        self.observable_name  = "{}@multiranger".format(scf.cf.link_uri),
        self.__logger = Logger.getInstance(scf)
        self.__manager = CoordinationManager.getInstance()

        # Add observable to Manager
        self.__manager.add_observable(self.observable_name, self.get_state)

        # Logging variables declaration
        self.__logger.add_variable("range", "front", update_period_ms, "uint16_t")
        self.__logger.add_variable("range", "back", update_period_ms, "uint16_t")
        self.__logger.add_variable("range", "right", update_period_ms, "uint16_t")
        self.__logger.add_variable("range", "left", update_period_ms, "uint16_t")
        self.__logger.add_variable("range", "up", update_period_ms, "uint16_t")
        # Set group watcher
        self.__logger.set_group_watcher("range", self.__set_state)
        # Start logging
        self.__logger.start_logging_group("range")
    
    def __del__(self) -> None:
        # Stop logging
        self.__logger.stop_logging_group("range")

    def __set_state(self, ts, name, data) -> None:
        self.__front = data['front']
        self.__back = data['back']
        self.__right = data['right']
        self.__left = data['left']
        self.__up = data['up']
        self.__manager.update_observable_state(self.observable_name, data)

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
from extension.extended_crazyflie import ExtendedCrazyFlie
from extension.coordination.coordination_manager import CoordinationManager

MAX_RANGE = 4000 # max range of action = 4 meter

class ZRanger:
    def __init__(self, ecf : ExtendedCrazyFlie, update_period_ms = 100) -> None:
        self.__zrange = MAX_RANGE+1
        self.observable_name = "{}@zranger".format(ecf.cf.link_uri),
        self.__ecf = ecf

        # Add observable to Manager
        self.__ecf.coordination_manager.add_observable(self.observable_name, self.get_state())

        # Logging variables declaration
        self.__ecf.logging_manager.add_variable("range", "zrange", update_period_ms, "uint16_t")
        # Set group watcher
        self.__ecf.logging_manager.set_variable_watcher("range", "zrange", self.__set_state)
        # Start logging
        self.__ecf.logging_manager.start_logging_variable("range", "zrange")
    
    def __del__(self) -> None:
        # Stop logging
        self.__ecf.logging_manager.stop_logging_variable("range", "zrange")

    def __set_state(self, ts, name, data) -> None:
        self.__zrange = data['zrange']
        self.__ecf.coordination_manager.update_observable_state(self.observable_name, self.get_state())

    def get_zrange(self) -> int:
        return self.__zrange
    def get_state(self) -> dict:
        return {
            'zrange':self.__zrange,
        }
    
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
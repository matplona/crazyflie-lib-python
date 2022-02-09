from extension.variables.variables import Logger

class ActionLimit():
    #measure unit millimeters
    MIN = 0.5 * 1000
    MAX = 1 * 1000
    CENTER = (MAX + MIN)/2

class VelocityLimit():
    #measure unit meters/second
    MIN = 0
    MAX = 2

class ZRanger:
    def __init__(self, scf, update_period_ms = 500) -> None:
        self.__zrange = ActionLimit.CENTER
        self.__logger = Logger.getInstance(scf)
        self.__conditions_actions = []
        # Logging zrange sensor
        self.__logger.add_variable("range", "zrange", update_period_ms, "uint16_t")
        self.__logger.set_watcher("range", "zrange", self.__set_zrange)
    
        self.__logger.start_logging_group("range")
    
    def __del__(self) -> None:
        self.__logger.stop_logging_group("range")

    def __set_zrange(self, ts, name, value) -> None:
        self.__zrange = value
        self.__call_condition_action() # update observers

    def get_zrange(self) -> int:
        return self.__zrange

    def add_action_on_condition(self, action, condition) -> int:
        """
        This method will add an action function that will be called if the condition fuction returns true.
        The condition will be called with 1 parameters (zrange) and must return a bool
        The action will be called with 1 arguments (zrange) and should return None
        This will be fired every time the zrange sensor receive a new value.
        """
        self.__conditions_actions.append({
            'condition' : condition,
            'action' : action,
        })
        return len(self.__conditions_actions) - 1

    def __call_condition_action(self):
        for c_a in self.__conditions_actions:
            if(c_a["condition"](self.__zrange)):
                c_a["action"](self.__zrange)


    def stop_action(self, index : int) -> None: 
        self.__conditions_actions.pop(index)

    def keep_distance(self, callback, *args) -> int:
        """
        The drone will keep the distance from the zrange sensor inside the Action limits:
        The callback function will be called when the sensor reads a value outside the limits.
        The argument provided to the callback is the distance from the center of the range namely: ACTION_VALUE
        If zrange < MIN  -->  ACTION_VALUE > 0 (need to go up)
        If zrange > MAX  -->  ACTION_VALUE < 0 (need to go down)
        """
        def condition(zrange) -> bool:
            return zrange < ActionLimit.MIN or zrange > ActionLimit.MAX
        def action(zrange) -> None:
            callback((ActionLimit.CENTER - zrange), *args)
        return self.add_action_on_condition(action, condition)
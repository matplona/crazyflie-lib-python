from extension.variables.variables import Logger

class ActionLimit():
    #measure unit millimeters
    MIN = 500
    MAX = 1000

class VelocityLimit():
    #measure unit meters/second
    MIN = 0
    MAX = 2

class MultiRanger:
    def __init__(self, scf, update_period_ms = 100) -> None:
        self.__front = ActionLimit.MAX+1
        self.__back = ActionLimit.MAX+1
        self.__right = ActionLimit.MAX+1
        self.__left = ActionLimit.MAX+1
        self.__up =  ActionLimit.MAX+1
        self.__logger = Logger.getInstance(scf)
        self.__conditions_actions = []
        # Logging front sensor
        self.__logger.add_variable("range", "front", update_period_ms, "uint16_t")
        self.__logger.set_watcher("range", "front", self.__set_front)
        # Logging back sensor
        self.__logger.add_variable("range", "back", update_period_ms, "uint16_t")
        self.__logger.set_watcher("range", "back", self.__set_back)
        # Logging right sensor
        self.__logger.add_variable("range", "right", update_period_ms, "uint16_t")
        self.__logger.set_watcher("range", "right", self.__set_right)
        # Logging left sensor
        self.__logger.add_variable("range", "left", update_period_ms, "uint16_t")
        self.__logger.set_watcher("range", "left", self.__set_left)
        # Logging up sensor
        self.__logger.add_variable("range", "up", update_period_ms, "uint16_t")
        self.__logger.set_watcher("range", "up", self.__set_up)

        self.__logger.start_logging_group("range")
    
    def __del__(self) -> None:
        self.__logger.stop_logging_group("range")

    def __set_front(self, ts, name, value) -> None:
        self.__front = value
        self.__call_condition_action() # update observers
    def __set_back(self, ts, name, value) -> None:
        self.__back = value
        self.__call_condition_action() # update observers
    def __set_left(self, ts, name, value) -> None:
        self.__left = value
        self.__call_condition_action() # update observers
    def __set_right(self, ts, name, value) -> None:
        self.__right = value
        self.__call_condition_action() # update observers
    def __set_up(self, ts, name, value) -> None:
        self.__up = value
        self.__call_condition_action() # update observers

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

    def add_action_on_condition(self, action, condition) -> int:
        """
        This method will add an action function that will be called if the condition fuction returns true.
        The condition will be called with 5 parameters respectively (front, back, left, right, up) and must return a bool
        The action will be called with 5 arguments respectively (front, back, left, right, up) and should return None
        This will be fired every time one of the 5 sensors receive a new value.
        """
        self.__conditions_actions.append({
            'condition' : condition,
            'action' : action,
        })
        return len(self.__conditions_actions) - 1

    def __call_condition_action(self):
        for c_a in self.__conditions_actions:
            if(c_a["condition"](self.__front, self.__back, self.__left, self.__right, self.__up)):
                c_a["action"](self.__front, self.__back, self.__left, self.__right, self.__up)


    def __compute_velocity(self, value) -> float:
        #fixing values in the range (0, ACTION_LIMIT)
        value = ActionLimit.MIN if value < ActionLimit.MIN else value
        value = ActionLimit.MAX if value > ActionLimit.MAX else value
        # inverse rescaling from the interval (0, 100mm) to (0, 1m/s)
        # if the sensor get 100mm or more the velocity would be 0m/s
        # if the sensor get 0mm the velocity would be 1m/s
        # if the sensor get a value between 0 and 100 mm the velocity would be a value between 0 and 1 m/s
        # NewValue = (((OldValue - OldMin) * (NewMax - NewMin)) / (OldMax - OldMin)) + NewMin where:
            # OldValue = range_in_mm
            # NewValue = velocity_in_ms
            # OldMin = ActionLimit.MAX (range)
            # OldMax = ActionLimit.MIN (range)
            # NewMin = VelocityLimit.MIN (velocity)
            # NewMax = VelocityLimit.MAX (velocity)
        # NOTICE: we inverted the ActionLimits to get the inverted range conversion
        return (((value - ActionLimit.MAX) * (VelocityLimit.MAX - VelocityLimit.MIN)) / (ActionLimit.MIN - ActionLimit.MAX)) + VelocityLimit.MIN

    def get_vx(self)-> float:
        vx = 0
        if(ActionLimit.MIN <= self.__back <= ActionLimit.MAX):
            #back gives a push in the positive x direction
            vx += self.__compute_velocity(self.__back)
        if(ActionLimit.MIN <= self.__front <= ActionLimit.MAX):
            #back gives a push in the negative x direction
            vx -= self.__compute_velocity(self.__front)
        return vx
    def get_vy(self)-> float:
        vy = 0
        if(ActionLimit.MIN <= self.__right <= ActionLimit.MAX):
            #back gives a push in the positive y direction
            vy += self.__compute_velocity(self.__right)
        if(ActionLimit.MIN <= self.__left <= ActionLimit.MAX):
            #back gives a push in the negative y direction
            vy -= self.__compute_velocity(self.__left)
        return vy
    


    def avoid_obstacle(self, distance_mm : float, callback, *args) -> int:
        """
        If an obstacle is detected around the crazyflie in the distance provided,
        the callback function is called with all the arguments provided. Notice that 
        This callback is continously called and don't stop after the first call.
        """
        def condition(front, back, left, right, up) -> bool:
            return  front <= distance_mm or back <= distance_mm or left <= distance_mm or right <= distance_mm or up <= distance_mm
        def action(front, back, left, right, up) -> None:
            callback(front, back, left, right, up, *args)

        return self.add_action_on_condition(action, condition)

    def fly_away(self, callback, *args) -> int:
        def condition(*_) -> bool:
            return True
        def action(*_) -> None:
            callback(self.get_vx(), self.get_vy(), *args)
        return self.add_action_on_condition(action, condition)
    
    def stop_action(self, index : int) -> None: 
        self.__conditions_actions.pop(index)

    def follow_me(self, callback, *args) -> int:
        def condition(*_) -> bool:
            return True
        def action(*_) -> None:
            callback(self.get_vx()*-1, self.get_vy()*-1, *args)
        return self.add_action_on_condition(action, condition)
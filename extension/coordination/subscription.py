from coordination import Action # import Action Type
from coordination import Condition # import Codition Type

class Subscription:
    def __init__(self, action : Action, condition : Condition, parameters : list) -> None:
        self.__action : Action = action
        self.__condition : Condition = condition
        self.__parameters : list = parameters
    
    def update_subscriber(self, new_state : dict) -> None:
        #if the condition is true on the new state
        if self.__condition(new_state) :
            # callback the subscriber with the new state and the additional parameters
            self.__action(new_state, self.__parameters)

    def set_condition(self, condition : Condition) -> None:
        self.__condition = condition
    
    def set_action(self, action : Action) -> None:
        self.__action = action

    def set_parameters(self, parameters : list) -> None:
        self.__parameters = parameters
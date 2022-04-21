from typing import Any
from extension.coordination import Action # import Action Type
from extension.coordination import Condition # import Codition Type

class Observer:
    def __init__(self, action : Action, condition : Condition, context : list) -> None:
        self.__action : Action = action
        self.__condition : Condition = condition
        self.__context : list = context
    
    def notify(self, new_state : dict) -> None:
        #if the condition is true on the new state
        if self.__condition(new_state) :
            # callback the observer with the new state and its context
            self.__action(new_state, *self.__context)

    def set_condition(self, condition : Condition) -> None:
        self.__condition = condition
    
    def set_action(self, action : Action) -> None:
        self.__action = action

    def set_context(self, context : Any) -> None:
        self.__context = context
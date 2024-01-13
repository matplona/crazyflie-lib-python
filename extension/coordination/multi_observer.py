from typing import Callable
from extension.coordination import Action, MultiCondition # import Action Type
from extension.coordination.observer import Observer # import Codition Type

class MultiObserver(Observer):
    def __init__(self, action : Action, condition : MultiCondition, context : list, observable_getters: dict[str, Callable[[str], dict]]) -> None:
        self.__action : Action = action
        self.__condition : MultiCondition = condition
        self.__context : list = context
        self.__observable_getters: dict[str, Callable[[str], dict]] = observable_getters
    
    def notify(self, _ ) -> None:
        complete_state = []
        for name, getter in self.__observable_getters.items():
            complete_state.append(getter(name))
        #if the condition is true on the new state
        if self.__condition(complete_state):
            # callback the observer with the new state and its context
            self.__action(complete_state, *self.__context)
from threading import Event
from typing import Callable
from extension.coordination import Action, MultiCondition # import Action Type
from extension.coordination import Condition
from extension.coordination.multi_observer import MultiObserver # import Codition Type
from extension.coordination.observable import Observable
from extension.coordination.observer import Observer

class CoordinationManager:
    __instance = None

    @staticmethod
    def getInstance() :
        """call this method to get the right instance of the CoordinationManager"""
        if CoordinationManager.__instance == None:
            CoordinationManager.__instance = CoordinationManager()
        return CoordinationManager.__instance

    def __init__(self) -> None:
        if self.__instance == None :
            # initialize correctly the instance
            self.__observables : dict[str, Observable] = {}
        else:
            raise Exception("This is not the right way to get an Instance, please call the static method getInstance()")
    
    def add_observable(self, observable_name : str, initial_state : dict) -> None:
        # check that the name not clashes
        if observable_name not in self.__observables:
            # add a new observable in the map
            self.__observables[observable_name] = Observable(initial_state)
        else:
            raise Exception('Observable "{}" already exist!'.format(observable_name))
    
    def remove_observable(self, observable_name : str) -> dict:
        # check that the observable exist
        if observable_name in self.__observables:
            # remove observable and return its last state 
            return self.__observables.pop(observable_name)
        else:
            raise Exception('Observable "{}" doesn\' exist!'.format(observable_name))
    
    def remove_all_observables(self) -> dict:
        self.__observables.clear()

    def get_observable_state(self, observable_name: str) -> dict:
        if observable_name in self.__observables :
            return self.__observables[observable_name].get_state()
        else:
            raise Exception('Observable "{}" doesn\'t exist!'.format(observable_name))

    def update_observable_state(self, observable_name : str, new_state : dict) -> None:
        if observable_name in self.__observables :
            self.__observables[observable_name].update_observable_state(new_state)
        else:
            raise Exception('Observable "{}" doesn\'t exist!'.format(observable_name))

    def observe(self, observable_name : str, action : Action, condition : Condition = lambda *_ : True, context : list = []):
        if observable_name in self.__observables :
            obs = Observer(action, condition, context)
            self.__observables[observable_name].add_observer(obs)
        else:
            raise Exception('Observable "{}" doesn\'t exist!'.format(observable_name))
    

    def multi_observe(self, observable_names : list[str], action : Action, condition : MultiCondition = lambda *_ : True, context : list = []):
        observable_getters : dict[str, Callable[[str], dict]] = {} 
        for observable_name in observable_names:
            if observable_name in self.__observables :
                observable_getters[observable_name] = lambda name: self.get_observable_state(name)
            else:
                raise Exception('Observable "{}" doesn\'t exist!'.format(observable_name))
        for observable_name in observable_names:
            obs = MultiObserver(action, condition, context, observable_getters)
            self.__observables[observable_name].add_observer(obs)

    def observe_and_wait(self, observable_name : str, condition : Condition) -> Event:
        if observable_name in self.__observables :
            e : Event = Event()
            obs = Observer(lambda _ : e.set(), condition, [])
            self.__observables[observable_name].add_observer(obs)
            return e
        else:
            raise Exception('Observable "{}" doesn\'t exist!'.format(observable_name))
        
    def multi_observe_and_wait(self, observable_names : list[str], condition : MultiCondition) -> Event:
        observable_getters : dict[str, Callable[[str], dict]] = {} 
        for observable_name in observable_names:
            if observable_name in self.__observables :
                observable_getters[observable_name] = lambda name: self.get_observable_state(name)
            else:
                raise Exception('Observable "{}" doesn\'t exist!'.format(observable_name))
        for observable_name in observable_names:
            e : Event = Event()
            obs = MultiObserver(lambda _ : e.set(), condition, [])
            self.__observables[observable_name].add_observer(obs)
            return e
        else:
            raise Exception('Observable "{}" doesn\'t exist!'.format(observable_name))
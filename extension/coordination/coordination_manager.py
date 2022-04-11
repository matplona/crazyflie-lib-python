from threading import Event
from coordination import Action # import Action Type
from coordination import Condition # import Codition Type
from coordination.observable import Observable
from coordination.observer import Observer

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
            self.__observables : dict[str, Observable] = []
        else:
            raise("This is not the right way to get an Instance, please call the static method getInstance()")
    
    def add_observable(self, observable_name : str, initial_state : dict) -> None:
        # check that the name not clashes
        if observable_name not in self.__observables:
            # add a new observable in the map
            self.__observable[observable_name] = Observable(initial_state)
        else:
            raise('Observable "{}" already exist!'.format(observable_name))
    
    def remove_observable(self, observable_name : str) -> dict:
        # check that the observable exist
        if observable_name in self.__observables:
            # remove observable and return its last state 
            return self.__observable.pop(observable_name)
        else:
            raise('Observable "{}" doesn\' exist!'.format(observable_name))
    
    def get_observable_state(self, observable_name: str):
        if observable_name in self.__observables :
            self.__observables[observable_name].get_state()
        else:
            raise('Observable "{}" doesn\'t exist!'.format(observable_name))

    def update_observable_state(self, observable_name : str, new_state : dict) -> None:
        if observable_name in self.__observables :
            self.__observables[observable_name].update_observable_state(new_state)
        else:
            raise('Observable "{}" doesn\'t exist!'.format(observable_name))

    def observe(self, observable_name : str, action : Action, condition : Condition = lambda *_ : True, context : list = []):
        if observable_name in self.__observables :
            obs = Observer(action, condition, context)
            self.__observables[observable_name].add_observer(obs)
        else:
            raise('Observable "{}" doesn\'t exist!'.format(observable_name))
    
    def observe_and_wait(self, observable_name : str, condition : Condition) -> Event:
        if observable_name in self.__observables :
            e : Event = Event()
            obs = Observer(lambda _ : e.set(), condition, None)
            self.__observables[observable_name].add_observer(obs)
            return e
        else:
            raise('Observable "{}" doesn\'t exist!'.format(observable_name))
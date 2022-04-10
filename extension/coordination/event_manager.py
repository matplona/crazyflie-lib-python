from coordination import Action # import Action Type
from coordination import Condition # import Codition Type
from coordination.event import Event
from coordination.observer import Observer

class EventManager:
    __instance = None

    @staticmethod
    def getInstance() :
        """call this method to get the right instance of the EventManager"""
        if EventManager.__instance == None:
            EventManager.__instance = EventManager()
        return EventManager.__instance

    def __init__(self) -> None:
        if self.__instance == None :
            # initialize correctly the instance
            self.__events : dict[str, Event] = []
        else:
            raise("This is not the right way to get an Instance, please call the static method getInstance()")
    
    def add_event(self, event_name : str, initial_state : dict) -> None:
        # check that the name not clashes
        if event_name not in self.__events:
            # add a new event in the map
            self.__event[event_name] = Event(initial_state)
        else:
            raise('Event "{}" already exist!'.format(event_name))
    
    def remove_event(self, event_name : str) -> dict:
        # check that the event exist
        if event_name in self.__events:
            # remove event and return its last state 
            return self.__event.pop(event_name)
        else:
            raise('Event "{}" doesn\' exist!'.format(event_name))
    
    def get_event_state(self, event_name: str):
        if event_name in self.__events :
            self.__events[event_name].get_state()
        else:
            raise('Event "{}" doesn\'t exist!'.format(event_name))

    def update_event_state(self, event_name : str, new_state : dict) -> None:
        if event_name in self.__events :
            self.__events[event_name].update_event_state(new_state)
        else:
            raise('Event "{}" doesn\'t exist!'.format(event_name))

    def observe(self, event_name : str, action : Action, condition : Condition = lambda *_ : True, context : list = []):
        if event_name in self.__events :
            obs = Observer(action, condition, context)
            self.__events[event_name].add_observer(obs)
        else:
            raise('Event "{}" doesn\'t exist!'.format(event_name))
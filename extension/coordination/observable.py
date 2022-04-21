from extension.coordination.observer import Observer

class Observable:
    def __init__(self, initial_state : dict) -> None:
        self.__state : dict = initial_state
        self.__observer : list[Observer]  = []

    def add_observer(self, observer : Observer) -> None:
        self.__observer.append(observer)

    def update_observable_state(self, new_state : dict) -> None:
        # quick check if domain is consistent
        if self.__state.keys() == new_state.keys():
            self.__state = new_state
            # notify observer of the change
            for s in self.__observer:
                s.notify(self.__state)
    
    def get_state(self):
        return self.__state
from coordination.subscription import Subscription

class Topic:
    def __init__(self, initial_state : dict) -> None:
        self.__state : dict = initial_state
        self.__subscriptions : list[Subscription]  = []

    def add_subscription(self, subscription : Subscription) -> None:
        self.__subscriptions.append(subscription)

    def update_state(self, new_state : dict) -> None:
        # quick check if domain is consistent
        if self.__state.keys() == new_state.keys():
            self.__state = new_state
            # callback subscribers
            for s in self.__subscriptions:
                s.update_subscriber(self.__state)
from coordination import Action # import Action Type
from coordination import Condition # import Codition Type
from coordination.topic import Topic
from coordination.subscription import Subscription

class Dispatcher:
    __instance = None

    @staticmethod
    def getInstance() :
        """call this method to get the right instance of the Dispacher"""
        if Dispatcher.__instance == None:
            Dispatcher.__instance = Dispatcher()
        return Dispatcher.__instance

    def __init__(self) -> None:
        if self.__instance == None :
            # initialize correctly the instance
            self.__topics : dict[str, Topic] = []
        else:
            raise("This is not the right way to get an Instance, please call the static method getInstance()")
    
    def add_topic(self, topic_name : str, initial_state : dict) -> None:
        # check that the name not clashes
        if topic_name not in self.__topics:
            # add a new topic in the map
            self.__topics[topic_name] = Topic(initial_state)
        else:
            raise('Topic "{}" already exist!'.format(topic_name))
    
    def update_state(self, topic_name : str, new_state : dict) -> None:
        if topic_name in self.__topics :
            self.__topics[topic_name].update_state(new_state)
        else:
            raise('Topic "{}" doesn\'t exist!'.format(topic_name))

    def subscribe(self, topic_name : str, action : Action, condition : Condition = lambda *_ : True, parameters : list = []):
        if topic_name in self.__topics :
            sub = Subscription(action, condition, parameters)
            self.__topics[topic_name].add_subscription(sub)
        else:
            raise('Topic "{}" doesn\'t exist!'.format(topic_name))

import time
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from extension.battery import Battery
from extension.coordination.coordination_manager import CoordinationManager
from extension.decks.ai import AiDeck
from extension.decks.deck_type import DeckType
from extension.decks.flowdeck import FlowDeck
from extension.decks.multiranger import MultiRanger
from extension.decks.z_ranger import ZRanger
from extension.variables.parameters_manager import ParametersManager
from extension.variables.logging_manager import LoggingManager

class ExtendedCrazyFlie(SyncCrazyflie):

    def __init__(self, link_uri, cf=Crazyflie(rw_cache='./cache'), reset_estimators=True) -> None:
        super().__init__(link_uri=link_uri, cf=cf)
        self.__reset_estimators = reset_estimators
        self.decks = {}
        self.logging_manager : LoggingManager = None
        self.parameters_manager : ParametersManager = None
        self.coordination_manager : CoordinationManager = CoordinationManager.getInstance()

    def __enter__(self):
        super().__enter__()
        # initialize logging_manager
        self.logging_manager : LoggingManager = LoggingManager.getInstance(self.cf)
        # initialize parameters_manager
        self.parameters_manager : ParametersManager = ParametersManager.getInstance(self.cf)
        # initialize decks
        if self.__is_attached(DeckType.bcMultiranger):
            self.decks[DeckType.bcMultiranger] = MultiRanger(self)
        if self.__is_attached(DeckType.bcZRanger2):
            self.decks[DeckType.bcZRanger2] = ZRanger(self)
        if self.__is_attached(DeckType.bcAIDeck):
            self.decks[DeckType.bcAIDeck] = AiDeck(self)
        if self.__is_attached(DeckType.bcFlow2):
            self.decks[DeckType.bcFlow2] = FlowDeck(self)

        # initialize battery module
        self.battery : Battery = Battery(self)

        # reset estimator
        if self.__reset_estimators:
            print("resetting estimators")
            self.reset_estimator()

        # return reference
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logging_manager.stop_logging_all()
        super().__exit__(exc_type, exc_val, exc_tb)

    def __is_attached(self, deck:DeckType):
        self.cf.param.get_value("deck.{}".format(deck.name)) != 0

    def reset_estimator(self):
        """
        This function will reset the kalman state and wait for convergence of estimators
        """
        self.cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        self.cf.param.set_value('kalman.resetEstimation', '0')
        print('Waiting for estimator to find position...')
        self.logging_manager.add_variable('kalman', 'varPX', 100, 'float')
        self.logging_manager.add_variable('kalman', 'varPY', 100, 'float')
        self.logging_manager.add_variable('kalman', 'varPZ', 100, 'float')
        self.logging_manager.set_group_watcher('kalman', self.__cb_estimators)
        self.coordination_manager.add_observable("{}@resetEstimation".format(self.cf.link_uri), {
            'var_x_history' : [1000] * 10,
            'var_y_history' : [1000] * 10,
            'var_z_history' : [1000] * 10,
        })
        self.logging_manager.start_logging_group('kalman')
        self.coordination_manager.observe_and_wait(
            observable_name= "{}@resetEstimation".format(self.cf.link_uri), # observable name
            condition= self.__quality_test, # test if the quality is below threshold
        ).wait()# wait the quality
         
        # remove used resources
        self.logging_manager.remove_variable('kalman', 'varPX')
        self.logging_manager.remove_variable('kalman', 'varPY')
        self.logging_manager.remove_variable('kalman', 'varPZ')
        self.coordination_manager.remove_observable("{}@resetEstimation".format(self.cf.link_uri))

    # callback for update estimator values
    def __cb_estimators(self, ts, name, data):
        state = self.coordination_manager.get_observable_state("{}@resetEstimation".format(self.cf.link_uri))
        state['var_x_history'].append(data['varPX'])
        state['var_x_history'].pop(0)
        state['var_y_history'].append(data['varPY'])
        state['var_y_history'].pop(0)
        state['var_z_history'].append(data['varPZ'])
        state['var_z_history'].pop(0)
        self.coordination_manager.update_observable_state("{}@resetEstimation".format(self.cf.link_uri), state)
    # condition on notify
    def __quality_test(self, state) -> bool:
        threshold = 0.001
        min_x = min(state['var_x_history'])
        max_x = max(state['var_x_history'])
        min_y = min(state['var_y_history'])
        max_y = max(state['var_y_history'])
        min_z = min(state['var_z_history'])
        max_z = max(state['var_z_history'])
        return (max_x - min_x) < threshold and (max_y - min_y) < threshold and (max_z - min_z) < threshold
    
    

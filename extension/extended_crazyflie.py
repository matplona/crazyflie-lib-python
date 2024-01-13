import logging
import time
from cflib import crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from extension.battery import Battery
from extension.coordination.coordination_manager import CoordinationManager
from extension.decks.ai import AiDeck
from extension.decks.deck import Deck, DeckType
from extension.decks.flowdeck import FlowDeck
from extension.decks.lighthouse.lighthouse import Lighthouse
from extension.decks.multiranger.multiranger import MultiRanger
from extension.decks.z_ranger import ZRanger
from extension.state_estimate import StateEstimate
from extension.variables.parameters_manager import ParametersManager
from extension.variables.logging_manager import LogVariableType, LoggingManager
console = logging.getLogger(__name__)

class ExtendedCrazyFlie(SyncCrazyflie):
    def __init__(self, link_uri, cf=Crazyflie(), reset_estimators=True) -> None:
        super().__init__(link_uri=link_uri, cf=cf)
        self.__reset_estimators = reset_estimators
        self.decks : dict[Deck]= {}
        self.logging_manager : LoggingManager = None
        self.parameters_manager : ParametersManager = None
        self.coordination_manager : CoordinationManager = CoordinationManager.getInstance()

    def __enter__(self):
        if len(crtp.CLASSES) == 0:
            crtp.init_drivers() # initialize drivers 
        super().__enter__()
        # initialize logging_manager
        self.logging_manager : LoggingManager = LoggingManager(self)
        # initialize parameters_manager
        self.parameters_manager : ParametersManager = ParametersManager(self)

        # reset estimator
        if self.__reset_estimators:
            self.reset_estimator()

        # initialize decks
        if self.__is_attached(DeckType.bcFlow2):
            self.decks[DeckType.bcFlow2] = FlowDeck(self)
            console.info("Created FlowDeck module")
        elif self.__is_attached(DeckType.bcZRanger2):
            # if it hasn't the flowDeck but has Zrange than initialize the zrange
            self.decks[DeckType.bcZRanger2] = ZRanger(self)
            console.info("Created Zranger module")
        if self.__is_attached(DeckType.bcMultiranger):
            self.decks[DeckType.bcMultiranger] = MultiRanger(self)
            console.info("Created MultiRanger module")
        if self.__is_attached(DeckType.bcAI):
            self.decks[DeckType.bcAI] = AiDeck(self)
            console.info("Created AIDeck module")
        if self.__is_attached(DeckType.bcLighthouse4):
            self.decks[DeckType.bcLighthouse4] = Lighthouse(self)
            console.info("Created Lighthouse module")
        
        # initialize battery module
        self.battery : Battery = Battery(self)
        console.info("Created Battery module")

        # initialize state estimate module
        self.state_estimate : StateEstimate = StateEstimate(self, True, False, False)

        # return reference
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logging_manager.close()
        super().__exit__(exc_type, exc_val, exc_tb)

    def __is_attached(self, deck:DeckType) -> bool:
        return self.parameters_manager.get_value('deck', deck.name) != '0'

    def reset_estimator(self):
        """
        This function will reset the kalman state and wait for convergence of estimators
        """
        console.info("Resetting estimators")
        self.parameters_manager.set_value('kalman','resetEstimation', '1')
        time.sleep(0.1)
        self.parameters_manager.set_value('kalman','resetEstimation', '1')
        console.info('Waiting for estimator to find position...')
        self.logging_manager.add_variable('kalman', 'varPX', 10, LogVariableType.float)
        self.logging_manager.add_variable('kalman', 'varPY', 10, LogVariableType.float)
        self.logging_manager.add_variable('kalman', 'varPZ', 10, LogVariableType.float)
        self.logging_manager.set_group_watcher('kalman', self.__cb_estimators)
        self.coordination_manager.add_observable("{}@resetEstimation".format(self.cf.link_uri), {
            'var_x_history' : [1000] * 10,
            'var_y_history' : [1000] * 10,
            'var_z_history' : [1000] * 10,
        })
        start = time.time()
        self.logging_manager.start_logging_group('kalman')
        self.coordination_manager.observe_and_wait(
            observable_name= "{}@resetEstimation".format(self.cf.link_uri), # observable name
            condition= self.__quality_test, # test if the quality is below threshold
        ).wait()# wait the quality
        console.info(f"Estimators reset completed in {time.time()-start} s")
        # remove used resources
        self.logging_manager.stop_logging_group('kalman')
        self.logging_manager.remove_group('kalman')
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
        #print("0.001 > {}".format(max((max_x - min_x), (max_y - min_y), (max_z - min_z))))
        return (max_x - min_x) < threshold and (max_y - min_y) < threshold and (max_z - min_z) < threshold
    
    

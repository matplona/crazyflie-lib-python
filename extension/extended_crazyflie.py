from threading import Event
import time
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from extension.coordination.coordination_manager import CoordinationManager
from extension.decks.ai import AiDeck
from extension.decks.deck import Deck
from extension.decks.multiranger import MultiRanger
from extension.decks.z_ranger import ZRanger
from extension.variables.variables import Logger

class ExtendedCrazyFlie(SyncCrazyflie):
    def __init__(self, link_uri, cf=Crazyflie(rw_cache='./cache'), reset_estimators=True) -> None:
        super().__init__(link_uri=link_uri, cf=cf)
        self.__reset_estimators = reset_estimators
        self.decks = {}
        self.logger : Logger = None
        
    def __enter__(self):
        super().__enter__()

        # initialize logger
        self.logger : Logger = Logger.getInstance(self)

        # initialize decks
        if(self.__is_attached(Deck.bcMultiranger)):
            self.decks[Deck.bcMultiranger] = MultiRanger(scf=self)
        if(self.__is_attached(Deck.bcZRanger2)):
            self.decks[Deck.bcZRanger2] = ZRanger(scf=self)
        if(self.__is_attached(Deck.bcAIDeck)):
            self.decks[Deck.bcAIDeck] = AiDeck(scf=self)

        # reset estimator
        if(self.__reset_estimators):
            self.reset_estimator()
        
        # start logging battery level every 10 seconds
        self.logger.add_variable('pm','vbat', 10000,'float')
        self.logger.add_variable('pm','batteryLevel', 10000, 'uint8_t')
        self.logger.add_variable('pm','state', 10000, 'int8_t')
        self.logger.set_group_watcher('pm', self.__update_battery)
        self.battery_observable = "{}@battery".format(self.cf.link_uri)
        CoordinationManager.getInstance().add_observable(
            self.battery_observable, {
                'vabt' : 5,
                'batteryLevel': 100,
                'state': 0,
            }
        )
        self.logger.start_logging_group('pm')

        # return reference
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.stop_logging_all()
        super().__exit__(exc_type, exc_val, exc_tb)

    def __is_attached(self, deck:Deck):
        self.cf.param.get_value("deck.{}".format(deck.name)) != 0

    def reset_estimator(self):
        """
        This function will reset the kalman state and wait for convergence of estimators
        """
        self.cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        self.cf.param.set_value('kalman.resetEstimation', '0')
        print('Waiting for estimator to find position...')
        self.logger.add_variable('kalman', 'varPX', 10, 'float')
        self.logger.add_variable('kalman', 'varPY', 10, 'float')
        self.logger.add_variable('kalman', 'varPZ', 10, 'float')
        self.logger.set_group_watcher('kalman', self.__cb_estimators)
        cm : CoordinationManager = CoordinationManager.getInstance()
        cm.add_observable("{}@resetEstimation".format(self.cf.link_uri), {
            'var_x_history' : [1000] + 10,
            'var_y_history' : [1000] + 10,
            'var_z_history' : [1000] + 10,
        })
        cm.observe_and_wait(
            observable_name= "{}@resetEstimation".format(self.cf.link_uri), # observable name
            condition= self.__quality_test, # test if the quality is below threshold
        ).wait()# wait the quality
         
        # remove used resources
        self.logger.remove_variable('kalman', 'varPX')
        self.logger.remove_variable('kalman', 'varPX')
        self.logger.remove_variable('kalman', 'varPX')
        cm.remove_observable("{}@resetEstimation".format(self.cf.link_uri))

    # callback for update estimator values
    def __cb_estimators(self, ts, name, data):
        cm : CoordinationManager = CoordinationManager.getInstance()
        state = cm.get_observable_state("{}@resetEstimation".format(self.cf.link_uri))
        state['var_x_history'].append(data['varPX'])
        state['var_x_history'].pop(0)
        state['var_y_history'].append(data['varPY'])
        state['var_y_history'].pop(0)
        state['var_z_history'].append(data['varPZ'])
        state['var_z_history'].pop(0)
        cm.update_observable_state("{}@resetEstimation".format(self.cf.link_uri), state)
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
    # callback for update battery state
    def __update_battery(self, ts, name, data):
        self.__battery = {
            'state': data['state'],
            'vbat': data['vbat'],
            'batteryLevel':data['batteryLevel']
        }
        CoordinationManager.getInstance().update_observable_state(self.battery_observable, self.__battery)

    def get_battery(self):
        return self.__battery
    

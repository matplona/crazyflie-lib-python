"""
TODO: description
"""

import time
import cflib.crtp
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from extension.decks.deck import DeckType
from extension.extended_crazyflie import ExtendedCrazyFlie
from extension.variables.logging_manager import LogVariableType
DEFAULT_HEIGHT = 0.5
TARGET = [1, 1, DEFAULT_HEIGHT]
threshold = 0.1

def position_changed(state : dict, positions : list) -> None:
    positions.append([state['x'], state['y'], state['z']])

def target_reached(state : dict) -> bool:
    pos : list = state.items()
    reached = True
    for i in range(len(pos)):
        reached = reached and (TARGET[i] - threshold) <= pos[i] <= (TARGET[i] + threshold)
    return reached

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E705')
    positions = [] # empty positions

    with ExtendedCrazyFlie(uri) as ecf:
        time.sleep(3)
        print("Battery: {}".format(ecf.battery.get_complete_battery_status()))
        
        if(DeckType.bcFlow2 not in ecf.decks):
            pass#raise Exception("This example needs FlowDeck")
        #ecf.decks[DeckType.bcFlow2].contribute_to_state_estimate = False
        #ecf.decks[DeckType.bcFlow2].zrange.contribute_to_state_estimate = False
        #print(ecf.parameters_manager.get_value('motion', 'disable'))
        #print(ecf.parameters_manager.get_value('motion', 'disableZrange'))

        ecf.logging_manager.add_variable('stateEstimate', 'x', 1100, LogVariableType.float)
        ecf.logging_manager.add_variable('stateEstimate', 'y', 1100, LogVariableType.float)
        ecf.logging_manager.add_variable('stateEstimate', 'z', 1100, LogVariableType.float)
        observable_name = "{}@custom_observable".format(ecf.cf.link_uri)
        ecf.coordination_manager.add_observable(
            observable_name, 
            {
                'x':0,
                'y':0,
                'z':0,
            }
        )
        ecf.logging_manager.set_group_watcher(
            'stateEstimate',
            lambda ts,name,val: ecf.coordination_manager.update_observable_state(
                observable_name,
                {
                    'x':val['x'],
                    'y':val['y'],
                    'z':val['z'],
                }
            )
        )
        
        time.sleep(5)
        ecf.logging_manager.start_logging_group('stateEstimate')

        ecf.coordination_manager.observe(
            observable_name=observable_name,
            action= lambda state: print(state),
        )
        
        input("fly..")

        with MotionCommander(ecf.cf, default_height=DEFAULT_HEIGHT) as mc:
            # take_off
            ecf.coordination_manager.observe(
                observable_name = observable_name,
                action= position_changed,
                context= [mc, positions],
            ) # first observer to print out the state

            mc.start_linear_motion(0.5,0.5,0,0)
            
            ecf.coordination_manager.observe_and_wait(
                observable_name = observable_name,
                condition= target_reached,
            ).wait(timeout=3) # estimated arrival time = 2 seconds

            # mc.stop()

            print("Landing...")
            # landing
    
    # print results
    print(positions)
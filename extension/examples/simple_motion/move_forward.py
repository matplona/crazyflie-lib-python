"""
In this example is shown the coordination framework in action.
The goal of this example is to stop and land when the drone reach the position (x=1,y=0,z=Any)
relative to its starting point, i.e. the drone will stop when it move 1 meter forward.
For doing that, we set up an observe&wait observer with the coordination framework
that is looking at the position estimate, and it will wait utill the condition target_reached returns true.
Since it is very unlikely that the drone will fly over that position with exact precision,
we defined a range around the TARGET using threshold of 10cm to be sure that the drone fly through it.

To run this example is better to use:
    - DeckFlow and/or LightHouse.
"""

import logging
import time
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from extension.extended_crazyflie import ExtendedCrazyFlie
from extension.variables.logging_manager import LogVariableType
DEFAULT_HEIGHT = 0.5
TARGET = [1, 0]
threshold = 0.1

logging.basicConfig(level=logging.INFO)

def position_changed(state : dict, positions : list) -> None:
    positions.append([state['x'], state['y'], state['z']])

def target_reached(state : dict) -> bool:
    reached = True
    reached = reached and ((TARGET[0] - threshold) <= state['x'] <= (TARGET[0] + threshold))
    reached = reached and ((TARGET[1] - threshold) <= state['y'] <= (TARGET[1] + threshold))
    if reached: print('Target REACHED!')
    return reached

if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E706')
    positions = [] # empty positions
    with ExtendedCrazyFlie(uri) as ecf:
        time.sleep(1)
        ecf.logging_manager.add_variable('stateEstimate', 'x', 10, LogVariableType.float)
        ecf.logging_manager.add_variable('stateEstimate', 'y', 10, LogVariableType.float)
        ecf.logging_manager.add_variable('stateEstimate', 'z', 10, LogVariableType.float)
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
        time.sleep(1)
        ecf.logging_manager.start_logging_group('stateEstimate')
        time.sleep(1)

        # change the TARGET coordinate system into Global coordinate system
        estimate = ecf.coordination_manager.get_observable_state(observable_name)
        TARGET[0] += estimate['x']
        TARGET[1] += estimate['y']

        print(f"I'm @ [{estimate['x']},{estimate['y']},{estimate['z']}]\t\t\tTrying to reach [{TARGET[0]},{TARGET[1]},{TARGET[2]}]")

        input("fly..")

        with MotionCommander(ecf.cf, default_height=DEFAULT_HEIGHT) as mc:
            # take_off
            time.sleep(1)
            ecf.coordination_manager.observe(
                observable_name = observable_name,
                action= position_changed,
                context= [positions],
            ) # first observer to print out the state
            mc.start_linear_motion(0.2,0,0,0)
            ecf.coordination_manager.observe_and_wait(
                observable_name = observable_name,
                condition= target_reached,
            ).wait(timeout=6) # estimated arrival time = 5 seconds
            mc.start_linear_motion(0,0,0,0)#stop
            time.sleep(1)
            print("Landing...")
            # landing
    
    # print results
    #import matplotlib as plt

    print(positions)

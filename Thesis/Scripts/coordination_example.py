from cflib.positioning.motion_commander import MotionCommander
from extension.extended_crazyflie import ExtendedCrazyFlie
import time

def is_below_safe_limit(state: dict):
    return state['distance'] < 0.5

def avoid_wall(state: dict, mc: MotionCommander, direction):
    mc[direction](0.5 - state['distance'])

def add_observables(ecf: ExtendedCrazyFlie, directions):
    for direction in directions:
        ecf.coordination_manager.add_observable(
            f'{direction}_observable', {'distance': 0})

def add_variables(ecf: ExtendedCrazyFlie, directions):
    for direction in directions:
        ecf.logging_manager.add_variable('range', direction, 100)

def set_watchers(ecf: ExtendedCrazyFlie, directions):
    for direction in directions:
        ecf.logging_manager.set_variable_watcher('range', direction,  
            lambda distance: ecf.coordination_manager.update_observable_state(
                f'{direction}_observable', {distance}))
        
def observe(ecf: ExtendedCrazyFlie, mc: MotionCommander, directions_and_opposite):
    for [direction, opposite] in directions_and_opposite:
        ecf.coordination_manager.observe(
                observable_names=f'{direction}_observable',
                condition=is_below_safe_limit,
                action=avoid_wall,
                context=[mc, opposite])

if __name__ == '__main__':
    with ExtendedCrazyFlie('radio://0/80/2M/E7E7E7E7E7') as ecf:
        with MotionCommander() as mc:
            # observables setup
            add_observables(ecf, ['left', 'right', 'front', 'back'])
            # communication setup 
            add_variables(ecf, ['left', 'right', 'front', 'back'])
            # watch updates for left range and updates the relative observable
            set_watchers(ecf, ['left', 'right', 'front', 'back'])
            # observe the state and act accordingly
            observe(ecf, mc, 
                    [['left', 'right'], ['right', 'left'],
                     ['front', 'back'], ['back', 'front']])
            time.sleep(100) # wait end of execution
from multiprocessing import current_process
import sys

sys.path.append('c:\\Users\\plona\\PC\\TESI\\crazyflie-lib-python')
from cflib.crazyflie.commander import Commander
from extension.coordination.coordination_manager import CoordinationManager
from extension.extended_crazyflie import ExtendedCrazyFlie

sequence = [
    (0, 0, 0.7),
    (-0.7, 0, 0.7),
    (0, 0, 0.7),
    (0, 0, 0.2),
]
base_x = 1.0
base_y = 1.0
base_z = 0.0
base_yaw = 90  # In degrees
current_target_observable = 'current_target_observable'

print(current_process().pid)
input('start')

def update_commander(state, commander : Commander):
    if state[1]['current_target'] == len(sequence):
        commander.send_position_setpoint(0,0,0,0)
        return
    x = sequence[state[1]['current_target']][0] + base_x
    y = sequence[state[1]['current_target']][1] + base_y
    z = sequence[state[1]['current_target']][2] + base_z
    commander.send_position_setpoint(x, y, z, base_yaw)

def update_target(state, cm: CoordinationManager):
    current_target = state[1]['current_target']
    cm.update_observable_state(current_target_observable,  {'current_target': current_target +1})

def should_update_current_target(state):
    current_target = state[1]['current_target']
    if current_target < len(sequence):
        return (
            round(state[0]['x'] - base_x, 1) == sequence[current_target][0] and
            round(state[0]['y'] - base_y, 1) == sequence[current_target][1] and
            round(state[0]['z'] - base_z, 1) == sequence[current_target][2]
        )
    return False

if __name__ == '__main__':
    
    uri = 'udp://127.0.0.1:1808'
    with ExtendedCrazyFlie(uri) as ecf:
        ecf.parameters_manager.set_value('kalman','initialX', base_x)
        ecf.parameters_manager.set_value('kalman','initialY', base_y)
        ecf.parameters_manager.set_value('kalman','initialZ', base_z)
        ecf.parameters_manager.set_value('kalman','initialYaw', base_yaw)
        ecf.coordination_manager.add_observable(current_target_observable, {'current_target': 0})
        ecf.coordination_manager.multi_observe(
            observable_names=[ecf.state_estimate.observable_name, current_target_observable],
            action=update_commander,
            context=[ecf.cf.commander]
        )
        ecf.coordination_manager.multi_observe(
            observable_names=[ecf.state_estimate.observable_name, current_target_observable],
            condition=should_update_current_target,
            action=update_target,
            context=[ecf.coordination_manager]
        )
        ecf.coordination_manager.observe_and_wait(current_target_observable, lambda state: state['current_target'] == len(sequence)).wait()
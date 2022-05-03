import time
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import cflib.crtp
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from extension.extended_crazyflie import ExtendedCrazyFlie
import logging

logging.basicConfig(level=logging.INFO)
USE_ECF = False

positions = []
velocities = []
def record_position(ts, data, log):
    global positions
    p = [
        data['stateEstimate.x'],
        data['stateEstimate.y'],
        data['stateEstimate.z'],
        'A' if 'stateEstimate.ax' in data else 'N',
    ]
    positions.append(p)
def record_position_2(ts, data, log):
    p = [
        data['stateEstimate.x'],
        data['stateEstimate.y'],
        data['stateEstimate.z'],
        'A' if 'stateEstimate.ax' in data else 'N',
    ]
    print(f'Pos: {p}')
def record_position_3(ts, data, log):
    print(f'Pos: {data}')

def record_velocity(ts, data, log):
    global velocities
    g = [data['stateEstimate.vx'],data['stateEstimate.vy'],data['stateEstimate.vz']]
    velocities.append(g)
def record_velocity_2(ts, data, log):
    g = [data['stateEstimate.vx'],data['stateEstimate.vy'],data['stateEstimate.vz']]
    print(f'Vel: {g}')

def print_variables(lg : LogConfig):
    print(f'{lg.name} has the following varibles:')
    for var in lg.variables:
        print(f'\t{var.name}')

def append_variable(lg : LogConfig, name : str):
    existing = lg.variables
    lg.variables.clear()
    for v in existing:
        lg.add_variable(v.name)
    lg.add_variable(name) # append

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E705')

    if USE_ECF :
        with ExtendedCrazyFlie(uri) as ecf:
            time.sleep(5)
            with MotionCommander(ecf.cf) as mc:
                mc.forward(1)
    else :
        with SyncCrazyflie(uri) as scf:
            scf.cf.param.set_value('kalman.resetEstimation', '1')
            time.sleep(0.1)
            scf.cf.param.set_value('kalman.resetEstimation', '0')
            time.sleep(5)
            lg : LogConfig = LogConfig("uno", 1000)
            lg.add_variable('stateEstimate.x')
            lg.add_variable('stateEstimate.y')
            lg.add_variable('stateEstimate.z')
            lg.data_received_cb.add_callback(record_position_3)

            lg2 : LogConfig = LogConfig('due', 2000)
            lg2.add_variable('stateEstimate.vx')
            lg2.add_variable('stateEstimate.vy')
            lg2.add_variable('stateEstimate.vz')
            lg2.data_received_cb.add_callback(record_velocity_2)

            scf.cf.log.add_config(lg)
            scf.cf.log.add_config(lg2)
            print_variables(lg)
            lg.start()
            print("started lg")
            time.sleep(3)
            lg.stop()
            print('stopping lg')
            lg.delete()
            time.sleep(1)

            scf.cf.log.log_blocks.remove(lg)

            append_variable(lg, 'pm.vbat')
            print_variables(lg)
            scf.cf.log.add_config(lg)
            print_variables(lg)
            input("press to restart")
            #lg.create()
            lg.start()
            print("restarting lg")
            time.sleep(4)
            lg.stop()
            print('stopping lg')
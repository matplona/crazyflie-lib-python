from threading import Event
import time
import math
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.positioning.motion_commander import MotionCommander
from my_examples.calibration import WriteBsGeoSwarm

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger

go = Event()
go.clear()

DEFAULT_HEIGHT = 0.5
URI0 = 'radio://0/80/2M/E7E7E7E700'
URI1 = 'radio://0/80/2M/E7E7E7E701'

uris = {
    URI0,
    URI1
}

def print_battery_level(scf: SyncCrazyflie):
    lg = LogConfig(name='Battery', period_in_ms=10)
    lg.add_variable('pm.vbat', 'float')
    lg.add_variable('pm.batteryLevel')
    with SyncLogger(scf, lg) as logger:
        for log_entry in logger:
            print("{} : {}".format(scf.cf.link_uri, log_entry[1] ))
            break

def print_positions(swarm):
    for uri, position in swarm.get_estimated_positions().items():
            print("{} : [x={}\t, y={}\t, z={}\t]".format(uri, round(position.x,3), round(position.y,3), round(position.z,3)))

def wait_for_param_download(scf):
    while not scf.cf.param.is_updated:
        time.sleep(1.0)
"""USING MOTION COMMANDER"""
def sequence0_motion(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        go.wait(timeout=5)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(180)
        time.sleep(1)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(180)
        time.sleep(2)
def sequence1_motion(scf):
    print("Executing sequence")
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(2)
        mc.turn_left(90)
        time.sleep(2)
        go.set()
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(180)
        time.sleep(1)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(90)
        time.sleep(2)

"""USING COMMANDER"""
def take_off(cf, position):
    take_off_time = 1.0
    sleep_time = 0.1
    steps = int(take_off_time / sleep_time)
    vz = position[2] / take_off_time

    print(vz)

    for i in range(steps):
        cf.commander.send_velocity_world_setpoint(0, 0, vz, 0)
        time.sleep(sleep_time)
def land(cf, position):
    landing_time = 1.0
    sleep_time = 0.1
    steps = int(landing_time / sleep_time)
    vz = -position[2] / landing_time

    print(vz)

    for _ in range(steps):
        cf.commander.send_velocity_world_setpoint(0, 0, vz, 0)
        time.sleep(sleep_time)
    cf.commander.send_stop_setpoint()
    # Make sure that the last packet leaves before the link is closed
    # since the message queue is not flushed before closing
    time.sleep(0.1)
def sequence0_commander(scf : SyncCrazyflie):
    sequence = [
        #x, y, z, time
        (0, 0, DEFAULT_HEIGHT, 5.0),
        (1, 0, DEFAULT_HEIGHT, 5.0),
        (0, 0, DEFAULT_HEIGHT, 5.0)
    ]
    try:
        cf = scf.cf
        take_off(cf, sequence[0])
        for position in sequence:
            print('Setting position {}'.format(position))
            end_time = time.time() + position[3]
            while time.time() < end_time:
                cf.commander.send_position_setpoint(position[0],
                                                    position[1],
                                                    position[2], 0)
                time.sleep(0.1)
        land(cf, sequence[-1])
    except Exception as e:
        print(e)
def sequence1_commander(scf : SyncCrazyflie):
    sequence = [
        #x, y, z, time
        (0, -1, DEFAULT_HEIGHT, 5.0),
        (0, 0, DEFAULT_HEIGHT , 5.0),
        (0, -1, DEFAULT_HEIGHT, 5.0)
    ]
    try:
        cf = scf.cf
        take_off(cf, sequence[0])
        for position in sequence:
            print('Setting position {}'.format(position))
            end_time = time.time() + position[3]
            while time.time() < end_time:
                cf.commander.send_position_setpoint(position[0],
                                                    position[1],
                                                    position[2], 0)
                time.sleep(0.1)
        land(cf, sequence[-1])
    except Exception as e:
        print(e)

"""USING HL COMMANDER"""
def activate_high_level_commander(scf):
    scf.cf.param.set_value('commander.enHighLevel', '1')

def sequence0_hl_commander(scf : SyncCrazyflie):
    activate_high_level_commander(scf)
    time_to_move = 3.0
    sequence = [
        #x, y, z, yaw, time
        (0, 0, DEFAULT_HEIGHT, 0, time_to_move),                    #step1
        (1, 0, DEFAULT_HEIGHT, 0, time_to_move),                    #step2
        (1, 0, DEFAULT_HEIGHT, math.radians(180), time_to_move),    #step3
        (0, 0, DEFAULT_HEIGHT, math.radians(180), time_to_move),    #step4
        (0, 0, DEFAULT_HEIGHT, 0, time_to_move),                    #step5
    ]
    commander = scf.cf.high_level_commander
    commander.takeoff(DEFAULT_HEIGHT, time_to_move)
    time.sleep(time_to_move)
    for position in sequence:
        commander.go_to(position[0],position[1],position[2],position[3],position[4])
        time.sleep(position[4])
    commander.land(0.0, time_to_move)
    time.sleep(time_to_move)
    commander.stop()
    
def sequence1_hl_commander(scf : SyncCrazyflie):
    activate_high_level_commander(scf)
    time_to_move = 3.0
    sequence = [
        #x, y, z, yaw, time
        (0, -1, DEFAULT_HEIGHT, 0, time_to_move/2),                     #step1.1
        (0, -1, DEFAULT_HEIGHT, math.radians(90), time_to_move/2),      #step1.2
        (0, 0, DEFAULT_HEIGHT, math.radians(90), time_to_move),         #step2
        (0, 0, DEFAULT_HEIGHT, math.radians(-90), time_to_move),        #step3
        (0, -1, DEFAULT_HEIGHT, math.radians(-90), time_to_move),       #step4
        (0, -1, DEFAULT_HEIGHT, math.radians(0), time_to_move),         #step5
    ]
    commander = scf.cf.high_level_commander
    commander.takeoff(DEFAULT_HEIGHT, time_to_move)
    time.sleep(time_to_move)
    for position in sequence:
        commander.go_to(position[0],position[1],position[2],position[3],position[4])
        time.sleep(position[4])
    commander.land(0.0, time_to_move)
    time.sleep(time_to_move)
    commander.stop()


def do_nothing(scf):
    time.sleep(1)

tasks = {
    URI0 : [do_nothing],
    URI1 : [sequence1_hl_commander]
}

def run_independent(scf, function):
    print("Executing task for {}".format(scf.cf.link_uri))
    function(scf)

def run_sequence(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(2)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(180)
        time.sleep(1)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(180)

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        print('Waiting for parameters to be downloaded...')
        swarm.parallel(wait_for_param_download)
        swarm.parallel(print_battery_level)
        swarm_writer = WriteBsGeoSwarm(swarm)
        swarm_writer.estimate_and_write(URI0)
        print("Estimation Completed")
        time.sleep(3)
        print_positions(swarm)
        input("press to fly..")
        swarm.parallel(run_independent,  args_dict=tasks)
        #swarm.parallel(run_sequence)
        time.sleep(3)
        print_positions(swarm)


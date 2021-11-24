from threading import Event
import time
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.positioning.position_hl_commander import PositionHlCommander
from extension.variables.variables import Logger

DEFAULT_HEIGHT = 0.5
URI0 = 'radio://0/80/2M/E7E7E7E700'
URI1 = 'radio://0/80/2M/E7E7E7E701'
URI2 = 'radio://0/80/2M/E7E7E7E702'
URI3 = 'radio://0/80/2M/E7E7E7E703'
URI4 = 'radio://0/80/2M/E7E7E7E704'
URI5 = 'radio://0/80/2M/E7E7E7E705'
URI6 = 'radio://0/80/2M/E7E7E7E706'
URI7 = 'radio://0/80/2M/E7E7E7E707'

uris = {
    URI2,
    URI3,
    URI4,
    URI5,
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
        time.sleep(0.5)
        
"""USING MOTION COMMANDER"""
barrier = Event()
barrier.clear()

def target_position(ts, name, value):
    #the cf reached the target so emit event barrier to let pass who was waiting
    print("URI1 reached the target x={:2f}".format(value))
    barrier.set()

"""USING COMMANDER"""
def take_off(cf, position):
    take_off_time = 1.0
    sleep_time = 0.1
    steps = int(take_off_time / sleep_time)
    vz = position[2] / take_off_time
    for i in range(steps):
        cf.commander.send_velocity_world_setpoint(0, 0, vz, 0)
        time.sleep(sleep_time)
def land(cf, position):
    landing_time = 1.0
    sleep_time = 0.1
    steps = int(landing_time / sleep_time)
    vz = -position[2] / landing_time
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
def sequence_commander(scf : SyncCrazyflie, sequence):
    #sequence = [(x0, y0, z0, yaw0, time0), ... ]
    try:
        cf = scf.cf
        take_off(cf, sequence[0])
        for position in sequence:
            end_time = time.time() + position[4]
            while time.time() < end_time:
                cf.commander.send_position_setpoint(position[0],
                                                    position[1],
                                                    position[2],
                                                    position[3])
                time.sleep(0.1)
        land(cf, sequence[-1])
    except Exception as e:
        print(e)
"""USING HL COMMANDER"""
def activate_high_level_commander(scf):
    scf.cf.param.set_value('commander.enHighLevel', '1')

def sequence0_hl_commander(scf : SyncCrazyflie):
    x = 0.0
    y = 0.0
    z = 0.0
    print("POS_URI0: ({:2f},{:2f},{:2f})".format(x,y,z))
    with PositionHlCommander(scf, x=x, y=y, z=z, default_height=DEFAULT_HEIGHT) as commander:
        #only take off
        barrier.wait(timeout=10)
def sequence1_hl_commander(scf : SyncCrazyflie):
    logger = Logger(scf)
    logger.add_variable("stateEstimate","x", 10, "float")
    logger.add_variable("stateEstimate","y", 10, "float")
    logger.add_predicate("stateEstimate", "x", lambda val: 0.4<val<0.6)
    logger.add_watcher("stateEstimate", "x", target_position)
    logger.start_logging_all()
    x = 0.0
    y = 1.0
    z = 0.0
    print("POS_URI1: ({:2f},{:2f},{:2f})".format(x,y,z))
    with PositionHlCommander(scf, x=x, y=y, z=z, default_height=DEFAULT_HEIGHT) as commander:
        commander.go_to(x+0.5,y,1)
        barrier.wait(timeout=10)
        commander.go_to(x,y,z)
def sequence_hl_commander(scf :SyncCrazyflie, sequence):
    x = sequence[0][0]
    y = sequence[0][1]
    z = sequence[0][2]
    print("POS for {}: ({:2f},{:2f},{:2f})".format(scf.cf.link_uri,x,y,z))
    with PositionHlCommander(scf, x=x, y=y, z=z, default_height=DEFAULT_HEIGHT) as commander:
        for point in sequence[1:]:
            #for each point except the first that is the initial
            commander.go_to(point[0], point[1], point[2])

def do_nothing(scf):
    time.sleep(1)

tasks = {
    URI4 : [sequence0_hl_commander],
    URI5 : [sequence1_hl_commander],
}

sequences_hl = {
    URI2 : [[
        (0,0,0),
        (0.3,0,1),
        (0,0,DEFAULT_HEIGHT)
    ]],
    URI3 : [[
        (0,0.5,0),
        (0.3,0.5,1),
        (0,0.5,DEFAULT_HEIGHT)
    ]],
    URI4 : [[
        (0,1,0),
        (0.3,1,1),
        (0,1,DEFAULT_HEIGHT)
    ]],
    URI5 : [[
        (0,1.5,0),
        (0.3,1.5,1),
        (0,1.5,DEFAULT_HEIGHT)
    ]],
}

sequences = {
    URI2 : [[
        (0,0,DEFAULT_HEIGHT,0,3),
        (0.3,0,1,0,3),
        (0,0,DEFAULT_HEIGHT,0,3)
    ]],
    URI3 : [[
        (0,0.5,DEFAULT_HEIGHT,0,3),
        (0.3,0.5,1,0,3),
        (0,0.5,DEFAULT_HEIGHT,0,3)
    ]],
    URI4 : [[
        (0,1,DEFAULT_HEIGHT,0,3),
        (0.3,1,1,0,3),
        (0,1,DEFAULT_HEIGHT,0,3)
    ]],
    URI5 : [[
        (0.5,0,DEFAULT_HEIGHT,0,3),
        (0.8,0,1,0,3),
        (0.5,0,DEFAULT_HEIGHT,0,3)
    ]],
}

def reset_estimator(scf):
    cf = scf.cf
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')
    wait_for_position_estimator(scf)

def wait_for_position_estimator(scf):
    print('Waiting for estimator to find position...')

    log_config = LogConfig(name='Kalman Variance', period_in_ms=10)
    log_config.add_variable('kalman.varPX', 'float')
    log_config.add_variable('kalman.varPY', 'float')
    log_config.add_variable('kalman.varPZ', 'float')

    var_y_history = [1000] * 10
    var_x_history = [1000] * 10
    var_z_history = [1000] * 10

    threshold = 0.001

    with SyncLogger(scf, log_config) as logger:
        for log_entry in logger:
            data = log_entry[1]

            var_x_history.append(data['kalman.varPX'])
            var_x_history.pop(0)
            var_y_history.append(data['kalman.varPY'])
            var_y_history.pop(0)
            var_z_history.append(data['kalman.varPZ'])
            var_z_history.pop(0)

            min_x = min(var_x_history)
            max_x = max(var_x_history)
            min_y = min(var_y_history)
            max_y = max(var_y_history)
            min_z = min(var_z_history)
            max_z = max(var_z_history)

            # print("{} {} {}".
            #       format(max_x - min_x, max_y - min_y, max_z - min_z))

            if (max_x - min_x) < threshold and (
                    max_y - min_y) < threshold and (
                    max_z - min_z) < threshold:
                print("{} QUALITY REACHED".format(scf.cf.link_uri))
                break

def run_hl_common(scf, sequence):
    activate_high_level_commander(scf)
    print("Executing common hl task with independent sequence for {}".format(scf.cf.link_uri))
    sequence_hl_commander(scf, sequence)

def run_common(scf, sequence):
    print("Executing common task with independent sequence for {}".format(scf.cf.link_uri))
    sequence_commander(scf, sequence)

def run_independent(scf, function):
    activate_high_level_commander(scf)
    print("Executing task {} for {}".format(function, scf.cf.link_uri))
    function(scf)

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        print('Waiting for parameters to be downloaded...')
        swarm.parallel(wait_for_param_download)
        swarm.parallel(print_battery_level)
        swarm.parallel_safe(reset_estimator)
        time.sleep(3)
        print_positions(swarm)
        input("press to fly..")
        time.sleep(3)
        swarm.parallel_safe(run_hl_common, args_dict=sequences_hl)
        #swarm.parallel_safe(run_common, args_dict=sequences)
        #swarm.parallel_safe(run_independent, args_dict=tasks)
        time.sleep(3)
        print_positions(swarm)

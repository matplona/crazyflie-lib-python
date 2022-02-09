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

"""SYNCHRONIZATION"""
barrier = Event()
barrier.clear()
def target_position(ts, name, value):
    #the cf reached the target so emit event barrier to let pass who was waiting
    print("URI1 reached the target x={:2f}".format(value))
    barrier.set()

"""USING POSITION HL COMMANDER"""
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
def sequence_pos_hl_commander(scf :SyncCrazyflie, sequence):
    x = sequence[0][0]
    y = sequence[0][1]
    z = sequence[0][2]
    print("[o] {} starts at ({:2f},{:2f},{:2f})".format(scf.cf.link_uri,x,y,z))
    with PositionHlCommander(scf, x=x, y=y, z=z, default_height=DEFAULT_HEIGHT) as commander:
        for point in sequence[1:]:
            print("[*] {} go to ({:2f},{:2f},{:2f})".format(scf.cf.link_uri, point[0], point[1], point[2]))
            #for each point except the first that is the initial
            commander.go_to(point[0], point[1], point[2])
            time.sleep(3)

"""USING HL COMMANDER"""
def sequence_hl_commander(scf : SyncCrazyflie, sequence):
    log = LogConfig(name='State', period_in_ms=1000)
    log.add_variable('stateEstimate.x', 'float')
    log.add_variable('stateEstimate.y', 'float')
    log.add_variable('stateEstimate.z', 'float')
    with SyncLogger(scf, log) as logger:
        for log_entry in logger:
            print("{} : [x={:.2f}\t, y={:.2f}\t, z={:.2f}\t]".format(scf.cf.link_uri, log_entry[1]["stateEstimate.x"], log_entry[1]["stateEstimate.y"], log_entry[1]["stateEstimate.z"]))
            break
    commander = scf.cf.high_level_commander
    commander.takeoff(DEFAULT_HEIGHT, 3)
    time.sleep(3)
    commander.land(0, 3)
    time.sleep(3)
    commander.stop()

def do_nothing(scf):
    time.sleep(1)

tasks = {
    URI4 : [sequence0_hl_commander],
    URI5 : [sequence1_hl_commander],
}

sequences_hl = {
    #    x,     y,      z
    URI2 : [[
        (0,     0,      0),
        (0,     0,      DEFAULT_HEIGHT),
        (0.3,   0,      DEFAULT_HEIGHT),
        (0,     0,      DEFAULT_HEIGHT)
    ]],
    URI3 : [[
        (0,     0.5,    0),
        (0,     0.5,    DEFAULT_HEIGHT),
        (0.3,   0.5,    DEFAULT_HEIGHT),
        (0,     0.5,    DEFAULT_HEIGHT)
    ]],
    URI4 : [[
        (0,     1,      0),
        (0,     1,      DEFAULT_HEIGHT),
        (0.3,   1,      DEFAULT_HEIGHT),
        (0,     1,      DEFAULT_HEIGHT)
    ]],
    URI5 : [[
        (0,     1.5,    0),
        (0,     1.5,    DEFAULT_HEIGHT),
        (0.3,   1.5,    DEFAULT_HEIGHT),
        (0,     1.5,    DEFAULT_HEIGHT)
    ]],}

"""
sequences = {
    #    x,     y,      z,                  yaw,    time
    URI2 : [[
        (0,     0,      DEFAULT_HEIGHT,     0,      3),
        (0.3,   0,      DEFAULT_HEIGHT,     0,      3),
        (0,     0,      DEFAULT_HEIGHT,     0,      3)
    ]],
    URI3 : [[
        (0,     0.5,    DEFAULT_HEIGHT,     0,      3),
        (0.3,   0.5,    DEFAULT_HEIGHT,     0,      3),
        (0,     0.5,    DEFAULT_HEIGHT,     0,      3)
    ]],
    URI4 : [[
        (0,     1,      DEFAULT_HEIGHT,     0,      3),
        (0.3,   1,      DEFAULT_HEIGHT,     0,      3),
        (0,     1,      DEFAULT_HEIGHT,     0,      3)
    ]],
    URI5 : [[
        (0.5,   0,      DEFAULT_HEIGHT,     0,      3),
        (0.8,   0,      DEFAULT_HEIGHT,     0,      3),
        (0.5,   0,      DEFAULT_HEIGHT,     0,      3)
    ]],}
"""
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

def run_pos_hl_common(scf, sequence):
    activate_high_level_commander(scf)
    print("Executing common pos hl task with independent sequence for {}".format(scf.cf.link_uri))
    sequence_pos_hl_commander(scf, sequence)


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
        #swarm.parallel_safe(run_hl_common, args_dict=sequences_hl)
        swarm.parallel_safe(run_pos_hl_common, args_dict=sequences_hl)
        #swarm.parallel_safe(run_independent, args_dict=tasks) THIS USES SYNCHRONIZATION with 2 drones
        time.sleep(3)
        print_positions(swarm)

from threading import Barrier, Event
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
from extension.decks.z_ranger import ZRanger
from extension.swarm.swarm_test import print_battery_level
from extension.variables.parameters_manager import Logger
import time
import math
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from extension.decks.multiranger import MultiRanger, ActionLimit, VelocityLimit

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

            if (max_x - min_x) < threshold and (
                    max_y - min_y) < threshold and (
                    max_z - min_z) < threshold:
                print("{} QUALITY REACHED".format(scf.cf.link_uri))
                break


def keep_distance(action_value, action_period, mc : MotionCommander):
    vz = action_value / action_period # velocity in mm/ms (that is equal to m/s)
    vz = min(action_value / action_period,  VelocityLimit.MAX) # bounding up velocity to LIMIT
    vz = max(action_value / action_period, -VelocityLimit.MAX) # bounding down velocity to LIMIT
    mc.start_linear_motion(0,0,vz) # start action
    time.sleep(action_period)
    mc.start_linear_motion(0,0,0) # stop action

URI = 'radio://0/80/2M/E7E7E7E706'
DEFAULT_HEIGHT = 0.4

if __name__ == '__main__':
    import math
    expPointA = 2.5
    expStdA = 1
    expPointB = 4.0
    expStdB = 1/1000
    expCoeff = math.log((expStdB / expStdA) / (expPointB - expPointA))
    distance = 1.0
    stdDev = expStdA * (1.0  + math.exp( expCoeff * (distance - expPointA)))
    print(stdDev)
    #exit()
    # Initialize the low-level drivers
    try:
        cflib.crtp.init_drivers()
        with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
            zranger : ZRanger = ZRanger(scf)
            # scf.cf.param.set_value("stabilizer.estimator", 2) # change default estimator 1=complementary 2=EKF
            # print(scf.cf.param.get_value("stabilizer.estimator"))
            reset_estimator(scf)
            print_battery_level(scf)
            input("go..")
            with MotionCommander(scf, DEFAULT_HEIGHT) as mc:
                time.sleep(1)
                try:
                    # id = zranger.keep_distance(keep_distance, 400, mc)
                    # zranger.stop_action(id)
                    mc.forward(2)
                    #time.sleep(10)
                except Exception as e:
                    print(e)
                finally:
                    mc.land()
                    time.sleep(2)
    except:
        print("error")
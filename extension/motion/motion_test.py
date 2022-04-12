from threading import Barrier, Event
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
from extension.decks.z_ranger import ZRanger
from extension.variables.logging_manager import LoggingManager
import time
import math
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from extension.decks.multiranger import MultiRanger, ActionLimit, VelocityLimit
def spiral(mc:MotionCommander, round):
    mc.forward(distance_m=radious, velocity=(radious/step_duration))
    mc.start_linear_motion(mc.VELOCITY, 0, (spiral_height/circle_durtion), 360/circle_durtion)
    time.sleep(circle_durtion*round)

def obstacle_detected(front, back, left, right, mc : MotionCommander):
    global barrier
    print("DETECTED OBSTACLE, area:[f:{}, b:{}, l:{}, r{}]".format(front, back, left, right))
    mc.stop()
    barrier.set()

def fly_away(vx, vy, mc : MotionCommander):
    mc.start_linear_motion(vx, vy, 0)

def keep_distance(action_value, action_period, mc : MotionCommander):
    vz = action_value / action_period # velocity in mm/ms (that is equal to m/s)
    vz = min(action_value / action_period,  VelocityLimit.MAX) # bounding up velocity to LIMIT
    vz = max(action_value / action_period, -VelocityLimit.MAX) # bounding down velocity to LIMIT
    mc.start_linear_motion(0,0,vz) # start action
    time.sleep(action_period)
    mc.start_linear_motion(0,0,0) # stop action


def keep_distance_test(action_value, action_period):
    vz = action_value / action_period # velocity in mm/ms (that is equal to m/s)
    vz = min(action_value / action_period,  VelocityLimit.MAX) # bounding up velocity to LIMIT
    vz = max(action_value / action_period, -VelocityLimit.MAX) # bounding down velocity to LIMIT
    print("{} / {} = {}".format(action_value, action_period, vz))
URI = 'radio://0/80/2M/E7E7E7E706'
DEFAULT_HEIGHT = 0.7
radious = 0.5
spiral_height = 0.1
step_duration = 3
circle_durtion = 2*math.pi*radious/0.2

"""SYNCHRONIZATION"""
barrier = Event()
barrier.clear()
def target_position(ts, name, value):
    #the cf reached the target so emit event barrier to let pass who was waiting
    barrier.set()

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        #reset_estimator(scf)
        #print_battery_level(scf)
        input("go..")

        """NO MOTION"""
        # try:
        #     id = zranger.keep_distance(keep_distance_test, 400)
        #     time.sleep(3)
        #     zranger.stop_action(id)
        # except Exception as e:
        #     print(e)
        # finally:
        #     time.sleep(3)

        """WITH REAL MOTION"""
        with MotionCommander(scf, DEFAULT_HEIGHT) as mc:
            time.sleep(3)
            try:
                scf.cf.param.set_value("deck_estimate_contribution.zRange2Contribution", 0)
                mc.forward(1)
                scf.cf.param.set_value("deck_estimate_contribution.zRange2Contribution", 1)
                time.sleep(5)
                mc.back(1)
                scf.cf.param.set_value("deck_estimate_contribution.zRange2Contribution", 0)
            except Exception as e:
                print(e)
            finally:
                time.sleep(1)
                mc.land()


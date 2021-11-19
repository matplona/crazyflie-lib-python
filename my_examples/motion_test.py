import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from calibration import *
URI = 'radio://0/40/2M/1'
DEFAULT_HEIGHT = 0.5
is_ready = False

def connect_and_calibrate(cf):
    writer = WriteBsGeo(cf)
    writer.estimate_and_write()
    if not writer._valid :
        raise Exception("The enviroment geometry is not valid.")

def trajectory_one(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        """
            .   < --    .
            |           ^
            v           |
            .   -- >    .
        """
        print("Taking off")
        time.sleep(1)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(90)
        time.sleep(1)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(90)
        time.sleep(1)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(90)
        time.sleep(1)
        mc.forward(1)
        time.sleep(1)
        mc.turn_left(90)
        print("Landing")

def circular_trajectory(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(2)
        mc.circle_left(1)

def take_off_simple(scf, seconds):
    with MotionCommander(scf) as mc:
        print("Taking off")
        time.sleep(seconds)
        print("Landing")
    
logging.basicConfig(level=logging.ERROR)

if __name__ == '__main__':

    cflib.crtp.init_drivers()
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        try:
            connect_and_calibrate(scf.cf)
            #take_off_simple(scf, 10)
            #trajectory_one(scf)
        except Exception as e:
            print(str(e))
        print("closing connection")
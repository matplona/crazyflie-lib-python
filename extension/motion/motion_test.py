import time
import math
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

def spiral(mc:MotionCommander, round):
    mc.forward(distance_m=radious, velocity=(radious/step_duration))
    mc.start_linear_motion(mc.VELOCITY, 0, (spiral_height/circle_durtion), 360/circle_durtion)
    time.sleep(circle_durtion*round)

URI = 'radio://0/80/2M/E7E7E7E700'
DEFAULT_HEIGHT = 0.3
radious = 0.5
spiral_height = 0.1
step_duration = 3
circle_durtion = 2*math.pi*radious/0.2
if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        input("fly..")
        with MotionCommander(scf, DEFAULT_HEIGHT) as mc:
            time.sleep(1)                   #wait take_off
            spiral(mc, 3)



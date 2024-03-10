import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper


uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
if __name__ == '__main__':
    cflib.crtp.init_drivers()

    sequence = [
    (1, 0),
    (1, 1),
    (0, 1),
    (0, 0),
    ]

    with SyncCrazyflie(uri) as scf:
        with MotionCommander(scf.cf, default_height=0.5) as mc:

            for position in sequence:
                x = position[0] 
                y = position[1] 
                z = 0.5
                mc.move_distance(x, y, z)
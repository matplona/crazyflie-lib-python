import time
import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
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
        # take off
        for i in range(50):
            scf.cf.commander.send_hover_setpoint(0, 0, 0, 0.5)
            time.sleep(0.1)
        
        for position in sequence:
            x = position[0] 
            y = position[1] 
            z = 0.5
            
            # timed loop
            for i in range(50):
                scf.cf.commander.send_position_setpoint(x, y, z, 0)
                time.sleep(0.1)

        # landing and close the connection
        scf.cf.commander.send_stop_setpoint()
        time.sleep(0.1)
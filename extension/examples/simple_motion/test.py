import time
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import cflib.crtp
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from extension.extended_crazyflie import ExtendedCrazyFlie

USE_ECF = False

positions = []

def record_position(ts, data, log):
    global positions
    p = [data['stateEstimate.x'],data['stateEstimate.y'],data['stateEstimate.z']]
    positions.append(p)

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E706')

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
            lg : LogConfig = LogConfig("uno", 10)
            lg.add_variable('stateEstimate.x')
            lg.add_variable('stateEstimate.y')
            lg.add_variable('stateEstimate.z')
            lg.data_received_cb.add_callback(record_position)
            scf.cf.log.add_config(lg)
            with MotionCommander(scf.cf) as mc:
                lg.start()
                mc.forward(1)
                lg.stop()
            
            print(f"drone has moved {positions[len(positions)-1][0] - positions[0][0]} m")
            
    


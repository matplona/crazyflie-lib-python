import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.crazyflie.toc import Toc

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E701'

#logging level => only errors
logging.basicConfig(level=logging.ERROR)

def simple_log_async(scf, lg_stab):
    return


def simple_log(scf, logconf):
    with SyncLogger(scf, lg_stab) as logger:
        for i in range(5):
            for log_entry in logger:
                timestamp = log_entry[0]
                data = log_entry[1]
                logconf_name = log_entry[2]
                print('%s' % (data))
                break
            time.sleep(1)

def param_updated_callback(name, value):
        print("%s has value %d" % (name, int(value)))

def simple_connect():

    print("Yeah, I'm connected! :D")
    time.sleep(3)
    print("Now I will disconnect :'(")

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()


    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
    lg_stab.add_variable('pm.vbat', 'float')
    lg_stab.add_variable('pm.batteryLevel')
    lg_stab.add_variable('radio.rssi')


    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        # param_name = "sound.effect"
        # param_value = 6
        # scf.cf.param.add_update_callback(group="sound", name="effect", cb=param_updated_callback)
        # scf.cf.param.set_value(param_name, param_value)
        simple_log(scf, lg_stab)
        # param_value = 0
        # scf.cf.param.set_value(param_name, param_value)
        time.sleep(1)
()
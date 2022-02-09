import time
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

def perc_to_int(perc) -> int:
    #give a number from zero to UINT16_MAX
    return int(65535*perc/100)

URI = 'radio://0/80/2M/E7E7E7E706'
if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        scf.cf.param.set_value("motorPowerSet.enable", 1)
        input("fly..")
        for m in range(1, 5):
            print("motor m{}".format(m))
            for i in range(0,10):
                scf.cf.param.set_value("motorPowerSet.m{}".format(m), perc_to_int(i*10))
                time.sleep(0.5)
            scf.cf.param.set_value("motorPowerSet.m{}".format(m), 0)
            time.sleep(3)
        scf.cf.param.set_value("motorPowerSet.enable", 0)
        time.sleep(3)
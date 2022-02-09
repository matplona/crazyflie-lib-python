from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import cflib.crtp
from extension.decks.ai import AiDeck
import time

URI = 'radio://0/80/2M/E7E7E7E703'
deck = AiDeck()
if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        input("go...")
        time.sleep(5)
        scf.cf.param.set_value("motorPowerSet.enable", 1)
        scf.cf.param.set_value("motorPowerSet.m1", 10000)
        scf.cf.param.set_value("motorPowerSet.m2", 10000)
        scf.cf.param.set_value("motorPowerSet.m3", 10000)
        scf.cf.param.set_value("motorPowerSet.m4", 10000)
        deck.record(seconds=40, name="square")
        #deck.record(seconds=5)
        scf.cf.param.set_value("motorPowerSet.enable", 0)
        scf.cf.param.set_value("motorPowerSet.m1", 0)
        scf.cf.param.set_value("motorPowerSet.m2", 0)
        scf.cf.param.set_value("motorPowerSet.m3", 0)
        scf.cf.param.set_value("motorPowerSet.m4", 0)

        input("show...")
        deck.show_recording()
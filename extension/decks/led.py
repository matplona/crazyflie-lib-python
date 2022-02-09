from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from extension.variables.variables import Setter


class LedRing:
    def __init__(self, scf : SyncCrazyflie) -> None:
        self.__setter = Setter.getInstance(scf)
        self.__ring_effect = 6
        self.__red_solid = 20
        self.__green_solid = 20
        self.__blue_solid = 20
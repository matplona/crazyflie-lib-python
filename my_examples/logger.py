import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig

class Logger:
    def __init__ (self, cf : Crazyflie, var_list : dict, period_in_ms):
        self._cf = cf
        lg_conf = LogConfig(name=cf.link_uri, period_in_ms=period_in_ms)
        for var, type in var_list.items():
            lg_conf.add_variable(var, type)
        self._lg_conf = lg_conf

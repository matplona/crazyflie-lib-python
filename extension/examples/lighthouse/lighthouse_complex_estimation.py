"""
This example uses the most advanced and automatic geometry estimation process of the Lighthouse deck and then it plots a representation of the
flight area ( BSs + cf position) toghether with the trajectory followed during the sampling. It can be confiured with the extension/decks/lighthouse/config.xml file 
"""

import time
from cflib.utils import uri_helper
from extension.decks.deck import DeckType
from extension.decks.lighthouse.lighthouse import Lighthouse
from extension.extended_crazyflie import ExtendedCrazyFlie



#### ATTENTION: ###########################################################################
# the automatic_geometry_estimation is still EXPERIMENTAL, use it only for TESTING PURPOSES
###########################################################################################



if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

    with ExtendedCrazyFlie(uri) as ecf:
        time.sleep(5)
        ecf.battery.print_state()
        if DeckType.bcLighthouse4 not in ecf.decks:
            raise Exception('This example needs LigthHouse Deck')
        lh : Lighthouse= ecf.decks[DeckType.bcLighthouse4]
        lh.automatic_geometry_estimation(visualize=True)

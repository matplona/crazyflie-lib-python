"""
This example uses the most reliable and efficient geometry estimation process of the Lighthouse deck and then it plots a representation of the
flight area ( BSs + cf position). You will receive instruction inn the console that will guide you through the process step by step.
"""

import time
from cflib.utils import uri_helper
from decks.deck import DeckType
from decks.lighthouse.lighthouse import Lighthouse
from extended_crazyflie import ExtendedCrazyFlie

if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
    with ExtendedCrazyFlie(uri) as ecf:
        time.sleep(5)
        ecf.battery.print_state()
        if DeckType.bcLighthouse4 not in ecf.decks:
            raise Exception('This example needs LigthHouse Deck')
        lh : Lighthouse= ecf.decks[ 7]
        lh.multi_bs_geometry_estimation()
        lh.plot_result()
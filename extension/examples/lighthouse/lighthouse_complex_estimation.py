import time
from cflib.utils import uri_helper
from extension.decks.deck import DeckType
from extension.decks.lighthouse import Lighthouse
from extension.extended_crazyflie import ExtendedCrazyFlie

#logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E706')

    with ExtendedCrazyFlie(uri) as ecf:
        time.sleep(5)
        ecf.battery.print_state()
        if DeckType.bcLighthouse4 not in ecf.decks:
            raise Exception('This example needs LigthHouse Deck')
        lh : Lighthouse= ecf.decks[DeckType.bcLighthouse4]
        lh.complex_geometry_estimate(visualize=True)

import time

from colorama import Fore, Style
from cflib.positioning.motion_commander import MotionCommander
from cflib.positioning.position_hl_commander import PositionHlCommander
from cflib.utils import uri_helper
from extension.decks.deck import DeckType
from extension.decks.lighthouse import Lighthouse
from extension.extended_crazyflie import ExtendedCrazyFlie

#logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E706')

    with ExtendedCrazyFlie(uri) as ecf:
        time.sleep(3)
        # ecf.coordination_manager.observe(
        #     ecf.state_estimate.observable_name,
        #     lambda x: print(f'{Fore.MAGENTA}@{Style.RESET_ALL}({x["x"]}, {x["y"]}, {x["z"]})'),
        # )
        ecf.battery.print_state()
        # with MotionCommander(ecf.cf) as mc:
        #     time.sleep(5)
        input('fly...')
        with PositionHlCommander(ecf.cf, default_height=0.3, default_velocity=0.2) as pc:
            time.sleep(10)
        

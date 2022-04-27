"""
This program creates a hand driven drone, after takeoff
the drone can be moved using hands by simply pushing it
when your hand is in the range specified.
Closer would be the hand faster would be the drone in 
flying away from your hand.
In this example the height of the flight is fixed and 
the drone moves only in the x-y plane.
The range of the action and the velocity limits are specified in the utils.py 
"""

import time
import cflib.crtp
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from extension.decks.deck_type import DeckType
from extension.decks.lighthouse import Lighthouse
from extension.decks.multiranger import MultiRanger
from extension.examples.hand_driven_drone.utils import get_vx, get_vy
from extension.extended_crazyflie import ExtendedCrazyFlie

INITIALIZE_LIGHTHOUSE = False

def fly_away(multiranger_state : dict, mc : MotionCommander) :
    vx = get_vx(multiranger_state['front'], multiranger_state['back'])
    vy = get_vy(multiranger_state['right'], multiranger_state['left'])
    #mc.start_linear_motion(vx, vy, 0)
    print(f'({vx}, {vy})')

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E706')
    DEFAULT_HEIGHT = 0.5

    with ExtendedCrazyFlie(uri) as ecf:
        print("Battery: {}".format(ecf.battery.get_complete_battery_status()))
        if(DeckType.bcMultiranger not in ecf.decks):
            raise Exception("This example needs Multiranger deck attached")
        multiranger : MultiRanger = ecf.decks[DeckType.bcMultiranger]
        
        if(INITIALIZE_LIGHTHOUSE and DeckType.bcLighthouse4 in ecf.decks): 
            lh : Lighthouse = ecf.decks[DeckType.bcLighthouse4]
            print("Estimating the geometry")
            lh.simple_geometry_estimate()
        input("fly..")
        with MotionCommander(ecf.cf, default_height=DEFAULT_HEIGHT) as mc:
            ecf.coordination_manager.observe(
                observable_name= multiranger.observable_name,
                action= fly_away,
                context= [mc],
            )
            time.sleep(5)
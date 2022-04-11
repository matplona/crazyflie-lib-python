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
from cflib.positioning.motion_commander import MotionCommander
from extension.coordination.coordination_manager import CoordinationManager
from extension.decks.deck import Deck
from hand_driven_drone.utils import get_vx, get_vy
from extension.extended_crazyflie import ExtendedCrazyFlie

def fly_away(multiranger_state : dict, mc : MotionCommander) :
    vx = get_vx(multiranger_state['front'], multiranger_state['back'])
    vy = get_vy(multiranger_state['right'], multiranger_state['left'])
    mc.start_linear_motion(vx, vy, 0)

URI = 'radio://0/80/2M/E7E7E7E703'
DEFAULT_HEIGHT = 0.5
with ExtendedCrazyFlie(URI) as ecf:
    print(ecf.get_battery)
    if(Deck.bcMultiranger not in ecf.decks):
        raise Exception("This example needs Multiranger deck attached")
    cm : CoordinationManager = CoordinationManager.getInstance()
    with MotionCommander(ecf.cf, default_height=DEFAULT_HEIGHT) as mc:
        cm.observe(
            observable_name= ecf.decks[Deck.bcMultiranger].observable_name,
            action= fly_away,
            context= [mc],
        )
        time.sleep(30)
"""
This program creates a hand driven drone, after takeoff
the drone can be moved using hands by simply pulling it
when your hand is in the range specified.
To avoid oscillating the drone, its velocity would be clipped 
at 0.5 meter/second and will progressively reduce when it become
closer to the ActionLimit.MIN.
In this example the height of the flight is fixed and 
the drone moves only in the x-y plane.
To be safe in not hurt you the drone will stop his movement
when the range will be below a SAFE limit.
When the battery will reach 10% or less the drone will safely land.

CLIP ACTION (SPEED_CLIP=0.5)
input   output              input   output
2       0                   -2      0
1.75    0.25                -1.75   -0.25
1.5     0.5                 -1.5    -0.5
1.25    0.5                 -1.25   -0.5
1.0     0.5                 -1.0    -0.5
0.75    0.5                 -0.75   -0.5
0.5     0.5                 -0.5    -0.5
0.25    0.25                -0.25   -0.25
0.0     0.0                 
"""

from functools import reduce
import time
from cflib.positioning.motion_commander import MotionCommander
from extension.coordination.coordination_manager import CoordinationManager
from extension.decks.deck import DeckType
from extension.examples.hand_driven_drone.utils import ActionLimit, VelocityLimit,get_vx, get_vy
from extension.extended_crazyflie import ExtendedCrazyFlie

SPEED_CLIP = 0.5
BATTERY_LIMIT = 10

def is_safe(*args):
    return reduce(lambda acc, arg: acc and arg>=ActionLimit.SAFE, args, True)

def normalize(x):
    if x==0 : return x # aviod div0
    # normailze will transform x into SPEED_CLIP mantaining the sign
    return (x/abs(x))*SPEED_CLIP

def clip(x):
    sign = 1 if x==0 else x/abs(x) # store the sign (-1 or +1)
    x = abs(x) # apply the absolute value
    if x > VelocityLimit.MAX-SPEED_CLIP:
        # means that the hand is closer so we need to reduce the speed progressively
        # e.g.:
        #   x = 1.6  => x = 0.4
        #   x = 2.0  => x = 0
        x = VelocityLimit.MAX - x
    # clip will normalize only if greather than 0.5 and reapply the correct sign
    return sign * (normalize(x) if x > SPEED_CLIP else x)

def follow_safe(multiranger_state : dict, mc : MotionCommander) :
    if is_safe(multiranger_state['back'], multiranger_state['front'], multiranger_state['left'], multiranger_state['right']):
        vx = clip(get_vx(multiranger_state['front'], multiranger_state['back']))
        vy = clip(get_vy(multiranger_state['right'], multiranger_state['left']))
        mc.start_linear_motion(-vx, -vy, 0)
    else:
        # unsafe -> stop action
        mc.start_linear_motion(0, 0, 0)

URI = 'radio://0/80/2M/E7E7E7E706'
DEFAULT_HEIGHT = 0.5
if __name__ == '__main__':
    with ExtendedCrazyFlie(URI) as ecf:
        ecf.battery.print_state()
        if(DeckType.bcMultiranger not in ecf.decks):
            raise Exception("This example needs Multiranger deck attached")
        cm : CoordinationManager = CoordinationManager.getInstance()
        input('fly...')
        with MotionCommander(ecf.cf, default_height=DEFAULT_HEIGHT) as mc:
            cm.observe(
                observable_name= ecf.decks[DeckType.bcMultiranger].observable_name,
                action= follow_safe,
                context= [mc],
            )
            time.sleep(30)
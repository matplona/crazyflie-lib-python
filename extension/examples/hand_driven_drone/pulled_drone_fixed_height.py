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

from cflib.positioning.motion_commander import MotionCommander
from extension.decks.deck import DeckType
from extension.decks.multiranger.utils import Behavior
from extension.extended_crazyflie import ExtendedCrazyFlie

URI = 'radio://0/80/2M/E7E7E7E7E7'
if __name__ == '__main__':
    with ExtendedCrazyFlie(URI) as ecf:
        with MotionCommander(ecf.cf) as mc:
            ecf.decks[DeckType.bcMultiranger].set_behavior(Behavior.OBJECT_TRACKING, mc)
            
            
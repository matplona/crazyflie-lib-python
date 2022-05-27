"""
In this example we combined the behaviour from extension\examples\hand_driven_drone\pushed_drone_fixed_height.py and
extension\examples\hand_driven_drone\standing_drone_variable_height.py resulting in a full hand-driven drone.
"""

import time

from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from extension.decks.deck import DeckType
from extension.decks.multiranger import MultiRanger
from extension.decks.z_ranger import ZRanger
from extension.examples.hand_driven_drone.utils import get_vx, get_vy
from extension.extended_crazyflie import ExtendedCrazyFlie

ADJUST_VELOCITY = 0.15 # [m/s]
threshold = 0.1 # [m]
DEFAULT_HEIGHT = 0.2
prev = 0 # 0=hovering, -1=lowering, +1=raising

def adjust_height(zrange_state : dict, mc : MotionCommander, ):
    global prev
    h = zrange_state['zrange']/1000
    if (h < DEFAULT_HEIGHT + threshold) and prev < 1:
        prev = 1
        mc.start_linear_motion(0,0,ADJUST_VELOCITY, 0) # raise height
    elif (h > DEFAULT_HEIGHT - threshold) and prev >-1:
        prev = -1
        mc.start_linear_motion(0,0,-ADJUST_VELOCITY, 0) # lower height
    elif prev != 0:
        prev = 0 
        mc.start_linear_motion(0,0,0,0) # hover fixed

def fly_away(multiranger_state : dict, mc : MotionCommander) :
    vx = get_vx(multiranger_state['front'], multiranger_state['back'])
    vy = get_vy(multiranger_state['right'], multiranger_state['left'])
    mc.start_linear_motion(vx, vy, 0)
    
if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E706')
    
    with ExtendedCrazyFlie(uri) as ecf:
        ecf.battery.print_state()
        if(DeckType.bcFlow2 not in ecf.decks and DeckType.bcZRanger2 not in ecf.decks):
            raise Exception("This example needs FlowDeck or ZRanger deck attached")
        if(DeckType.bcLighthouse4 not in ecf.decks):
            raise Exception("This example needs Lighthouse deck attached")

        # disabling height and/or flow measurament from EKF
        zranger : ZRanger = None
        if DeckType.bcFlow2 in ecf.decks:
            ecf.decks[DeckType.bcFlow2].contribute_to_state_estimate = False # disable flow contribution
            zranger = ecf.decks[DeckType.bcFlow2].zranger # get the ZRanger of the FlowDeck
        if DeckType.bcZRanger2 in ecf.decks:
            zranger = ecf.decks[DeckType.bcZRanger2]
        zranger.contribute_to_state_estimate = False # disable zrange contribution
        if(DeckType.bcMultiranger not in ecf.decks):
            raise Exception("This example needs Multiranger deck attached")
        multiranger : MultiRanger = ecf.decks[DeckType.bcMultiranger]
        input("fly..")
        print(f'cf param motion.disable = {ecf.cf.param.get_value("motion.disable")}')
        print(f'cf param motion.disableZrange = {ecf.cf.param.get_value("motion.disableZrange")}')
        with MotionCommander(ecf.cf, default_height=DEFAULT_HEIGHT) as mc:
            ecf.coordination_manager.observe(
                observable_name= zranger.observable_name,
                action= adjust_height,
                context= [mc],
            )
            ecf.coordination_manager.observe(
                observable_name= multiranger.observable_name,
                action= fly_away,
                context= [mc],
            )
            time.sleep(30)
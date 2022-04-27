"""
For this example we use the hight ToF sensor of the ZRanger or the one of the FlowDeck to
to create a drone that keeps fixed is X_Y position while the height is adjustable by placing an hand
below the drone. It will try to keep the distance from your hand constant. changes of height are gradual
with a constant velocity of 0.3 m/s
"""

import time
from cflib.crazyflie.commander import Commander
import cflib.crtp
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from extension.decks.deck_type import DeckType
from extension.decks.z_ranger import ZRanger
from extension.extended_crazyflie import ExtendedCrazyFlie

def adjust_height(zrange_state : dict, c : Commander):
    h = zrange_state['zrange']
    if h > DEFAULT_HEIGHT:
        c.send_position_setpoint(0,0,h,0)
        

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E705')
    DEFAULT_HEIGHT = 0.5

    with ExtendedCrazyFlie(uri) as ecf:
        print("Battery: {}".format(ecf.battery.get_complete_battery_status()))
        if(DeckType.bcFlow2 not in ecf.decks or DeckType.bcZRanger2 not in ecf.decks):
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
        input("fly..")

        with MotionCommander(ecf.cf, default_height=DEFAULT_HEIGHT) as mc:
            ecf.coordination_manager.observe(
                observable_name= ecf.decks[DeckType.bcMultiranger].observable_name,
                action= adjust_height,
                context= [mc],
            )
            time.sleep(30)
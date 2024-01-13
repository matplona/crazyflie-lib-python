from cflib.positioning.motion_commander import MotionCommander
from extension.decks.deck import DeckType
from extension.extended_crazyflie import ExtendedCrazyFlie


def safe_distance(multiranger_state : dict, mc : MotionCommander):
    if multiranger_state['left'] < 0.5:
        mc.right(0.5 - multiranger_state['left'])
    if multiranger_state['right'] < 0.5:
        mc.left(0.5 - multiranger_state['right'])
    if multiranger_state['front'] < 0.5:
        mc.back(0.5 - multiranger_state['front'])
    if multiranger_state['back'] < 0.5:
        mc.forward(0.5 - multiranger_state['back'])
    

with ExtendedCrazyFlie('radio://0/80/2M/E7E7E7E7E7') as ecf:
    with MotionCommander(ecf.cf) as mc:
        ecf.coordination_manager.observe(
        	observable_name= ecf.decks[DeckType.bcMultiranger].observable_name,
        	action= safe_distance,
            context= [mc],
        )







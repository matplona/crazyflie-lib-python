"""
In this example is shown the coordination framework in action.
The goal of this example is to stop and land when the drone reach the position (x=1,y=0,z=Any)
relative to its starting point, i.e. the drone will stop when it move 1 meter forward.
For doing that, we set up an observe&wait observer with the coordination framework
that is looking at the position estimate, and it will wait utill the condition target_reached returns true.
Since it is very unlikely that the drone will fly over that position with exact precision,
we defined a range around the TARGET using threshold of 10cm to be sure that the drone fly through it.

To run this example is better to use:
    - DeckFlow and/or LightHouse.
"""

import logging
import time
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from extension.extended_crazyflie import ExtendedCrazyFlie
DEFAULT_HEIGHT = 0.5
TARGET = [1, 0]
threshold = 0.1

logging.basicConfig(level=logging.INFO)

def target_reached(state : dict) -> bool:
    reached = True
    reached = reached and ((TARGET[0] - threshold) <= state['x'] <= (TARGET[0] + threshold))
    reached = reached and ((TARGET[1] - threshold) <= state['y'] <= (TARGET[1] + threshold))
    if reached: print('Target REACHED!')
    return reached

if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E706')
    positions = [] # empty positions
    with ExtendedCrazyFlie(uri) as ecf:
        time.sleep(1)

        # change the TARGET coordinate system into Global coordinate system
        TARGET[0] += ecf.state_estimate.x
        TARGET[1] += ecf.state_estimate.y

        input("fly..")
        ecf.state_estimate.record_positions(period_in_ms=50)
        ecf.state_estimate.record_velocities(period_in_ms=50)
        ecf.state_estimate.record_accelerations(period_in_ms=50)
        ecf.state_estimate.record_attitudes(period_in_ms=50)
        with MotionCommander(ecf.cf, default_height=DEFAULT_HEIGHT) as mc:
            # take_off
            time.sleep(1)
            mc.start_linear_motion(0.2,0,0,0)
            ecf.coordination_manager.observe_and_wait(
                observable_name = ecf.state_estimate.observable_name,
                condition= target_reached,
            ).wait(timeout=6) # estimated arrival time = 5 seconds
            mc.start_linear_motion(0,0,0,0)#stop
            time.sleep(1)
            print("Landing...")
            # landing
        ecf.state_estimate.stop_record_positions()
        ecf.state_estimate.stop_record_velocities()
        ecf.state_estimate.stop_record_accelerations()
        ecf.state_estimate.stop_record_attitudes()

        ecf.state_estimate.plot_positions_3D()
        ecf.state_estimate.plot_position_velocity_3D()
        ecf.state_estimate.plot_position_acceleration_3D()
        ecf.state_estimate.plot_position_2D()
        ecf.state_estimate.plot_velocity_2D()
        ecf.state_estimate.plot_acceleraiton_2D()
        ecf.state_estimate.plot_attitude_2D()


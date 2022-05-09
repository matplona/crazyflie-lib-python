from __future__ import annotations
import logging
from threading import Event
import time
from typing import TYPE_CHECKING
from colorama import Fore, Style

from cv2 import threshold
import numpy as np
from cflib.positioning.motion_commander import MotionCommander
from cflib.positioning.position_hl_commander import PositionHlCommander
from extension.decks.deck import Deck, DeckType
from extension.exceptions import SetterException
from cflib.crazyflie.mem.lighthouse_memory import LighthouseBsGeometry
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_config_manager import LighthouseConfigWriter
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolution, LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleAverageReader
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleReader
from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
from cflib.localization.lighthouse_system_scaler import LighthouseSystemScaler
from cflib.localization.lighthouse_types import LhBsCfPoses, LhCfPoseSample
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import LhMeasurement
from cflib.localization.lighthouse_types import Pose
import xmlschema

console = logging.getLogger(__name__)

if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie

class Lighthouse(Deck):
    def __init__(self, ecf : ExtendedCrazyFlie) -> None:
        super().__init__(DeckType.bcLighthouse4) #initialize super
        self.__ecf = ecf

    def simple_geometry_estimate(self) -> dict[int, LighthouseBsGeometry] | None:
        self.__origin = None
        while(self.__origin is None):
            console.info("Estimating LightHouse geometry in the Origin")
            self.__origin : LhCfPoseSample = self.__record_sample() # record one sampleù
            if self.__origin is None:
                console.error("Estimation in the origin failed.")
                input("Move the crazyflie and be sure that is receivoing from at least 2 BS. Press ENTER when ready.")
        solution = self.__estimate_and_solve([self.__origin]) # estimate and solve only for origin
        if not self.__ready:
            confirm = input(f'[{Fore.YELLOW}WARNING{Style.RESET_ALL}]\tSolution did not converge, it might not be good!\nContinue? [y/n] :{Fore.CYAN}>{Style.RESET_ALL}')
        if confirm.lower() != 'y':
            print(f'Geometry estimation {Fore.RED}ABORTED{Style.RESET_ALL}')
            return None
        geo_dict : dict[int, LighthouseBsGeometry] = self.__create_geometry_dict(solution.bs_poses)
        self.upload_geometry(geo_dict)
        return geo_dict
    
    def complex_geometry_estimate(self, visualize=False) -> dict[int, LighthouseBsGeometry]:
        """This method will fly the crazyflie around the flight space to estimate the geometry in
        different position. This will leads in a better estimation of the Geometry of the environment.
        By default the crazyflie will move around from the starting point (origin) by at most 1.5 m in
        all the 3 dimension. Make sure to have at least 2 meters of free space around it. If you want
        to specify a different fligth space, modify the config file (#TODO) according to the readme.md
        inside the ligthhouse_config folder.
        """
        confirm = input(f'[!] WARNING:\tthe crazyflie {self.__ecf.cf.link_uri} will fly to estimate the geometry in multiple points in the fligth area. Continue ? [y/n].\n')
        if confirm.lower() == 'y':
            if DeckType.bcFlow2 not in self.__ecf.decks:
                console.error("To use complex estimation you need a Flow Deck attched. Aborting.")
                return
            # # # # # # # # # #     XML CONFIG PARSING  # # # # # # # # # # # # # # # # # # # # 
            

            # # # # # # # # # #     ORIGIN MEASURAMENT  # # # # # # # # # # # # # # # # # # # # 
            self.simple_geometry_estimate()
            if not self.__ready:
                console.error("Estimation in the origin failed, can't fly")
                return
            self.__ready = False
            self.__ecf.reset_estimator() # reset estimators
            H = 0.3
            # # # # # # # # # #     X AXIS MEASURAMENT  # # # # # # # # # # # # # # # # # # # # 
            console.info("X axis estimation")
            with MotionCommander(self.__ecf.cf) as mc:
                time.sleep(1) # wait take off completely
                mc.forward(1, 0.1) # move 1 meter forward slowly
                time.sleep(1) # stabilize than land
            self.__x_axis = []
            threshold=0.05 # 5 cm
            while(len(self.__x_axis) == 0):
                for _ in range(3):
                    # try 3 measurament
                    measure = self.__record_sample()
                    if measure is not None:
                        self.__x_axis = [measure]
                        break
                if len(self.__x_axis) == 0:
                    input('In this position the CF is not receiving from 2 BS. Move it manually, be sure that it is on the Positive x axis. Press ENNTER when ready.')
                if not (-threshold < self.__ecf.state_estimate.y < threshold):
                    self.__x_axis = 0 # repeat
                    input('The CF discosted too much from the X axis. Move it manually on the Positive x axis. Press ENTER when ready.')
                    continue
                if self.__ecf.state_estimate.x < 0:
                    self.__x_axis = 0 # repeat
                    input('The CF is in the negative X axis.  Move it manually on the Positive x axis. Press ENTER when ready.')
            self.__scale_reference = self.__ecf.state_estimate.x # get scale reference

            # # # # # # # # # #    XY PLANE MEASURAMENT  # # # # # # # # # # # # # # # # # # # # 
            console.info("XY plane estimation")
            self.__xy_plane = []
            threshold=0.2 # 20 cm
            movements_completed = 0
            desired_position = [
                (1, 1), #   first quad
                (-1, 1), # second quad
                (-1, -1), # third quad
                (1, -1), # fourth quad
            ]
            while(len(self.__xy_plane) < len(desired_position)):
                # if the number of measures is equal to the movements completed
                if len(self.__xy_plane) == movements_completed:
                    # need to move to next point
                    with PositionHlCommander(self.__ecf.cf, default_velocity=0.1, default_height=H) as hl:
                        time.sleep(1) # wait take off completely
                        hl.go_to(*desired_position[movements_completed], H)
                        time.sleep(1) # stabilize than land
                    movements_completed += 1

                for _ in range(3):
                    # try 3 measurament
                    measure = self.__record_sample()
                    if measure is not None:
                        self.__xy_plane.append(measure)
                        break
                if len(self.__xy_plane) == movements_completed:
                    # if the number of measures is still equal to the movements completed
                    input('In this position the CF is not receiving from 2 BS. Move it manually, be sure that it is on the XY plane but not on the X axis. Press ENNTER when ready.')
                if -threshold < self.__ecf.state_estimate.x < threshold:
                    self.__xy_plane.pop() # repeat
                    input('The CF is too close to the X axis. Move it manually on the XY plane but not on the X axis. Press ENTER when ready.')
            
            # # # # # # # # # #    SPACE MEASURAMENT  # # # # # # # # # # # # # # # # # # # # 
            console.info("3D space estimation")
            self.__space_samples = []
            plot_interval = 500
            plot_clock = 0
            waypoints = [
                (0,0,H),
                (1,0,H),
                (1,1,   H+0.05*0),
                (-1,1,  H+0.05*1),
                (-1,-1, H+0.05*2),
                (1,-1,  H+0.05*3),
                (1,1,   H+0.05*4),
                (-1,1,  H+0.05*5),
                (-1,-1, H+0.05*6),
                (1,-1,  H+0.05*7),
                (1,1,   H+0.05*8),
                (-1,1,  H+0.05*9),
                (-1,-1, H+0.05*10),
                (1,-1,  H+0.05*11),
                (1,1,   H+0.05*12),
                (-1,1,  H+0.05*13),
                (-1,-1, H+0.05*14),
                (1,-1,  H+0.05*15),
                (1,1,   H+0.05*16),
                (-1,1,  H+0.05*17),
                (-1,-1, H+0.05*18),
                (1,-1,  H+0.05*19),
                (0,0,   H+0.05*20),
            ]
            bs_seen = set()
            self.__intervals_quality = []
            def ready_cb(bs_id: int, angles: LighthouseBsVectors):
                nonlocal bs_seen
                now = time.time()
                if now > plot_clock + plot_interval: 
                    plot_clock = now # update clock
                    self.__intervals_quality.append(len(bs_seen)) # append the quality as the Num of differen bs received in the last interval 
                    bs_seen = set() # reset the bs seen in the last inteval
                measurement = LhMeasurement(timestamp=now, base_station_id=bs_id, angles=angles)
                self.__space_samples.append(measurement)
                bs_seen.add(str(bs_id + 1))
            reader = LighthouseSweepAngleReader(self.__ecf.cf, ready_cb)
            reader.start()
            self.__ecf.state_estimate.record_positions(period_in_ms=plot_interval)
            with PositionHlCommander(self.__ecf.cf, default_velocity=0.1, default_height=H) as hl:
                time.sleep(1) # wait take off completely
                for waypoint in waypoints:
                    hl.go_to(*waypoint)
                    time.sleep(0.2) # wait a bit
                time.sleep(1) # stabilize than land
            reader.stop()
            self.__ecf.state_estimate.stop_record_positions()
        
            # # # # # # # # # #    ESTIMATION  # # # # # # # # # # # # # # # # # # # # # # # 
            matched_samples = [self.__origin] + self.__x_axis + self.__xy_plane + LighthouseSampleMatcher.match(self.__space_samples, min_nr_of_bs_in_match=2)
            solution = self.__estimate_and_solve(matched_samples)
            if not self.__ready:
                confirm = input(f'[{Fore.YELLOW}WARNING{Style.RESET_ALL}]\tSolution did not converge, it might not be good!\nContinue? [y/n] :{Fore.CYAN}>{Style.RESET_ALL}')
            if confirm.lower() != 'y':
                print(f'Geometry estimation {Fore.RED}ABORTED{Style.RESET_ALL}')
                return None
            
            start_x_axis = 1
            start_xy_plane = 1 + len(self.__x_axis)
            origin_pos = solution.cf_poses[0].translation
            x_axis_poses = solution.cf_poses[start_x_axis:start_x_axis + len(self.__x_axis)]
            x_axis_pos = list(map(lambda x: x.translation, x_axis_poses))
            xy_plane_poses = solution.cf_poses[start_xy_plane:start_xy_plane + len(self.__xy_plane)]
            xy_plane_pos = list(map(lambda x: x.translation, xy_plane_poses))

            # Align the solution
            bs_aligned_poses, transformation = LighthouseSystemAligner.align(
                origin_pos, x_axis_pos, xy_plane_pos, solution.bs_poses)
            cf_aligned_poses = list(map(transformation.rotate_translate_pose, solution.cf_poses))
            # Scale the solution
            bs_scaled_poses, cf_scaled_poses, scale = LighthouseSystemScaler.scale_fixed_point(bs_aligned_poses,
                                                                                            cf_aligned_poses,
                                                                                            [self.__scale_reference, 0, 0],
                                                                                            cf_aligned_poses[1])

            if visualize:self.__visualize(cf_scaled_poses, bs_scaled_poses.values())
            geo_dict : dict[int, LighthouseBsGeometry] = self.__create_geometry_dict(solution.bs_poses)
            self.upload_geometry(geo_dict)
            return geo_dict

    def __visualize(self, cf_poses: list[Pose], bs_poses: list[Pose]):
        """Visualize positions of base stations and Crazyflie positions"""
        import matplotlib.pyplot as plt
        # get the plot of the positions while flying (last_step) using the quality as cmap
        fig, ax = self.__ecf.state_estimate.plot_positions_3D(show=False, cmap_values=self.__intervals_quality, cmp_label='Num of BS received')

        # add CF position in the plot
        positions = np.array(list(map(lambda x: x.translation, cf_poses)))
        x_cf = positions[:, 0]
        y_cf = positions[:, 1]
        z_cf = positions[:, 2]
        ax.scatter(x_cf, y_cf, z_cf, marker='x', s=15, c='k')
        
        # add BSs positions in the plot
        positions = np.array(list(map(lambda x: x.translation, bs_poses)))
        x_bs = positions[:, 0]
        y_bs = positions[:, 1]
        z_bs = positions[:, 2]
        ax.scatter(x_bs, y_bs, z_bs, marker='s', s=20, c='red')

        self.__set_axes_equal(ax)
        print('Close graph window to continue')
        plt.show()
    def __set_axes_equal(self, ax):
        '''Make axes of 3D plot have equal scale so that spheres appear as spheres,
        cubes as cubes, etc..  This is one possible solution to Matplotlib's
        ax.set_aspect('equal') and ax.axis('equal') not working for 3D.

        Input
        ax: a matplotlib axis, e.g., as output from plt.gca().
        '''

        x_limits = ax.get_xlim3d()
        y_limits = ax.get_ylim3d()
        z_limits = ax.get_zlim3d()

        x_range = abs(x_limits[1] - x_limits[0])
        x_middle = np.mean(x_limits)
        y_range = abs(y_limits[1] - y_limits[0])
        y_middle = np.mean(y_limits)
        z_range = abs(z_limits[1] - z_limits[0])
        z_middle = np.mean(z_limits)

        # The plot bounding box is a sphere in the sense of the infinity
        # norm, hence I call half the max range the plot radius.
        plot_radius = 0.5*max([x_range, y_range, z_range])

        ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
        ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
        ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])

    def __record_sample(self) -> LhCfPoseSample | None:
        """Record angles and average over the samples to reduce noise"""
        recorded_angles = None
        is_ready = Event()
        def ready_cb(averages):
            nonlocal recorded_angles
            recorded_angles = averages
            is_ready.set()
        reader = LighthouseSweepAngleAverageReader(self.__ecf.cf, ready_cb)
        reader.start_angle_collection()
        is_ready.wait()

        angles_calibrated = {}
        for bs_id, data in recorded_angles.items():
            angles_calibrated[bs_id] = data[1]

        result = LhCfPoseSample(angles_calibrated=angles_calibrated)

        visible = ', '.join(map(lambda x: str(x + 1), recorded_angles.keys()))
        console.debug(f'  Position recorded, base station ids visible: {visible}')

        if len(recorded_angles.keys()) < 2:
            console.error('Received too few base stations, we need at least two. Please try again!')
            result = None

        return result
    
    def __estimate_and_solve(self, matched_samples : list[LhCfPoseSample]) ->  LighthouseGeometrySolution:
        initial_guess : LhBsCfPoses = LighthouseInitialEstimator.estimate(
            matched_samples=matched_samples,
            sensor_positions= LhDeck4SensorPositions.positions
        )
        solution : LighthouseGeometrySolution = LighthouseGeometrySolver.solve(
            initial_guess=initial_guess, 
            matched_samples=matched_samples,
            sensor_positions= LhDeck4SensorPositions.positions
        )
        if not solution.success: 
            self.__ready = False
        return solution

    def __create_geometry_dict(self, bs_poses: dict[int, Pose]) -> dict[int, LighthouseBsGeometry]:
        geo_dict = {}
        for bs_id, pose in bs_poses.items():
            geo = LighthouseBsGeometry()
            geo.origin = pose.translation.tolist()
            geo.rotation_matrix = pose.rot_matrix.tolist()
            geo.valid = True
            geo_dict[bs_id] = geo
        return geo_dict

    def upload_geometry(self, geo_dict: dict[int, LighthouseBsGeometry]) -> None:
        """Upload the geometry dict to the Crazyflie"""
        event = Event()
        def data_written(_):
            event.set()
        helper = LighthouseConfigWriter(self.__ecf.cf)
        helper.write_and_store_config(data_written, geos=geo_dict)
        event.wait()
        console.debug("Geometry writtten inside the crazyflie")


import xmlschema
import os
schema = os.path.abspath('/lighthouse_config/config.xml')
with open(schema) as o:
    print(o.readline())
xml = os.path.abspath('/lighthouse_config/config.xml')
print(os.path.abspath(os.path.curdir))
#xmlschema.validate(xml, schema)

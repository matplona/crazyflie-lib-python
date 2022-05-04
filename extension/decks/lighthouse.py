from __future__ import annotations
from threading import Event
from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie

class Lighthouse(Deck):
    def __init__(self, ecf : ExtendedCrazyFlie) -> None:
        super().__init__(DeckType.bcLighthouse4) #initialize super
        self.__ecf = ecf

    def simple_geometry_estimate(self) -> dict[int, LighthouseBsGeometry]:
        self.__origin : LhCfPoseSample = self.__record_sample() # record one sample
        solution = self.__estimate_and_solve([self.__origin]) # estimate and solve only for origin
        geo_dict : dict[int, LighthouseBsGeometry] = self.__create_geometry_dict(solution.bs_poses)
        self.upload_geometry(geo_dict)
        return geo_dict

    def __record_sample(self) -> LhCfPoseSample:
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
        print(f'  Position recorded, base station ids visible: {visible}')

        if len(recorded_angles.keys()) < 2:
            print('Received too few base stations, we need at least two. Please try again!')
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


"""
Example of how to get estimation and write to the Lighthouse base station geometry
and calibration memory in a Crazyflie
"""
from threading import Event
from cv2 import VariationalRefinement
from cflib.crazyflie.mem import LighthouseBsGeometry
from cflib.crazyflie.mem import LighthouseMemHelper
from cflib.localization.lighthouse_bs_geo import LighthouseBsGeoEstimator
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleAverageReader
from cflib.crazyflie.swarm import Swarm

class EstimateBsGeo:
    def __init__ (self, cf):
        self._cf = cf
        self._reader = LighthouseSweepAngleAverageReader(cf=cf, ready_cb= self.cb_ready)
        self._estimator = LighthouseBsGeoEstimator()
        self._completed = Event()
        self._completed.clear()
        self._est_dict = {}
    def cb_ready(self, averages):
        est_dict = {}
        valid = True
        for bs, average in averages.items():
            estimate = self._estimator.estimate_geometry(average[1])
            if self._estimator.sanity_check_result(estimate[1]):
                est_dict[bs] = estimate
            else :
                valid = False
                print("BS {} geometry was invalid".format(bs))
        
        if valid :
            self._est_dict = est_dict
        else :
            self._est_dict = {}
        self._completed.set()  
    def estimate (self):
        """
        This finction will callback the estimation_cb function passing as parameter
        a dict in the form: {   0: (rotation_matrix, position_vector),
                                1: (rotation_matrix, position_vector)   }
        """
        self._completed.clear()
        self._est_dict = {}
        self._reader.start_angle_collection()
    def get_estimate(self):
        return self.wait_completion()
    def wait_completion(self):
        self._completed.wait()
        return self._est_dict
    def print_averages(self, averages):
        try:
            print(averages)
            for bs, average in averages.items():
                print("BS number %d with %d samples:" % (bs, average[0]))
                for i in range(len(average[1])):
                    print("Sensor {} : {}".format(i, average[1][i].cart))
            print("--------------------------------------------------")
        except Exception as e:
            print(str(e))
    def get_geo_dict (self):
        geo_dict = {}
        if not self.wait_completion() :
            raise Exception("The geometry estimated is invalid")
        for bs, estimate in self._est_dict.items() :
            lh_geo = LighthouseBsGeometry()
            lh_geo.rotation_matrix = estimate[0]
            lh_geo.origin = estimate[1]
            lh_geo.valid = True
            geo_dict[bs] = lh_geo
        return geo_dict

class WriteBsGeo:
    def __init__(self, cf):
        self._cf = cf
        self._completed = Event()
        self._estimated = Event()
        self._completed.clear()
        self._estimated.clear()
        self._geoEstimator = EstimateBsGeo(self._cf)
        self._estimate = {}
        self._valid = False
    def data_written (self, success):
        if success : 
            print("Enviroment geometry written correctly.")
        else:
            print("Error in writing geometry.")
        self._completed.set()
    def write_geometry(self, geo_dict):
        helper = LighthouseMemHelper(self._cf)
        self._completed.clear()
        helper.write_geos(geo_dict, self.data_written)
        self._completed.wait()
    def wait_estimated(self):
        self._estimated.wait()
        return self._valid
    def __initialize_estimate(self):
        self._estimated.clear()
        self._valid = False
        self._estimate = {}
    def estimate_and_write(self):
        self.__initialize_estimate()
        self._geoEstimator.estimate()
        try:
            self._estimate = self._geoEstimator.get_geo_dict()
            self.write_geometry(self._estimate)
            self._valid = True
        except Exception as e:
            self._valid = False
            raise e

class WriteBsGeoSwarm:
    def __init__(self, swarm : Swarm):
        self._swarm = swarm
        self._completed = Event()
        self._completed.clear()
        self._valid = False    
    def estimate_and_write(self, center):
        center_cf = None
        geo_estimator = None
        geo_dict = {}
        for uri, scf in self._swarm._cfs.items():
            if uri == center :
                center_cf = scf.cf
                geo_estimator = EstimateBsGeo(center_cf)
                geo_estimator.estimate()
                try:
                    geo_dict = geo_estimator.get_geo_dict()
                except Exception as e:
                    raise Exception("The swarm geometry cannot be written because of invalid center estimate")
        for uri, scf in self._swarm._cfs.items():
            #for all cf included center write the same geometry
            writer = WriteBsGeo(scf.cf)
            writer.write_geometry(geo_dict)
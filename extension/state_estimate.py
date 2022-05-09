from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie

from extension.exceptions import SetterException
from extension.variables.logging_manager import LogVariableType
import matplotlib.pyplot as plt
from math import sqrt
from threading import Timer
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import numpy as np

class StateEstimate:
    __x = 0
    __y = 0
    __z = 0
    __pos_clock = 0
    __pos_period = 0
    __positions = [[],[],[]]

    def __init__(self, ecf : ExtendedCrazyFlie, estimate_velocity = False, estimate_acceleration=False, estimate_attitude=False) -> None:
        # start logging stateEstimate every 10 ms
        ecf.logging_manager.add_variable('stateEstimateZ','x', 10, LogVariableType.uint16_t)
        ecf.logging_manager.add_variable('stateEstimateZ','y', 10, LogVariableType.uint16_t)
        ecf.logging_manager.add_variable('stateEstimateZ','z', 10, LogVariableType.uint16_t)
        if estimate_velocity:
            ecf.logging_manager.add_variable('stateEstimateZ','vx', 10, LogVariableType.uint16_t)
            ecf.logging_manager.add_variable('stateEstimateZ','vy', 10, LogVariableType.uint16_t)
            ecf.logging_manager.add_variable('stateEstimateZ','vz', 10, LogVariableType.uint16_t)
            self.__vx = 0
            self.__vy = 0
            self.__vz = 0
            self.__vel_clock = 0
            self.__vel_period = 0
            self.__velocities = [[],[],[]]
        if estimate_acceleration:
            ecf.logging_manager.add_variable('stateEstimateZ','ax', 10, LogVariableType.uint16_t)
            ecf.logging_manager.add_variable('stateEstimateZ','ay', 10, LogVariableType.uint16_t)
            ecf.logging_manager.add_variable('stateEstimateZ','az', 10, LogVariableType.uint16_t)
            self.__ax = 0
            self.__ay = 0
            self.__az = 0
            self.__acc_clock = 0
            self.__acc_period = 0
            self.__accelerations = [[],[],[]]
        if estimate_attitude:
            ecf.logging_manager.add_variable('stateEstimateZ','roll', 10, LogVariableType.uint16_t)
            ecf.logging_manager.add_variable('stateEstimateZ','pitch', 10, LogVariableType.uint16_t)
            ecf.logging_manager.add_variable('stateEstimateZ','yaw', 10, LogVariableType.uint16_t)
            self.__roll = 0
            self.__pitch = 0
            self.__yaw = 0
            self.__att_clock = 0
            self.__att_period = 0
            self.__attitudes = [[],[],[]]
        self.__estimate_velocity = estimate_velocity
        self.__estimate_acceleration = estimate_acceleration
        self.__estimate_attitude = estimate_attitude
        ecf.logging_manager.set_group_watcher('stateEstimateZ', self.__update_state)
        self.observable_name = "{}@stateEstimateZ".format(ecf.cf.link_uri)
        self.__ecf = ecf
        self.__ecf.coordination_manager.add_observable(self.observable_name, self.__get_state)
        ecf.logging_manager.start_logging_group('stateEstimateZ')
    
    def __del__(self):
        self.__ecf.logging_manager.stop_logging_group('stateEstimateZ')

    # callback for update battery state
    def __update_state(self, ts, name, data):

        # POSITION ===============================================================================
        self.__x = data['x']/1000
        self.__y = data['y']/1000
        self.__z = data['z']/1000
        # check if the state need to be recorded
        if self.__pos_clock > 0 and (ts > self.__pos_clock + self.__pos_period): 
            # if clock is active and the current timestamp is after the current clock plus period
            self.__pos_clock = ts # update the clock
            self.__positions[0].append(self.__x)
            self.__positions[1].append(self.__y)
            self.__positions[2].append(self.__z)
        
        # VELOCITY ==============================================================================
        if self.__estimate_velocity:
            self.__vx = data['vx']/1000
            self.__vy = data['vy']/1000
            self.__vz = data['vz']/1000
            # check if the state need to be recorded
            if self.__vel_clock > 0 and (ts > self.__vel_clock + self.__vel_period): 
                # if clock is active and the current timestamp is after the current clock plus period
                self.__vel_clock = ts # update the clock
                self.__velocities[0].append(self.__vx)
                self.__velocities[1].append(self.__vy)
                self.__velocities[2].append(self.__vz)

        # ACCELERATION ==========================================================================
        if self.__estimate_acceleration:
            self.__ax = data['ax']/1000
            self.__ay = data['ay']/1000
            self.__az = data['az']/1000
            if self.__acc_clock > 0 and (ts > self.__acc_clock + self.__acc_period): 
                # if clock is active and the current timestamp is after the current clock plus period
                self.__acc_clock = ts # update the clock
                self.__accelerations[0].append(self.__ax)
                self.__accelerations[1].append(self.__ay)
                self.__accelerations[2].append(self.__az)

        # ATTITUDE ==============================================================================
        if self.__estimate_attitude:
            self.__roll = data['roll']/1000
            self.__pitch = data['pitch']/1000
            self.__yaw = data['yaw']/1000
            if self.__att_clock > 0 and (ts > self.__att_clock + self.__att_period): 
                # if clock is active and the current timestamp is after the current clock plus period
                self.__att_clock = ts # update the clock
                self.__attitudes[0].append(self.__roll)
                self.__attitudes[1].append(self.__pitch)
                self.__attitudes[2].append(self.__yaw)
                
        # update the observable state
        self.__ecf.coordination_manager.update_observable_state(self.observable_name, self.__get_state())
    
    @property
    def x(self):
        return self.__x
    @property
    def y(self):
        return self.__y
    @property
    def z(self):
        return self.__z
    @property
    def vx(self):
        return self.__vx if self.__estimate_velocity else None
    @property
    def vy(self):
        return self.__vy if self.__estimate_velocity else None
    @property
    def vz(self):
        return self.__vz if self.__estimate_velocity else None
    @property
    def ax(self):
        return self.__ax if self.__estimate_acceleration else None
    @property
    def ay(self):
        return self.__ay if self.__estimate_acceleration else None
    @property
    def az(self):
        return self.__az if self.__estimate_acceleration else None
    @property
    def roll(self):
        return self.__roll if self.__estimate_attitude else None
    @property
    def pitch(self):
        return self.__pitch if self.__estimate_attitude else None
    @property
    def yaw(self):
        return self.__yaw if self.__estimate_attitude else None
    #properties are read_only
    @x.setter
    def x(self, _):
        raise SetterException('x')
    @y.setter
    def y(self, _):
        raise SetterException('y')
    @z.setter
    def z(self, _):
        raise SetterException('z')
    @vx.setter
    def vx(self, _):
        raise SetterException('vx')
    @vy.setter
    def vy(self, _):
        raise SetterException('vy')
    @vz.setter
    def vz(self, _):
        raise SetterException('vz')
    @ax.setter
    def ax(self, _):
        raise SetterException('ax')
    @ay.setter
    def ay(self, _):
        raise SetterException('ay')
    @az.setter
    def az(self, _):
        raise SetterException('az')
    @roll.setter
    def roll(self, _):
        raise SetterException('roll')
    @pitch.setter
    def pitch(self, _):
        raise SetterException('pitch')
    @yaw.setter
    def yaw(self, _):
        raise SetterException('yaw')
    
    def __get_state(self) -> dict:
        return {
            'x':self.x,
            'y':self.y,
            'z':self.z,
            'vx':self.vx, # none if not included
            'vy':self.vy, # none if not included
            'vz':self.vz, # none if not included
            'ax':self.ax, # none if not included
            'ay':self.ay, # none if not included
            'az':self.az, # none if not included
            'roll':self.roll, # none if not included
            'pitch':self.pitch, # none if not included
            'yaw':self.yaw, # none if not included
        }
    
    def record_positions(self, period_in_ms = 10, stop_after_in_s = -1, append = False):
        self.__pos_clock = 1 # clock active
        self.__pos_period = period_in_ms
        if not append: self.__positions = [] # clear previous record
        if stop_after_in_s > 0: Timer(stop_after_in_s, self.stop_record_positions).start()

    def record_velocities(self, period_in_ms = 10, stop_after_in_s = -1, append = False):
        if not self.__estimate_velocity:raise Exception("Velocity is not currently estimated")
        self.__vel_clock = 1 # clock active
        self.__vel_period = period_in_ms
        if not append: self.__velocities = [] # clear previous record
        if stop_after_in_s > 0: Timer(stop_after_in_s, self.stop_record_velocities).start()
    
    def record_accelerations(self, period_in_ms = 10, stop_after_in_s = -1, append = False):
        if not self.__estimate_acceleration:raise Exception("Acceleration is not currently estimated")
        self.__acc_clock = 1 # clock active
        self.__acc_period = period_in_ms
        if not append: self.__accelerations = [] # clear previous record
        if stop_after_in_s > 0: Timer(stop_after_in_s, self.stop_record_accelerations).start()
    
    def record_attitudes(self, period_in_ms = 10, stop_after_in_s = -1, append = False):
        if not self.__estimate_attitude:raise Exception("Attitude is not currently estimated")
        self.__att_clock = 1 # clock active
        self.__att_period = period_in_ms
        if not append: self.__attitudes = [] # clear previous record
        if stop_after_in_s > 0: Timer(stop_after_in_s, self.stop_record_attitudes).start()

    def stop_record_positions(self):
        self.__pos_clock = 0
    def stop_record_velocities(self):
        self.__vel_clock = 0
    def stop_record_accelerations(self):
        self.__acc_clock = 0
    def stop_record_attitudes(self):
        self.__att_clock = 0

    def plot_positions_3D(self, animated=False):
        if len(self.__positions) == 0:
            print("Positions record is empty")
        else:
            def __update(num, data, line):
                # NOTE: there is no .set_data() for 3 dim data...
                line.set_data(data[0:2, :num])
                line.set_3d_properties(data[2, :num])
            data_set = np.array([self.__positions[0], self.__positions[1], self.__positions[2]])
            samples = len(data_set[0])
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            line = ax.plot(data_set[0],data_set[1],data_set[2], )[0]
            ax.plot(data_set[0][0],data_set[1][0],data_set[2][0], c='g', marker='^')
            ax.plot(data_set[0][samples-1],data_set[1][samples-1],data_set[2][samples-1], c='r', marker='v')
            ax.set_title(f'{self.__ecf.cf.link_uri} trajectory')
            ax.set_xlabel('X [m]')
            ax.set_ylabel('Y [m]')
            ax.set_zlabel('Z [m]')
            if animated:
                FuncAnimation(
                    fig,
                    __update,
                    samples,
                    fargs=(data_set, line),
                    interval=200, 
                    blit=False,
                )
            plt.show()
    
    def plot_position_velocity_3D(self):
        if len(self.__positions) == 0 or len(self.__velocities) == 0:
            print("Positions and/or Velocities record are empty")
        elif len(self.__positions) != len(self.__velocities):
            print("Velocities and Positions has incompatible size")
        else:
            points = np.array([self.__positions[0], self.__positions[1], self.__positions[2]]).T.reshape(-1, 1, 3)
            vel = np.array([self.__velocities[0], self.__velocities[1], self.__velocities[2]]).T
            v_xyz = np.array([sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]) for v in vel])
            n = len(self.__positions[0])
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            lc = Line3DCollection(segments, cmap=plt.get_cmap('RdYlGn'),
                    norm=plt.Normalize(v_xyz.min(), v_xyz.max()))
            lc.set_array(v_xyz)
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            ax.set_xlim(min(self.__positions[0]), max(self.__positions[0]))
            ax.set_ylim(min(self.__positions[1]), max(self.__positions[1]))
            ax.set_zlim(min(self.__positions[2]), max(self.__positions[2]))
            line = ax.add_collection3d(lc)
            fig.colorbar(line, ax=ax, label='Velocity [m/s]', location='bottom', shrink=0.5)
            ax.plot(self.__positions[0][0],self.__positions[1][0],self.__positions[2][0], c='g', marker='^')
            ax.plot(self.__positions[0][n-1],self.__positions[1][n-1],self.__positions[2][n-1], c='r', marker='v')
            ax.set_title(f'{self.__ecf.cf.link_uri} trajectory with velocity')
            ax.set_xlabel('X [m]')
            ax.set_ylabel('Y [m]')
            ax.set_zlabel('Z [m]')
            plt.show()

    def plot_position_acceleration_3D(self):
        if len(self.__positions) == 0 or len(self.__accelerations) == 0:
            print("Positions and Acceletations record are empty")
        elif len(self.__positions) != len(self.__accelerations):
            print("Acceletations and Positions has incompatible size")
        else:
            points = np.array([self.__positions[0], self.__positions[1], self.__positions[2]]).T.reshape(-1, 1, 3)
            acc = np.array([self.__accelerations[0], self.__accelerations[1], self.__accelerations[2]]).T
            a_xyz = np.array([sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]) for a in acc])
            n = len(self.__positions[0])
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            lc = Line3DCollection(segments, cmap=plt.get_cmap('RdYlGn'),
                    norm=plt.Normalize(a_xyz.min(), a_xyz.max()))
            lc.set_array(a_xyz)
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            ax.set_xlim(min(self.__positions[0]), max(self.__positions[0]))
            ax.set_ylim(min(self.__positions[1]), max(self.__positions[1]))
            ax.set_zlim(min(self.__positions[2]), max(self.__positions[2]))
            line = ax.add_collection3d(lc)
            fig.colorbar(line, ax=ax, label='Acceleration [m/s²]', location='bottom', shrink=0.5)
            ax.plot(self.__positions[0][0],self.__positions[1][0],self.__positions[2][0], c='g', marker='^')
            ax.plot(self.__positions[0][n-1],self.__positions[1][n-1],self.__positions[2][n-1], c='r', marker='v')
            ax.set_title(f'{self.__ecf.cf.link_uri} trajectory with acceleration')
            ax.set_xlabel('X [m]')
            ax.set_ylabel('Y [m]')
            ax.set_zlabel('Z [m]')
            plt.show()
    
    def plot_position_2D(self):
        if len(self.__positions) == 0:
            print("Positions record is empty")
        else:
            data_set = np.array([self.__positions[0], self.__positions[1], self.__positions[2]])
            fig, axs = plt.subplots(3, 1, sharex=True, sharey=False)
            axs[0].set_ylabel('Position X [m/s]')
            axs[1].set_ylabel('Position Y [m/s]')
            axs[2].set_ylabel('Position Z [m/s]')
            axs[2].set_xlabel('Time [s]')
            ts = [x*self.__pos_period/1000 for x in range(len(data_set[0]))]
            axs[0].plot(data_set[0], ts)
            axs[1].plot(data_set[1], ts)
            axs[2].plot(data_set[2], ts)
            plt.show()

    def plot_velocity_2D(self):
        if len(self.__velocities) == 0:
            print("Velocities record is empty")
        else:
            data_set = np.array([self.__velocities[0], self.__velocities[1], self.__velocities[2]])
            fig, axs = plt.subplots(3, 1, sharex=True, sharey=False)
            axs[0].set_ylabel('Velocity X [m/s²]')
            axs[1].set_ylabel('Velocity Y [m/s²]')
            axs[2].set_ylabel('Velocity Z [m/s²]')
            axs[2].set_xlabel('Time [s]')
            ts = [x*self.__acc_period/1000 for x in range(len(data_set[0]))]
            axs[0].plot(data_set[0], ts)
            axs[1].plot(data_set[1], ts)
            axs[2].plot(data_set[2], ts)
            plt.show()

    def plot_acceleraiton_2D(self):
        if len(self.__accelerations) == 0:
            print("Accelerations record is empty")
        else:
            data_set = np.array([self.__accelerations[0], self.__accelerations[1], self.__accelerations[2]])
            fig, axs = plt.subplots(3, 1, sharex=True, sharey=False)
            axs[0].set_ylabel('Acceleration X [m/s]')
            axs[1].set_ylabel('Acceleration Y [m/s]')
            axs[2].set_ylabel('Acceleration Z [m/s]')
            axs[2].set_xlabel('Time [s]')
            ts = [x*self.__vel_period/1000 for x in range(len(data_set[0]))]
            axs[0].plot(data_set[0], ts)
            axs[1].plot(data_set[1], ts)
            axs[2].plot(data_set[2], ts)
            plt.show()
    
    def plot_attitude_2D(self):
        if len(self.__attitudes) == 0:
            print("Attitudes record is empty")
        else:
            data_set = np.array([self.__attitudes[0], self.__attitudes[1], self.__attitudes[2]])
            fig, axs = plt.subplots(3, 1, sharex=True, sharey=False)
            axs[0].set_ylabel('Roll [deg]')
            axs[1].set_ylabel('Pitch [deg]')
            axs[2].set_ylabel('Yaw [deg]')
            axs[2].set_xlabel('Time [s]')
            ts = [x*self.__vel_period/1000 for x in range(len(data_set[0]))]
            axs[0].plot(data_set[0], ts)
            axs[1].plot(data_set[1], ts)
            axs[2].plot(data_set[2], ts)
            plt.show()
    
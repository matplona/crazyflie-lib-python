
import csv
import errno
import logging 
import math
from queue import Queue
import struct
from threading import Thread, Timer
import time
from cflib.crtp.crtpstack import CRTPPacket, CRTPPort
import socket

LOG_TYPES= {
    'UINT8_T' : (b'\x01','<B',1),
    'UINT16_T' : (b'\x02','<H',2),
    'UINT32_T' : (b'\x03','<L',3),
    'INT8_T' : (b'\x04','<b',4),
    'INT16_T' : (b'\x05','<h',5),
    'INT32_T' : (b'\x06','<i',6),
    'FLOAT' : (b'\x07','<f',7),
    'FP16' : (b'\x08','<e',8),
}

PARAM_TYPES= {
    'UINT8_T' : (b'\x08', '<B'),
    'UINT16_T' : (b'\x09', '<H'),
    'UINT32_T' : (b'\x0a', '<L'),
    'UINT64_T' : (b'\x0b', '<Q'),
    'INT8_T' : (b'\x00', '<b'),
    'INT16_T' : (b'\x01', '<h'),
    'INT32_T' : (b'\x02', '<i'),
    'INT64_T' : (b'\x03', '<q'),
    'FP16' : (b'\x05', ''),
    'FLOAT' : (b'\x06', '<f'),
    'DOUBLE' : (b'\x07', '<d'),
    'EXTENDED': (b'\x10', ''),
    'READ_ONLY': (b'\x40', '')
}

MAGENTA = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
RED = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
ERROR = RED + BOLD + UNDERLINE

class CrazyflieSimulator():
    def __init__(self, log_file):
        self.MAX_VELOCITY = 0.2
        self.MAX_RATE = 360.0 / 5 
        self.SETPOINT_EXPIRE_TIME = 0.5
        self._log_toc = [
            LogInternalStateElement('FLOAT','acc','x', 0, 0),
            LogInternalStateElement('FLOAT','acc','y', 0, 1),
            LogInternalStateElement('FLOAT','acc','z', 0, 2),
            LogInternalStateElement('UINT8_T','activeMarker','btSns', 0, 3),
            LogInternalStateElement('UINT8_T','activeMarker','i2cOk', 0, 4),
            LogInternalStateElement('UINT32_T','aidecktest','testresult', 0, 5),
            LogInternalStateElement('UINT8_T','aidecktest','done', 0, 6),
            LogInternalStateElement('UINT8_T','amarkUartTest','passed', 0, 7),
            LogInternalStateElement('FLOAT','baro','asl', 0, 8),
            LogInternalStateElement('FLOAT','baro','temp', 0, 9),
            LogInternalStateElement('FLOAT','baro','pressure', 0, 10),
            LogInternalStateElement('FLOAT','controller','cmd_thrust', 0, 11),
            LogInternalStateElement('FLOAT','controller','cmd_roll', 0, 12),
            LogInternalStateElement('FLOAT','controller','cmd_pitch', 0, 13),
            LogInternalStateElement('FLOAT','controller','cmd_yaw', 0, 14),
            LogInternalStateElement('FLOAT','controller','r_roll', 0, 15),
            LogInternalStateElement('FLOAT','controller','r_pitch', 0, 16),
            LogInternalStateElement('FLOAT','controller','r_yaw', 0, 17),
            LogInternalStateElement('FLOAT','controller','accelz', 0, 18),
            LogInternalStateElement('FLOAT','controller','actuatorThrust', 0, 19),
            LogInternalStateElement('FLOAT','controller','roll', 0, 20),
            LogInternalStateElement('FLOAT','controller','pitch', 0, 21),
            LogInternalStateElement('FLOAT','controller','yaw', 0, 22),
            LogInternalStateElement('FLOAT','controller','rollRate', 0, 23),
            LogInternalStateElement('FLOAT','controller','pitchRate', 0, 24),
            LogInternalStateElement('FLOAT','controller','yawRate', 0, 25),
            LogInternalStateElement('INT16_T','controller','ctr_yaw', 0, 26),
            LogInternalStateElement('UINT16_T','crtp','rxRate', 0, 27),
            LogInternalStateElement('UINT16_T','crtp','txRate', 0, 28),
            LogInternalStateElement('FLOAT','ctrlINDI','cmd_thrust', 0, 29),
            LogInternalStateElement('FLOAT','ctrlINDI','cmd_roll', 0, 30),
            LogInternalStateElement('FLOAT','ctrlINDI','cmd_pitch', 0, 31),
            LogInternalStateElement('FLOAT','ctrlINDI','cmd_yaw', 0, 32),
            LogInternalStateElement('FLOAT','ctrlINDI','r_roll', 0, 33),
            LogInternalStateElement('FLOAT','ctrlINDI','r_pitch', 0, 34),
            LogInternalStateElement('FLOAT','ctrlINDI','r_yaw', 0, 35),
            LogInternalStateElement('FLOAT','ctrlINDI','u_act_dyn_p', 0, 36),
            LogInternalStateElement('FLOAT','ctrlINDI','u_act_dyn_q', 0, 37),
            LogInternalStateElement('FLOAT','ctrlINDI','u_act_dyn_r', 0, 38),
            LogInternalStateElement('FLOAT','ctrlINDI','du_p', 0, 39),
            LogInternalStateElement('FLOAT','ctrlINDI','du_q', 0, 40),
            LogInternalStateElement('FLOAT','ctrlINDI','du_r', 0, 41),
            LogInternalStateElement('FLOAT','ctrlINDI','ang_accel_ref_p', 0, 42),
            LogInternalStateElement('FLOAT','ctrlINDI','ang_accel_ref_q', 0, 43),
            LogInternalStateElement('FLOAT','ctrlINDI','ang_accel_ref_r', 0, 44),
            LogInternalStateElement('FLOAT','ctrlINDI','rate_d', 0, 45),
            LogInternalStateElement('FLOAT','ctrlINDI','uf_p', 0, 46),
            LogInternalStateElement('FLOAT','ctrlINDI','uf_q', 0, 47),
            LogInternalStateElement('FLOAT','ctrlINDI','uf_r', 0, 48),
            LogInternalStateElement('FLOAT','ctrlINDI','Omega_f_p', 0, 49),
            LogInternalStateElement('FLOAT','ctrlINDI','Omega_f_q', 0, 50),
            LogInternalStateElement('FLOAT','ctrlINDI','Omega_f_r', 0, 51),
            LogInternalStateElement('FLOAT','ctrlINDI','n_p', 0, 52),
            LogInternalStateElement('FLOAT','ctrlINDI','n_q', 0, 53),
            LogInternalStateElement('FLOAT','ctrlINDI','n_r', 0, 54),
            LogInternalStateElement('FLOAT','ctrlMel','cmd_thrust', 0, 55),
            LogInternalStateElement('FLOAT','ctrlMel','cmd_roll', 0, 56),
            LogInternalStateElement('FLOAT','ctrlMel','cmd_pitch', 0, 57),
            LogInternalStateElement('FLOAT','ctrlMel','cmd_yaw', 0, 58),
            LogInternalStateElement('FLOAT','ctrlMel','r_roll', 0, 59),
            LogInternalStateElement('FLOAT','ctrlMel','r_pitch', 0, 60),
            LogInternalStateElement('FLOAT','ctrlMel','r_yaw', 0, 61),
            LogInternalStateElement('FLOAT','ctrlMel','accelz', 0, 62),
            LogInternalStateElement('FLOAT','ctrlMel','zdx', 0, 63),
            LogInternalStateElement('FLOAT','ctrlMel','zdy', 0, 64),
            LogInternalStateElement('FLOAT','ctrlMel','zdz', 0, 65),
            LogInternalStateElement('FLOAT','ctrlMel','i_err_x', 0, 66),
            LogInternalStateElement('FLOAT','ctrlMel','i_err_y', 0, 67),
            LogInternalStateElement('FLOAT','ctrlMel','i_err_z', 0, 68),
            LogInternalStateElement('FLOAT','ctrltarget','x', 0, 69),
            LogInternalStateElement('FLOAT','ctrltarget','y', 0, 70),
            LogInternalStateElement('FLOAT','ctrltarget','z', 0, 71),
            LogInternalStateElement('FLOAT','ctrltarget','vx', 0, 72),
            LogInternalStateElement('FLOAT','ctrltarget','vy', 0, 73),
            LogInternalStateElement('FLOAT','ctrltarget','vz', 0, 74),
            LogInternalStateElement('FLOAT','ctrltarget','ax', 0, 75),
            LogInternalStateElement('FLOAT','ctrltarget','ay', 0, 76),
            LogInternalStateElement('FLOAT','ctrltarget','az', 0, 77),
            LogInternalStateElement('FLOAT','ctrltarget','roll', 0, 78),
            LogInternalStateElement('FLOAT','ctrltarget','pitch', 0, 79),
            LogInternalStateElement('FLOAT','ctrltarget','yaw', 0, 80),
            LogInternalStateElement('INT16_T','ctrltargetZ','x', 0, 81),
            LogInternalStateElement('INT16_T','ctrltargetZ','y', 0, 82),
            LogInternalStateElement('INT16_T','ctrltargetZ','z', 0, 83),
            LogInternalStateElement('INT16_T','ctrltargetZ','vx', 0, 84),
            LogInternalStateElement('INT16_T','ctrltargetZ','vy', 0, 85),
            LogInternalStateElement('INT16_T','ctrltargetZ','vz', 0, 86),
            LogInternalStateElement('INT16_T','ctrltargetZ','ax', 0, 87),
            LogInternalStateElement('INT16_T','ctrltargetZ','ay', 0, 88),
            LogInternalStateElement('INT16_T','ctrltargetZ','az', 0, 89),
            LogInternalStateElement('UINT8_T','DTR_P2P','rx_state', 0, 90),
            LogInternalStateElement('UINT8_T','DTR_P2P','tx_state', 0, 91),
            LogInternalStateElement('FLOAT','estimator','rtApnd', 0, 92),
            LogInternalStateElement('FLOAT','estimator','rtRej', 0, 93),
            LogInternalStateElement('FLOAT','ext_pos','X', 0, 94),
            LogInternalStateElement('FLOAT','ext_pos','Y', 0, 95),
            LogInternalStateElement('FLOAT','ext_pos','Z', 0, 96),
            LogInternalStateElement('FLOAT','extrx','thrust', 0, 97),
            LogInternalStateElement('FLOAT','extrx','roll', 0, 98),
            LogInternalStateElement('FLOAT','extrx','pitch', 0, 99),
            LogInternalStateElement('FLOAT','extrx','rollRate', 0, 100),
            LogInternalStateElement('FLOAT','extrx','pitchRate', 0, 101),
            LogInternalStateElement('FLOAT','extrx','yawRate', 0, 102),
            LogInternalStateElement('FLOAT','extrx','zVel', 0, 103),
            LogInternalStateElement('UINT8_T','extrx','AltHold', 0, 104),
            LogInternalStateElement('UINT8_T','extrx','Arm', 0, 105),
            LogInternalStateElement('UINT16_T','extrx_raw','ch0', 0, 106),
            LogInternalStateElement('UINT16_T','extrx_raw','ch1', 0, 107),
            LogInternalStateElement('UINT16_T','extrx_raw','ch2', 0, 108),
            LogInternalStateElement('UINT16_T','extrx_raw','ch3', 0, 109),
            LogInternalStateElement('UINT16_T','extrx_raw','ch4', 0, 110),
            LogInternalStateElement('UINT16_T','extrx_raw','ch5', 0, 111),
            LogInternalStateElement('UINT16_T','extrx_raw','ch6', 0, 112),
            LogInternalStateElement('UINT16_T','extrx_raw','ch7', 0, 113),
            LogInternalStateElement('FLOAT','flapper','vbat', 0, 114),
            LogInternalStateElement('FLOAT','flapper','i_raw', 0, 115),
            LogInternalStateElement('FLOAT','flapper','current', 0, 116),
            LogInternalStateElement('FLOAT','flapper','power', 0, 117),
            LogInternalStateElement('INT32_T','gps','lat', 0, 118),
            LogInternalStateElement('INT32_T','gps','lon', 0, 119),
            LogInternalStateElement('FLOAT','gps','hMSL', 0, 120),
            LogInternalStateElement('FLOAT','gps','hAcc', 0, 121),
            LogInternalStateElement('INT32_T','gps','nsat', 0, 122),
            LogInternalStateElement('INT32_T','gps','fix', 0, 123),
            LogInternalStateElement('INT16_T','gyro','xRaw', 0, 124),
            LogInternalStateElement('INT16_T','gyro','yRaw', 0, 125),
            LogInternalStateElement('INT16_T','gyro','zRaw', 0, 126),
            LogInternalStateElement('FLOAT','gyro','xVariance', 0, 127),
            LogInternalStateElement('FLOAT','gyro','yVariance', 0, 128),
            LogInternalStateElement('FLOAT','gyro','zVariance', 0, 129),
            LogInternalStateElement('FLOAT','gyro','x', 0, 130),
            LogInternalStateElement('FLOAT','gyro','y', 0, 131),
            LogInternalStateElement('FLOAT','gyro','z', 0, 132),
            LogInternalStateElement('FLOAT','health','motorVarXM1', 0, 133),
            LogInternalStateElement('FLOAT','health','motorVarYM1', 0, 134),
            LogInternalStateElement('FLOAT','health','motorVarXM2', 0, 135),
            LogInternalStateElement('FLOAT','health','motorVarYM2', 0, 136),
            LogInternalStateElement('FLOAT','health','motorVarXM3', 0, 137),
            LogInternalStateElement('FLOAT','health','motorVarYM3', 0, 138),
            LogInternalStateElement('FLOAT','health','motorVarXM4', 0, 139),
            LogInternalStateElement('FLOAT','health','motorVarYM4', 0, 140),
            LogInternalStateElement('UINT8_T','health','motorPass', 0, 141),
            LogInternalStateElement('FLOAT','health','batterySag', 0, 142),
            LogInternalStateElement('UINT8_T','health','batteryPass', 0, 143),
            LogInternalStateElement('UINT16_T','health','motorTestCount', 0, 144),
            LogInternalStateElement('FLOAT','kalman','stateX', 0, 145),
            LogInternalStateElement('FLOAT','kalman','stateY', 0, 146),
            LogInternalStateElement('FLOAT','kalman','stateZ', 0, 147),
            LogInternalStateElement('FLOAT','kalman','statePX', 0, 148),
            LogInternalStateElement('FLOAT','kalman','statePY', 0, 149),
            LogInternalStateElement('FLOAT','kalman','statePZ', 0, 150),
            LogInternalStateElement('FLOAT','kalman','stateD0', 0, 151),
            LogInternalStateElement('FLOAT','kalman','stateD1', 0, 152),
            LogInternalStateElement('FLOAT','kalman','stateD2', 0, 153),
            LogInternalStateElement('FLOAT','kalman','varX', 0, 154),
            LogInternalStateElement('FLOAT','kalman','varY', 0, 155),
            LogInternalStateElement('FLOAT','kalman','varZ', 0, 156),
            LogInternalStateElement('FLOAT','kalman','varPX', 0, 157),
            LogInternalStateElement('FLOAT','kalman','varPY', 0, 158),
            LogInternalStateElement('FLOAT','kalman','varPZ', 0, 159),
            LogInternalStateElement('FLOAT','kalman','varD0', 0, 160),
            LogInternalStateElement('FLOAT','kalman','varD1', 0, 161),
            LogInternalStateElement('FLOAT','kalman','varD2', 0, 162),
            LogInternalStateElement('FLOAT','kalman','q0', 0, 163),
            LogInternalStateElement('FLOAT','kalman','q1', 0, 164),
            LogInternalStateElement('FLOAT','kalman','q2', 0, 165),
            LogInternalStateElement('FLOAT','kalman','q3', 0, 166),
            LogInternalStateElement('FLOAT','kalman','rtUpdate', 0, 167),
            LogInternalStateElement('FLOAT','kalman','rtPred', 0, 168),
            LogInternalStateElement('FLOAT','kalman','rtFinal', 0, 169),
            LogInternalStateElement('FLOAT','kalman_pred','predNX', 0, 170),
            LogInternalStateElement('FLOAT','kalman_pred','predNY', 0, 171),
            LogInternalStateElement('FLOAT','kalman_pred','measNX', 0, 172),
            LogInternalStateElement('FLOAT','kalman_pred','measNY', 0, 173),
            LogInternalStateElement('UINT8_T','lhFlasher','done', 0, 174),
            LogInternalStateElement('UINT32_T','lhFlasher','code', 0, 175),
            LogInternalStateElement('UINT8_T','lighthouse','validAngles', 0, 176),
            LogInternalStateElement('FLOAT','lighthouse','rawAngle0x', 0, 177),
            LogInternalStateElement('FLOAT','lighthouse','rawAngle0y', 0, 178),
            LogInternalStateElement('FLOAT','lighthouse','rawAngle1x', 0, 179),
            LogInternalStateElement('FLOAT','lighthouse','rawAngle1y', 0, 180),
            LogInternalStateElement('FLOAT','lighthouse','angle0x', 0, 181),
            LogInternalStateElement('FLOAT','lighthouse','angle0y', 0, 182),
            LogInternalStateElement('FLOAT','lighthouse','angle1x', 0, 183),
            LogInternalStateElement('FLOAT','lighthouse','angle1y', 0, 184),
            LogInternalStateElement('FLOAT','lighthouse','rawAngle0xlh2', 0, 185),
            LogInternalStateElement('FLOAT','lighthouse','rawAngle0ylh2', 0, 186),
            LogInternalStateElement('FLOAT','lighthouse','rawAngle1xlh2', 0, 187),
            LogInternalStateElement('FLOAT','lighthouse','rawAngle1ylh2', 0, 188),
            LogInternalStateElement('FLOAT','lighthouse','angle0x_0lh2', 0, 189),
            LogInternalStateElement('FLOAT','lighthouse','angle0y_0lh2', 0, 190),
            LogInternalStateElement('FLOAT','lighthouse','angle1x_0lh2', 0, 191),
            LogInternalStateElement('FLOAT','lighthouse','angle1y_0lh2', 0, 192),
            LogInternalStateElement('UINT8_T','lighthouse','comSync', 0, 193),
            LogInternalStateElement('UINT16_T','lighthouse','bsAvailable', 0, 194),
            LogInternalStateElement('UINT16_T','lighthouse','bsReceive', 0, 195),
            LogInternalStateElement('UINT16_T','lighthouse','bsActive', 0, 196),
            LogInternalStateElement('UINT16_T','lighthouse','bsCalUd', 0, 197),
            LogInternalStateElement('UINT16_T','lighthouse','bsCalCon', 0, 198),
            LogInternalStateElement('UINT8_T','lighthouse','status', 0, 199),
            LogInternalStateElement('FLOAT','lighthouse','posRt', 0, 200),
            LogInternalStateElement('FLOAT','lighthouse','estBs0Rt', 0, 201),
            LogInternalStateElement('FLOAT','lighthouse','estBs1Rt', 0, 202),
            LogInternalStateElement('FLOAT','lighthouse','x', 0, 203),
            LogInternalStateElement('FLOAT','lighthouse','y', 0, 204),
            LogInternalStateElement('FLOAT','lighthouse','z', 0, 205),
            LogInternalStateElement('FLOAT','lighthouse','delta', 0, 206),
            LogInternalStateElement('UINT16_T','lighthouse','bsGeoVal', 0, 207),
            LogInternalStateElement('UINT16_T','lighthouse','bsCalVal', 0, 208),
            LogInternalStateElement('UINT8_T','loco','mode', 0, 209),
            LogInternalStateElement('FLOAT','loco','spiWr', 0, 210),
            LogInternalStateElement('FLOAT','loco','spiRe', 0, 211),
            LogInternalStateElement('FLOAT','locSrv','x', 0, 212),
            LogInternalStateElement('FLOAT','locSrv','y', 0, 213),
            LogInternalStateElement('FLOAT','locSrv','z', 0, 214),
            LogInternalStateElement('FLOAT','locSrv','qx', 0, 215),
            LogInternalStateElement('FLOAT','locSrv','qy', 0, 216),
            LogInternalStateElement('FLOAT','locSrv','qz', 0, 217),
            LogInternalStateElement('FLOAT','locSrv','qw', 0, 218),
            LogInternalStateElement('UINT16_T','locSrvZ','tick', 0, 219),
            LogInternalStateElement('FLOAT','mag','x', 0, 220),
            LogInternalStateElement('FLOAT','mag','y', 0, 221),
            LogInternalStateElement('FLOAT','mag','z', 0, 222),
            LogInternalStateElement('UINT32_T','memTst','errCntW', 0, 223),
            LogInternalStateElement('UINT8_T','motion','motion', 0, 224),
            LogInternalStateElement('INT16_T','motion','deltaX', 0, 225),
            LogInternalStateElement('INT16_T','motion','deltaY', 0, 226),
            LogInternalStateElement('UINT16_T','motion','shutter', 0, 227),
            LogInternalStateElement('UINT8_T','motion','maxRaw', 0, 228),
            LogInternalStateElement('UINT8_T','motion','minRaw', 0, 229),
            LogInternalStateElement('UINT8_T','motion','Rawsum', 0, 230),
            LogInternalStateElement('UINT8_T','motion','outlierCount', 0, 231),
            LogInternalStateElement('UINT8_T','motion','squal', 0, 232),
            LogInternalStateElement('FLOAT','motion','std', 0, 233),
            LogInternalStateElement('UINT32_T','motor','m1', 0, 234),
            LogInternalStateElement('UINT32_T','motor','m2', 0, 235),
            LogInternalStateElement('UINT32_T','motor','m3', 0, 236),
            LogInternalStateElement('UINT32_T','motor','m4', 0, 237),
            LogInternalStateElement('INT32_T','motor','m1req', 0, 238),
            LogInternalStateElement('INT32_T','motor','m2req', 0, 239),
            LogInternalStateElement('INT32_T','motor','m3req', 0, 240),
            LogInternalStateElement('INT32_T','motor','m4req', 0, 241),
            LogInternalStateElement('FLOAT','navFilter','posX', 0, 242),
            LogInternalStateElement('FLOAT','navFilter','posY', 0, 243),
            LogInternalStateElement('FLOAT','navFilter','posZ', 0, 244),
            LogInternalStateElement('FLOAT','navFilter','accX', 0, 245),
            LogInternalStateElement('FLOAT','navFilter','accY', 0, 246),
            LogInternalStateElement('FLOAT','navFilter','accZ', 0, 247),
            LogInternalStateElement('FLOAT','navFilter','omegaX', 0, 248),
            LogInternalStateElement('FLOAT','navFilter','omegaY', 0, 249),
            LogInternalStateElement('FLOAT','navFilter','omegaZ', 0, 250),
            LogInternalStateElement('FLOAT','navFilter','Phi', 0, 251),
            LogInternalStateElement('FLOAT','navFilter','Theta', 0, 252),
            LogInternalStateElement('FLOAT','navFilter','Psi', 0, 253),
            LogInternalStateElement('FLOAT','navFilter','Px', 0, 254),
            LogInternalStateElement('FLOAT','navFilter','Pvx', 0, 255),
            LogInternalStateElement('FLOAT','navFilter','Pattx', 0, 256),
            LogInternalStateElement('UINT32_T','navFilter','nanCounter', 0, 257),
            LogInternalStateElement('FLOAT','navFilter','range', 0, 258),
            LogInternalStateElement('FLOAT','navFilter','procTimeFilter', 0, 259),
            LogInternalStateElement('UINT8_T','navFilter','recAnchorId', 0, 260),
            LogInternalStateElement('UINT16_T','oa','front', 0, 261),
            LogInternalStateElement('UINT16_T','oa','back', 0, 262),
            LogInternalStateElement('UINT16_T','oa','up', 0, 263),
            LogInternalStateElement('UINT16_T','oa','left', 0, 264),
            LogInternalStateElement('UINT16_T','oa','right', 0, 265),
            LogInternalStateElement('INT32_T','outlierf','lhWin', 0, 266),
            LogInternalStateElement('INT32_T','outlierf','bucket0', 0, 267),
            LogInternalStateElement('INT32_T','outlierf','bucket1', 0, 268),
            LogInternalStateElement('INT32_T','outlierf','bucket2', 0, 269),
            LogInternalStateElement('INT32_T','outlierf','bucket3', 0, 270),
            LogInternalStateElement('INT32_T','outlierf','bucket4', 0, 271),
            LogInternalStateElement('FLOAT','outlierf','accLev', 0, 272),
            LogInternalStateElement('FLOAT','outlierf','errD', 0, 273),
            LogInternalStateElement('FLOAT','pid_attitude','roll_outP', 0, 274),
            LogInternalStateElement('FLOAT','pid_attitude','roll_outI', 0, 275),
            LogInternalStateElement('FLOAT','pid_attitude','roll_outD', 0, 276),
            LogInternalStateElement('FLOAT','pid_attitude','roll_outFF', 0, 277),
            LogInternalStateElement('FLOAT','pid_attitude','pitch_outP', 0, 278),
            LogInternalStateElement('FLOAT','pid_attitude','pitch_outI', 0, 279),
            LogInternalStateElement('FLOAT','pid_attitude','pitch_outD', 0, 280),
            LogInternalStateElement('FLOAT','pid_attitude','pitch_outFF', 0, 281),
            LogInternalStateElement('FLOAT','pid_attitude','yaw_outP', 0, 282),
            LogInternalStateElement('FLOAT','pid_attitude','yaw_outI', 0, 283),
            LogInternalStateElement('FLOAT','pid_attitude','yaw_outD', 0, 284),
            LogInternalStateElement('FLOAT','pid_attitude','yaw_outFF', 0, 285),
            LogInternalStateElement('FLOAT','pid_rate','roll_outP', 0, 286),
            LogInternalStateElement('FLOAT','pid_rate','roll_outI', 0, 287),
            LogInternalStateElement('FLOAT','pid_rate','roll_outD', 0, 288),
            LogInternalStateElement('FLOAT','pid_rate','roll_outFF', 0, 289),
            LogInternalStateElement('FLOAT','pid_rate','pitch_outP', 0, 290),
            LogInternalStateElement('FLOAT','pid_rate','pitch_outI', 0, 291),
            LogInternalStateElement('FLOAT','pid_rate','pitch_outD', 0, 292),
            LogInternalStateElement('FLOAT','pid_rate','pitch_outFF', 0, 293),
            LogInternalStateElement('FLOAT','pid_rate','yaw_outP', 0, 294),
            LogInternalStateElement('FLOAT','pid_rate','yaw_outI', 0, 295),
            LogInternalStateElement('FLOAT','pid_rate','yaw_outD', 0, 296),
            LogInternalStateElement('FLOAT','pid_rate','yaw_outFF', 0, 297),
            LogInternalStateElement('FLOAT','pm','vbat', 0, 298),
            LogInternalStateElement('UINT16_T','pm','vbatMV', 0, 299),
            LogInternalStateElement('FLOAT','pm','extVbat', 0, 300),
            LogInternalStateElement('UINT16_T','pm','extVbatMV', 0, 301),
            LogInternalStateElement('FLOAT','pm','extCurr', 0, 302),
            LogInternalStateElement('FLOAT','pm','chargeCurrent', 0, 303),
            LogInternalStateElement('INT8_T','pm','state', 0, 304),
            LogInternalStateElement('UINT8_T','pm','batteryLevel', 0, 305),
            LogInternalStateElement('FLOAT','posCtl','targetVX', 0, 306),
            LogInternalStateElement('FLOAT','posCtl','targetVY', 0, 307),
            LogInternalStateElement('FLOAT','posCtl','targetVZ', 0, 308),
            LogInternalStateElement('FLOAT','posCtl','targetX', 0, 309),
            LogInternalStateElement('FLOAT','posCtl','targetY', 0, 310),
            LogInternalStateElement('FLOAT','posCtl','targetZ', 0, 311),
            LogInternalStateElement('FLOAT','posCtl','bodyVX', 0, 312),
            LogInternalStateElement('FLOAT','posCtl','bodyVY', 0, 313),
            LogInternalStateElement('FLOAT','posCtl','bodyX', 0, 314),
            LogInternalStateElement('FLOAT','posCtl','bodyY', 0, 315),
            LogInternalStateElement('FLOAT','posCtl','Xp', 0, 316),
            LogInternalStateElement('FLOAT','posCtl','Xi', 0, 317),
            LogInternalStateElement('FLOAT','posCtl','Xd', 0, 318),
            LogInternalStateElement('FLOAT','posCtl','Xff', 0, 319),
            LogInternalStateElement('FLOAT','posCtl','Yp', 0, 320),
            LogInternalStateElement('FLOAT','posCtl','Yi', 0, 321),
            LogInternalStateElement('FLOAT','posCtl','Yd', 0, 322),
            LogInternalStateElement('FLOAT','posCtl','Yff', 0, 323),
            LogInternalStateElement('FLOAT','posCtl','Zp', 0, 324),
            LogInternalStateElement('FLOAT','posCtl','Zi', 0, 325),
            LogInternalStateElement('FLOAT','posCtl','Zd', 0, 326),
            LogInternalStateElement('FLOAT','posCtl','Zff', 0, 327),
            LogInternalStateElement('FLOAT','posCtl','VXp', 0, 328),
            LogInternalStateElement('FLOAT','posCtl','VXi', 0, 329),
            LogInternalStateElement('FLOAT','posCtl','VXd', 0, 330),
            LogInternalStateElement('FLOAT','posCtl','VXff', 0, 331),
            LogInternalStateElement('FLOAT','posCtl','VYp', 0, 332),
            LogInternalStateElement('FLOAT','posCtl','VYi', 0, 333),
            LogInternalStateElement('FLOAT','posCtl','VYd', 0, 334),
            LogInternalStateElement('FLOAT','posCtl','VYff', 0, 335),
            LogInternalStateElement('FLOAT','posCtl','VZp', 0, 336),
            LogInternalStateElement('FLOAT','posCtl','VZi', 0, 337),
            LogInternalStateElement('FLOAT','posCtl','VZd', 0, 338),
            LogInternalStateElement('FLOAT','posCtl','VZff', 0, 339),
            LogInternalStateElement('FLOAT','posCtrlIndi','posRef_x', 0, 340),
            LogInternalStateElement('FLOAT','posCtrlIndi','posRef_y', 0, 341),
            LogInternalStateElement('FLOAT','posCtrlIndi','posRef_z', 0, 342),
            LogInternalStateElement('FLOAT','posCtrlIndi','velS_x', 0, 343),
            LogInternalStateElement('FLOAT','posCtrlIndi','velS_y', 0, 344),
            LogInternalStateElement('FLOAT','posCtrlIndi','velS_z', 0, 345),
            LogInternalStateElement('FLOAT','posCtrlIndi','velRef_x', 0, 346),
            LogInternalStateElement('FLOAT','posCtrlIndi','velRef_y', 0, 347),
            LogInternalStateElement('FLOAT','posCtrlIndi','velRef_z', 0, 348),
            LogInternalStateElement('FLOAT','posCtrlIndi','angS_roll', 0, 349),
            LogInternalStateElement('FLOAT','posCtrlIndi','angS_pitch', 0, 350),
            LogInternalStateElement('FLOAT','posCtrlIndi','angS_yaw', 0, 351),
            LogInternalStateElement('FLOAT','posCtrlIndi','angF_roll', 0, 352),
            LogInternalStateElement('FLOAT','posCtrlIndi','angF_pitch', 0, 353),
            LogInternalStateElement('FLOAT','posCtrlIndi','angF_yaw', 0, 354),
            LogInternalStateElement('FLOAT','posCtrlIndi','accRef_x', 0, 355),
            LogInternalStateElement('FLOAT','posCtrlIndi','accRef_y', 0, 356),
            LogInternalStateElement('FLOAT','posCtrlIndi','accRef_z', 0, 357),
            LogInternalStateElement('FLOAT','posCtrlIndi','accS_x', 0, 358),
            LogInternalStateElement('FLOAT','posCtrlIndi','accS_y', 0, 359),
            LogInternalStateElement('FLOAT','posCtrlIndi','accS_z', 0, 360),
            LogInternalStateElement('FLOAT','posCtrlIndi','accF_x', 0, 361),
            LogInternalStateElement('FLOAT','posCtrlIndi','accF_y', 0, 362),
            LogInternalStateElement('FLOAT','posCtrlIndi','accF_z', 0, 363),
            LogInternalStateElement('FLOAT','posCtrlIndi','accFT_x', 0, 364),
            LogInternalStateElement('FLOAT','posCtrlIndi','accFT_y', 0, 365),
            LogInternalStateElement('FLOAT','posCtrlIndi','accFT_z', 0, 366),
            LogInternalStateElement('FLOAT','posCtrlIndi','accErr_x', 0, 367),
            LogInternalStateElement('FLOAT','posCtrlIndi','accErr_y', 0, 368),
            LogInternalStateElement('FLOAT','posCtrlIndi','accErr_z', 0, 369),
            LogInternalStateElement('FLOAT','posCtrlIndi','phi_tilde', 0, 370),
            LogInternalStateElement('FLOAT','posCtrlIndi','theta_tilde', 0, 371),
            LogInternalStateElement('FLOAT','posCtrlIndi','T_tilde', 0, 372),
            LogInternalStateElement('FLOAT','posCtrlIndi','T_inner', 0, 373),
            LogInternalStateElement('FLOAT','posCtrlIndi','T_inner_f', 0, 374),
            LogInternalStateElement('FLOAT','posCtrlIndi','T_incremented', 0, 375),
            LogInternalStateElement('FLOAT','posCtrlIndi','cmd_phi', 0, 376),
            LogInternalStateElement('FLOAT','posCtrlIndi','cmd_theta', 0, 377),
            LogInternalStateElement('FLOAT','posEstAlt','estimatedZ', 0, 378),
            LogInternalStateElement('FLOAT','posEstAlt','estVZ', 0, 379),
            LogInternalStateElement('FLOAT','posEstAlt','velocityZ', 0, 380),
            LogInternalStateElement('UINT8_T','radio','rssi', 0, 381),
            LogInternalStateElement('UINT8_T','radio','isConnected', 0, 382),
            LogInternalStateElement('UINT16_T','range','front', 5000, 383),
            LogInternalStateElement('UINT16_T','range','back', 5000, 384),
            LogInternalStateElement('UINT16_T','range','up', 5000, 385),
            LogInternalStateElement('UINT16_T','range','left', 5000, 386),
            LogInternalStateElement('UINT16_T','range','right', 5000, 387),
            LogInternalStateElement('UINT16_T','range','zrange', 0, 388),
            LogInternalStateElement('UINT16_T','ranging','state', 0, 389),
            LogInternalStateElement('FLOAT','ring','fadeTime', 0, 390),
            LogInternalStateElement('FLOAT','sensfusion6','qw', 0, 391),
            LogInternalStateElement('FLOAT','sensfusion6','qx', 0, 392),
            LogInternalStateElement('FLOAT','sensfusion6','qy', 0, 393),
            LogInternalStateElement('FLOAT','sensfusion6','qz', 0, 394),
            LogInternalStateElement('FLOAT','sensfusion6','gravityX', 0, 395),
            LogInternalStateElement('FLOAT','sensfusion6','gravityY', 0, 396),
            LogInternalStateElement('FLOAT','sensfusion6','gravityZ', 0, 397),
            LogInternalStateElement('FLOAT','sensfusion6','accZbase', 0, 398),
            LogInternalStateElement('UINT8_T','sensfusion6','isInit', 0, 399),
            LogInternalStateElement('UINT8_T','sensfusion6','isCalibrated', 0, 400),
            LogInternalStateElement('FLOAT','sensorFilter','dxPx', 0, 401),
            LogInternalStateElement('FLOAT','sensorFilter','dyPx', 0, 402),
            LogInternalStateElement('FLOAT','sensorFilter','dxPxPred', 0, 403),
            LogInternalStateElement('FLOAT','sensorFilter','dyPxPred', 0, 404),
            LogInternalStateElement('FLOAT','sensorFilter','distPred', 0, 405),
            LogInternalStateElement('FLOAT','sensorFilter','distMeas', 0, 406),
            LogInternalStateElement('FLOAT','sensorFilter','baroHeight', 0, 407),
            LogInternalStateElement('FLOAT','sensorFilter','innoChFlow_x', 0, 408),
            LogInternalStateElement('FLOAT','sensorFilter','innoChFlow_y', 0, 409),
            LogInternalStateElement('FLOAT','sensorFilter','innoChTof', 0, 410),
            LogInternalStateElement('FLOAT','sensorFilter','distTWR', 0, 411),
            LogInternalStateElement('FLOAT','stabilizer','roll', 0, 412),
            LogInternalStateElement('FLOAT','stabilizer','pitch', 0, 413),
            LogInternalStateElement('FLOAT','stabilizer','yaw', 0, 414),
            LogInternalStateElement('FLOAT','stabilizer','thrust', 0, 415),
            LogInternalStateElement('FLOAT','stabilizer','rtStab', 0, 416),
            LogInternalStateElement('UINT32_T','stabilizer','intToOut', 0, 417),
            LogInternalStateElement('FLOAT','stateEstimate','x', 0, 418),
            LogInternalStateElement('FLOAT','stateEstimate','y', 0, 419),
            LogInternalStateElement('FLOAT','stateEstimate','z', 0, 420),
            LogInternalStateElement('FLOAT','stateEstimate','vx', 0, 421),
            LogInternalStateElement('FLOAT','stateEstimate','vy', 0, 422),
            LogInternalStateElement('FLOAT','stateEstimate','vz', 0, 423),
            LogInternalStateElement('FLOAT','stateEstimate','ax', 0, 424),
            LogInternalStateElement('FLOAT','stateEstimate','ay', 0, 425),
            LogInternalStateElement('FLOAT','stateEstimate','az', 0, 426),
            LogInternalStateElement('FLOAT','stateEstimate','roll', 0, 427),
            LogInternalStateElement('FLOAT','stateEstimate','pitch', 0, 428),
            LogInternalStateElement('FLOAT','stateEstimate','yaw', 0, 429),
            LogInternalStateElement('FLOAT','stateEstimate','qx', 0, 430),
            LogInternalStateElement('FLOAT','stateEstimate','qy', 0, 431),
            LogInternalStateElement('FLOAT','stateEstimate','qz', 0, 432),
            LogInternalStateElement('FLOAT','stateEstimate','qw', 0, 433),
            LogInternalStateElement('INT16_T','stateEstimateZ','x', 0, 434),
            LogInternalStateElement('INT16_T','stateEstimateZ','y', 0, 435),
            LogInternalStateElement('INT16_T','stateEstimateZ','z', 0, 436),
            LogInternalStateElement('INT16_T','stateEstimateZ','vx', 0, 437),
            LogInternalStateElement('INT16_T','stateEstimateZ','vy', 0, 438),
            LogInternalStateElement('INT16_T','stateEstimateZ','vz', 0, 439),
            LogInternalStateElement('INT16_T','stateEstimateZ','ax', 0, 440),
            LogInternalStateElement('INT16_T','stateEstimateZ','ay', 0, 441),
            LogInternalStateElement('INT16_T','stateEstimateZ','az', 0, 442),
            LogInternalStateElement('UINT32_T','stateEstimateZ','quat', 0, 443),
            LogInternalStateElement('INT16_T','stateEstimateZ','rateRoll', 0, 444),
            LogInternalStateElement('INT16_T','stateEstimateZ','ratePitch', 0, 445),
            LogInternalStateElement('INT16_T','stateEstimateZ','rateYaw', 0, 446),
            LogInternalStateElement('UINT16_T','supervisor','info', 0, 447),
            LogInternalStateElement('UINT8_T','sys','canfly', 0, 448),
            LogInternalStateElement('UINT8_T','sys','isFlying', 0, 449),
            LogInternalStateElement('UINT8_T','sys','isTumbled', 0, 450),
            LogInternalStateElement('INT8_T','sys','testLogParam', 0, 451),
            LogInternalStateElement('FLOAT','tdoa2','d7', 0, 452),
            LogInternalStateElement('FLOAT','tdoa2','d0', 0, 453),
            LogInternalStateElement('FLOAT','tdoa2','d1', 0, 454),
            LogInternalStateElement('FLOAT','tdoa2','d2', 0, 455),
            LogInternalStateElement('FLOAT','tdoa2','d3', 0, 456),
            LogInternalStateElement('FLOAT','tdoa2','d4', 0, 457),
            LogInternalStateElement('FLOAT','tdoa2','d5', 0, 458),
            LogInternalStateElement('FLOAT','tdoa2','d6', 0, 459),
            LogInternalStateElement('FLOAT','tdoa2','cc0', 0, 460),
            LogInternalStateElement('FLOAT','tdoa2','cc1', 0, 461),
            LogInternalStateElement('FLOAT','tdoa2','cc2', 0, 462),
            LogInternalStateElement('FLOAT','tdoa2','cc3', 0, 463),
            LogInternalStateElement('FLOAT','tdoa2','cc4', 0, 464),
            LogInternalStateElement('FLOAT','tdoa2','cc5', 0, 465),
            LogInternalStateElement('FLOAT','tdoa2','cc6', 0, 466),
            LogInternalStateElement('FLOAT','tdoa2','cc7', 0, 467),
            LogInternalStateElement('UINT16_T','tdoa2','dist7', 0, 468),
            LogInternalStateElement('UINT16_T','tdoa2','dist0', 0, 469),
            LogInternalStateElement('UINT16_T','tdoa2','dist1', 0, 470),
            LogInternalStateElement('UINT16_T','tdoa2','dist2', 0, 471),
            LogInternalStateElement('UINT16_T','tdoa2','dist3', 0, 472),
            LogInternalStateElement('UINT16_T','tdoa2','dist4', 0, 473),
            LogInternalStateElement('UINT16_T','tdoa2','dist5', 0, 474),
            LogInternalStateElement('UINT16_T','tdoa2','dist6', 0, 475),
            LogInternalStateElement('FLOAT','tdoaEngine','stRx', 0, 476),
            LogInternalStateElement('FLOAT','tdoaEngine','stEst', 0, 477),
            LogInternalStateElement('FLOAT','tdoaEngine','stTime', 0, 478),
            LogInternalStateElement('FLOAT','tdoaEngine','stFound', 0, 479),
            LogInternalStateElement('FLOAT','tdoaEngine','stCc', 0, 480),
            LogInternalStateElement('FLOAT','tdoaEngine','stHit', 0, 481),
            LogInternalStateElement('FLOAT','tdoaEngine','stMiss', 0, 482),
            LogInternalStateElement('FLOAT','tdoaEngine','cc', 0, 483),
            LogInternalStateElement('UINT16_T','tdoaEngine','tof', 0, 484),
            LogInternalStateElement('FLOAT','tdoaEngine','tdoa', 0, 485),
            LogInternalStateElement('UINT8_T','twr','rangingSuccessRate0', 0, 486),
            LogInternalStateElement('UINT8_T','twr','rangingPerSec0', 0, 487),
            LogInternalStateElement('UINT8_T','twr','rangingSuccessRate1', 0, 488),
            LogInternalStateElement('UINT8_T','twr','rangingPerSec1', 0, 489),
            LogInternalStateElement('UINT8_T','twr','rangingSuccessRate2', 0, 490),
            LogInternalStateElement('UINT8_T','twr','rangingPerSec2', 0, 491),
            LogInternalStateElement('UINT8_T','twr','rangingSuccessRate3', 0, 492),
            LogInternalStateElement('UINT8_T','twr','rangingPerSec3', 0, 493),
            LogInternalStateElement('UINT8_T','twr','rangingSuccessRate4', 0, 494),
            LogInternalStateElement('UINT8_T','twr','rangingPerSec4', 0, 495),
            LogInternalStateElement('UINT8_T','twr','rangingSuccessRate5', 0, 496),
            LogInternalStateElement('UINT8_T','twr','rangingPerSec5', 0, 497),
            LogInternalStateElement('FLOAT','ukf','rtUpdate', 0, 498),
            LogInternalStateElement('FLOAT','ukf','rtPred', 0, 499),
            LogInternalStateElement('FLOAT','ukf','rtBaro', 0, 500),
            LogInternalStateElement('FLOAT','ukf','rtFinal', 0, 501),
            LogInternalStateElement('FLOAT','ukf','rtApnd', 0, 502),
            LogInternalStateElement('FLOAT','ukf','rtRej', 0, 503),
            LogInternalStateElement('FLOAT','usd','spiWrBps', 0, 504),
            LogInternalStateElement('FLOAT','usd','spiReBps', 0, 505),
            LogInternalStateElement('FLOAT','usd','fatWrBps', 0, 506)
        ]
        self._param_toc = [
            ParamInternalStateElement('UINT8_T','activeMarker','front', 1, 0),
            ParamInternalStateElement('UINT8_T','activeMarker','back', 3, 1),
            ParamInternalStateElement('UINT8_T','activeMarker','left', 4, 2),
            ParamInternalStateElement('UINT8_T','activeMarker','right', 2, 3),
            ParamInternalStateElement('UINT8_T','activeMarker','mode', 0, 4),
            ParamInternalStateElement('UINT8_T','activeMarker','poll', 0, 5),
            ParamInternalStateElement('UINT8_T','amarkUartTest','trigger', 0, 6),
            ParamInternalStateElement('UINT8_T','BigQuadTest','pass', 0, 7),
            ParamInternalStateElement('UINT8_T','commander','enHighLevel', 0, 8),
            ParamInternalStateElement('FLOAT','cppm','rateRoll', 720, 9),
            ParamInternalStateElement('FLOAT','cppm','ratePitch', 720, 10),
            ParamInternalStateElement('FLOAT','cppm','angPitch', 50, 11),
            ParamInternalStateElement('FLOAT','cppm','angRoll', 50, 12),
            ParamInternalStateElement('FLOAT','cppm','rateYaw', 400, 13),
            ParamInternalStateElement('UINT16_T','cpu','flash', 0, 14),
            ParamInternalStateElement('UINT32_T','cpu','id0', 0, 15),
            ParamInternalStateElement('UINT32_T','cpu','id1', 0, 16),
            ParamInternalStateElement('UINT32_T','cpu','id2', 0, 17),
            ParamInternalStateElement('UINT16_T','crtpsrv','echoDelay', 0, 18),
            ParamInternalStateElement('FLOAT','ctrlAtt','tau_xy', 0, 19),
            ParamInternalStateElement('FLOAT','ctrlAtt','zeta_xy', 0, 20),
            ParamInternalStateElement('FLOAT','ctrlAtt','tau_z', 0, 21),
            ParamInternalStateElement('FLOAT','ctrlAtt','zeta_z', 0, 22),
            ParamInternalStateElement('FLOAT','ctrlAtt','tau_rp', 0, 23),
            ParamInternalStateElement('FLOAT','ctrlAtt','mixing_factor', 0, 24),
            ParamInternalStateElement('FLOAT','ctrlAtt','coll_fairness', 0, 25),
            ParamInternalStateElement('FLOAT','ctrlINDI','thrust_threshold', 0, 26),
            ParamInternalStateElement('FLOAT','ctrlINDI','bound_ctrl_input', 0, 27),
            ParamInternalStateElement('FLOAT','ctrlINDI','g1_p', 0, 28),
            ParamInternalStateElement('FLOAT','ctrlINDI','g1_q', 0, 29),
            ParamInternalStateElement('FLOAT','ctrlINDI','g1_r', 0, 30),
            ParamInternalStateElement('FLOAT','ctrlINDI','g2', 0, 31),
            ParamInternalStateElement('FLOAT','ctrlINDI','ref_err_p', 0, 32),
            ParamInternalStateElement('FLOAT','ctrlINDI','ref_err_q', 0, 33),
            ParamInternalStateElement('FLOAT','ctrlINDI','ref_err_r', 0, 34),
            ParamInternalStateElement('FLOAT','ctrlINDI','ref_rate_p', 0, 35),
            ParamInternalStateElement('FLOAT','ctrlINDI','ref_rate_q', 0, 36),
            ParamInternalStateElement('FLOAT','ctrlINDI','ref_rate_r', 0, 37),
            ParamInternalStateElement('FLOAT','ctrlINDI','act_dyn_p', 0, 38),
            ParamInternalStateElement('FLOAT','ctrlINDI','act_dyn_q', 0, 39),
            ParamInternalStateElement('FLOAT','ctrlINDI','act_dyn_r', 0, 40),
            ParamInternalStateElement('FLOAT','ctrlINDI','filt_cutoff', 0, 41),
            ParamInternalStateElement('FLOAT','ctrlINDI','filt_cutoff_r', 0, 42),
            ParamInternalStateElement('UINT8_T','ctrlINDI','outerLoopActive', 0, 43),
            ParamInternalStateElement('FLOAT','ctrlMel','kp_xy', 0, 44),
            ParamInternalStateElement('FLOAT','ctrlMel','kd_xy', 0, 45),
            ParamInternalStateElement('FLOAT','ctrlMel','ki_xy', 0, 46),
            ParamInternalStateElement('FLOAT','ctrlMel','i_range_xy', 0, 47),
            ParamInternalStateElement('FLOAT','ctrlMel','kp_z', 0, 48),
            ParamInternalStateElement('FLOAT','ctrlMel','kd_z', 0, 49),
            ParamInternalStateElement('FLOAT','ctrlMel','ki_z', 0, 50),
            ParamInternalStateElement('FLOAT','ctrlMel','i_range_z', 0, 51),
            ParamInternalStateElement('FLOAT','ctrlMel','mass', 0, 52),
            ParamInternalStateElement('FLOAT','ctrlMel','massThrust', 0, 53),
            ParamInternalStateElement('FLOAT','ctrlMel','kR_xy', 0, 54),
            ParamInternalStateElement('FLOAT','ctrlMel','kR_z', 0, 55),
            ParamInternalStateElement('FLOAT','ctrlMel','kw_xy', 0, 56),
            ParamInternalStateElement('FLOAT','ctrlMel','kw_z', 0, 57),
            ParamInternalStateElement('FLOAT','ctrlMel','ki_m_xy', 0, 58),
            ParamInternalStateElement('FLOAT','ctrlMel','ki_m_z', 0, 59),
            ParamInternalStateElement('FLOAT','ctrlMel','kd_omega_rp', 0, 60),
            ParamInternalStateElement('FLOAT','ctrlMel','i_range_m_xy', 0, 61),
            ParamInternalStateElement('FLOAT','ctrlMel','i_range_m_z', 0, 62),
            ParamInternalStateElement('UINT8_T','deck','bcActiveMarker', 0, 63),
            ParamInternalStateElement('UINT8_T','deck','bcAI', 0, 64),
            ParamInternalStateElement('UINT8_T','deck','bcBuzzer', 0, 65),
            ParamInternalStateElement('UINT8_T','deck','bcCPPM', 0, 66),
            ParamInternalStateElement('UINT8_T','deck','cpxOverUART2', 0, 67),
            ParamInternalStateElement('UINT8_T','deck','bcFlapperDeck', 0, 68),
            ParamInternalStateElement('UINT8_T','deck','bcFlow', 0, 69),
            ParamInternalStateElement('UINT8_T','deck','bcFlow2', 0, 70),
            ParamInternalStateElement('UINT8_T','deck','bcGTGPS', 0, 71),
            ParamInternalStateElement('UINT8_T','deck','bcLedRing', 0, 72),
            ParamInternalStateElement('UINT8_T','deck','bcLhTester', 0, 73),
            ParamInternalStateElement('UINT8_T','deck','bcLighthouse4', 0, 74),
            ParamInternalStateElement('UINT8_T','deck','bcDWM1000', 0, 75),
            ParamInternalStateElement('UINT8_T','deck','bcLoco', 0, 76),
            ParamInternalStateElement('UINT8_T','deck','bcMultiranger', 0, 77),
            ParamInternalStateElement('UINT8_T','deck','bcOA', 0, 78),
            ParamInternalStateElement('UINT8_T','deck','bcUSD', 0, 79),
            ParamInternalStateElement('UINT8_T','deck','bcZRanger', 0, 80),
            ParamInternalStateElement('UINT8_T','deck','bcZRanger2', 0, 81),
            ParamInternalStateElement('UINT32_T','firmware','revision0', 0, 82),
            ParamInternalStateElement('UINT16_T','firmware','revision1', 0, 83),
            ParamInternalStateElement('UINT8_T','firmware','modified', 0, 84),
            ParamInternalStateElement('FLOAT','flapper','ampsPerVolt', 0, 85),
            ParamInternalStateElement('FLOAT','flapper','filtAlpha', 0, 86),
            ParamInternalStateElement('INT8_T','flapper','motBiasRoll', 0, 87),
            ParamInternalStateElement('UINT8_T','flapper','servPitchNeutr', 0, 88),
            ParamInternalStateElement('UINT8_T','flapper','servYawNeutr', 0, 89),
            ParamInternalStateElement('UINT16_T','flapper','flapperMaxThrust', 0, 90),
            ParamInternalStateElement('UINT8_T','flightmode','althold', 0, 91),
            ParamInternalStateElement('UINT8_T','flightmode','poshold', 0, 92),
            ParamInternalStateElement('UINT8_T','flightmode','posSet', 0, 93),
            ParamInternalStateElement('UINT8_T','flightmode','yawMode', 0, 94),
            ParamInternalStateElement('UINT8_T','flightmode','stabModeRoll', 0, 95),
            ParamInternalStateElement('UINT8_T','flightmode','stabModePitch', 0, 96),
            ParamInternalStateElement('UINT8_T','flightmode','stabModeYaw', 0, 97),
            ParamInternalStateElement('UINT8_T','health','startPropTest', 0, 98),
            ParamInternalStateElement('UINT8_T','health','startBatTest', 0, 99),
            ParamInternalStateElement('UINT16_T','health','propTestPWMRatio', 0, 100),
            ParamInternalStateElement('UINT16_T','health','batTestPWMRatio', 0, 101),
            ParamInternalStateElement('FLOAT','hlCommander','vtoff', 0, 102),
            ParamInternalStateElement('FLOAT','hlCommander','vland', 0, 103),
            ParamInternalStateElement('UINT8_T','imu_sensors','BMP388', 0, 104),
            ParamInternalStateElement('FLOAT','imu_sensors','imuPhi', 0, 105),
            ParamInternalStateElement('FLOAT','imu_sensors','imuTheta', 0, 106),
            ParamInternalStateElement('FLOAT','imu_sensors','imuPsi', 0, 107),
            ParamInternalStateElement('UINT8_T','imu_sensors','BoschGyrSel', 0, 108),
            ParamInternalStateElement('UINT8_T','imu_sensors','BoschAccSel', 0, 109),
            ParamInternalStateElement('UINT8_T','imu_sensors','BMM150', 0, 110),
            ParamInternalStateElement('UINT8_T','imu_sensors','BMP285', 0, 111),
            ParamInternalStateElement('UINT8_T','imu_sensors','AK8963', 0, 112),
            ParamInternalStateElement('UINT8_T','imu_sensors','LPS25H', 0, 113),
            ParamInternalStateElement('UINT8_T','imu_tests','MPU6500', 0, 114),
            ParamInternalStateElement('UINT8_T','imu_tests','AK8963', 0, 115),
            ParamInternalStateElement('UINT8_T','imu_tests','LPS25H', 0, 116),
            ParamInternalStateElement('FLOAT','imu_tests','imuPhi', 0, 117),
            ParamInternalStateElement('FLOAT','imu_tests','imuTheta', 0, 118),
            ParamInternalStateElement('FLOAT','imu_tests','imuPsi', 0, 119),
            ParamInternalStateElement('UINT8_T','kalman','resetEstimation', 0, 120),
            ParamInternalStateElement('UINT8_T','kalman','robustTdoa', 0, 121),
            ParamInternalStateElement('UINT8_T','kalman','robustTwr', 0, 122),
            ParamInternalStateElement('FLOAT','kalman','pNAcc_xy', 0, 123),
            ParamInternalStateElement('FLOAT','kalman','pNAcc_z', 0, 124),
            ParamInternalStateElement('FLOAT','kalman','pNVel', 0, 125),
            ParamInternalStateElement('FLOAT','kalman','pNPos', 0, 126),
            ParamInternalStateElement('FLOAT','kalman','pNAtt', 0, 127),
            ParamInternalStateElement('FLOAT','kalman','mNBaro', 0, 128),
            ParamInternalStateElement('FLOAT','kalman','mNGyro_rollpitch', 0, 129),
            ParamInternalStateElement('FLOAT','kalman','mNGyro_yaw', 0, 130),
            ParamInternalStateElement('FLOAT','kalman','initialX', 0, 131),
            ParamInternalStateElement('FLOAT','kalman','initialY', 0, 132),
            ParamInternalStateElement('FLOAT','kalman','initialZ', 0, 133),
            ParamInternalStateElement('FLOAT','kalman','initialYaw', 0, 134),
            ParamInternalStateElement('FLOAT','kalman','maxPos', 0, 135),
            ParamInternalStateElement('FLOAT','kalman','maxVel', 0, 136),
            ParamInternalStateElement('UINT8_T','led','bitmask', 0, 137),
            ParamInternalStateElement('UINT8_T','lighthouse','method', 1, 138),
            ParamInternalStateElement('UINT8_T','lighthouse','bsCalibReset', 0, 139),
            ParamInternalStateElement('UINT8_T','lighthouse','systemType', 2, 140),
            ParamInternalStateElement('UINT16_T','lighthouse','bsAvailable', 0, 141),
            ParamInternalStateElement('FLOAT','lighthouse','sweepStd', 0, 142),
            ParamInternalStateElement('FLOAT','lighthouse','sweepStd2', 0, 143),
            ParamInternalStateElement('UINT16_T','lighthouse','lh2maxRate', 0, 144),
            ParamInternalStateElement('UINT8_T','lighthouse','enLhRawStream', 0, 145),
            ParamInternalStateElement('UINT8_T','loco','mode', 0, 146),
            ParamInternalStateElement('UINT8_T','locSrv','enRangeStreamFP32', 0, 147),
            ParamInternalStateElement('UINT8_T','locSrv','enLhAngleStream', 0, 148),
            ParamInternalStateElement('FLOAT','locSrv','extPosStdDev', 0, 149),
            ParamInternalStateElement('FLOAT','locSrv','extQuatStdDev', 0, 150),
            ParamInternalStateElement('UINT8_T','memTst','resetW', 0, 151),
            ParamInternalStateElement('UINT8_T','motion','disable', 0, 152),
            ParamInternalStateElement('UINT8_T','motion','adaptive', 0, 153),
            ParamInternalStateElement('FLOAT','motion','flowStdFixed', 2, 154),
            ParamInternalStateElement('UINT8_T','motorPowerSet','enable', 0, 155),
            ParamInternalStateElement('UINT16_T','motorPowerSet','m1', 0, 156),
            ParamInternalStateElement('UINT16_T','motorPowerSet','m2', 0, 157),
            ParamInternalStateElement('UINT16_T','motorPowerSet','m3', 0, 158),
            ParamInternalStateElement('UINT16_T','motorPowerSet','m4', 0, 159),
            ParamInternalStateElement('UINT16_T','multiranger','filterMask', 0, 160),
            ParamInternalStateElement('FLOAT','pid_attitude','roll_kp', 0, 161),
            ParamInternalStateElement('FLOAT','pid_attitude','roll_ki', 0, 162),
            ParamInternalStateElement('FLOAT','pid_attitude','roll_kd', 0, 163),
            ParamInternalStateElement('FLOAT','pid_attitude','roll_kff', 0, 164),
            ParamInternalStateElement('FLOAT','pid_attitude','pitch_kp', 0, 165),
            ParamInternalStateElement('FLOAT','pid_attitude','pitch_ki', 0, 166),
            ParamInternalStateElement('FLOAT','pid_attitude','pitch_kd', 0, 167),
            ParamInternalStateElement('FLOAT','pid_attitude','pitch_kff', 0, 168),
            ParamInternalStateElement('FLOAT','pid_attitude','yaw_kp', 0, 169),
            ParamInternalStateElement('FLOAT','pid_attitude','yaw_ki', 0, 170),
            ParamInternalStateElement('FLOAT','pid_attitude','yaw_kd', 0, 171),
            ParamInternalStateElement('FLOAT','pid_attitude','yaw_kff', 0, 172),
            ParamInternalStateElement('FLOAT','pid_attitude','yawMaxDelta', 0, 173),
            ParamInternalStateElement('INT8_T','pid_attitude','attFiltEn', 0, 174),
            ParamInternalStateElement('FLOAT','pid_attitude','attFiltCut', 0, 175),
            ParamInternalStateElement('FLOAT','pid_rate','roll_kp', 0, 176),
            ParamInternalStateElement('FLOAT','pid_rate','roll_ki', 0, 177),
            ParamInternalStateElement('FLOAT','pid_rate','roll_kd', 0, 178),
            ParamInternalStateElement('FLOAT','pid_rate','roll_kff', 0, 179),
            ParamInternalStateElement('FLOAT','pid_rate','pitch_kp', 0, 180),
            ParamInternalStateElement('FLOAT','pid_rate','pitch_ki', 0, 181),
            ParamInternalStateElement('FLOAT','pid_rate','pitch_kd', 0, 182),
            ParamInternalStateElement('FLOAT','pid_rate','pitch_kff', 0, 183),
            ParamInternalStateElement('FLOAT','pid_rate','yaw_kp', 0, 184),
            ParamInternalStateElement('FLOAT','pid_rate','yaw_ki', 0, 185),
            ParamInternalStateElement('FLOAT','pid_rate','yaw_kd', 0, 186),
            ParamInternalStateElement('FLOAT','pid_rate','yaw_kff', 0, 187),
            ParamInternalStateElement('INT8_T','pid_rate','rateFiltEn', 0, 188),
            ParamInternalStateElement('FLOAT','pid_rate','omxFiltCut', 0, 189),
            ParamInternalStateElement('FLOAT','pid_rate','omyFiltCut', 0, 190),
            ParamInternalStateElement('FLOAT','pid_rate','omzFiltCut', 0, 191),
            ParamInternalStateElement('FLOAT','pm','lowVoltage', 0, 192),
            ParamInternalStateElement('FLOAT','pm','criticalLowVoltage', 0, 193),
            ParamInternalStateElement('FLOAT','posCtlPid','xKp', 0, 194),
            ParamInternalStateElement('FLOAT','posCtlPid','xKi', 0, 195),
            ParamInternalStateElement('FLOAT','posCtlPid','xKd', 0, 196),
            ParamInternalStateElement('FLOAT','posCtlPid','xKff', 0, 197),
            ParamInternalStateElement('FLOAT','posCtlPid','yKp', 0, 198),
            ParamInternalStateElement('FLOAT','posCtlPid','yKi', 0, 199),
            ParamInternalStateElement('FLOAT','posCtlPid','yKd', 0, 200),
            ParamInternalStateElement('FLOAT','posCtlPid','yKff', 0, 201),
            ParamInternalStateElement('FLOAT','posCtlPid','zKp', 0, 202),
            ParamInternalStateElement('FLOAT','posCtlPid','zKi', 0, 203),
            ParamInternalStateElement('FLOAT','posCtlPid','zKd', 0, 204),
            ParamInternalStateElement('FLOAT','posCtlPid','zKff', 0, 205),
            ParamInternalStateElement('UINT16_T','posCtlPid','thrustBase', 0, 206),
            ParamInternalStateElement('UINT16_T','posCtlPid','thrustMin', 0, 207),
            ParamInternalStateElement('FLOAT','posCtlPid','rLimit', 0, 208),
            ParamInternalStateElement('FLOAT','posCtlPid','pLimit', 0, 209),
            ParamInternalStateElement('FLOAT','posCtlPid','xVelMax', 0, 210),
            ParamInternalStateElement('FLOAT','posCtlPid','yVelMax', 0, 211),
            ParamInternalStateElement('FLOAT','posCtlPid','zVelMax', 0, 212),
            ParamInternalStateElement('FLOAT','posCtrlIndi','K_xi_x', 0, 213),
            ParamInternalStateElement('FLOAT','posCtrlIndi','K_xi_y', 0, 214),
            ParamInternalStateElement('FLOAT','posCtrlIndi','K_xi_z', 0, 215),
            ParamInternalStateElement('FLOAT','posCtrlIndi','K_dxi_x', 0, 216),
            ParamInternalStateElement('FLOAT','posCtrlIndi','K_dxi_y', 0, 217),
            ParamInternalStateElement('FLOAT','posCtrlIndi','K_dxi_z', 0, 218),
            ParamInternalStateElement('FLOAT','posCtrlIndi','pq_clamping', 0, 219),
            ParamInternalStateElement('FLOAT','posEstAlt','estAlphaAsl', 0, 220),
            ParamInternalStateElement('FLOAT','posEstAlt','estAlphaZr', 0, 221),
            ParamInternalStateElement('FLOAT','posEstAlt','velFactor', 0, 222),
            ParamInternalStateElement('FLOAT','posEstAlt','velZAlpha', 0, 223),
            ParamInternalStateElement('FLOAT','posEstAlt','vAccDeadband', 0, 224),
            ParamInternalStateElement('UINT32_T','powerDist','idleThrust', 0, 225),
            ParamInternalStateElement('FLOAT','quadSysId','thrustToTorque', 0, 226),
            ParamInternalStateElement('FLOAT','quadSysId','pwmToThrustA', 0, 227),
            ParamInternalStateElement('FLOAT','quadSysId','pwmToThrustB', 0, 228),
            ParamInternalStateElement('FLOAT','quadSysId','armLength', 0, 229),
            ParamInternalStateElement('UINT8_T','ring','effect', 6, 230),
            ParamInternalStateElement('UINT32_T','ring','neffect', 0, 231),
            ParamInternalStateElement('UINT8_T','ring','solidRed', 20, 232),
            ParamInternalStateElement('UINT8_T','ring','solidGreen', 20, 233),
            ParamInternalStateElement('UINT8_T','ring','solidBlue', 20, 234),
            ParamInternalStateElement('UINT8_T','ring','headlightEnable', 0, 235),
            ParamInternalStateElement('FLOAT','ring','emptyCharge', 0, 236),
            ParamInternalStateElement('FLOAT','ring','fullCharge', 0, 237),
            ParamInternalStateElement('UINT32_T','ring','fadeColor', 0, 238),
            ParamInternalStateElement('FLOAT','ring','fadeTime', 0, 239),
            ParamInternalStateElement('FLOAT','sensfusion6','kp', 0, 240),
            ParamInternalStateElement('FLOAT','sensfusion6','ki', 0, 241),
            ParamInternalStateElement('FLOAT','sensfusion6','baseZacc', 0, 242),
            ParamInternalStateElement('UINT8_T','sound','effect', 0, 243),
            ParamInternalStateElement('UINT32_T','sound','neffect', 0, 244),
            ParamInternalStateElement('UINT16_T','sound','freq', 0, 245),
            ParamInternalStateElement('UINT8_T','stabilizer','estimator', 0, 246),
            ParamInternalStateElement('UINT8_T','stabilizer','controller', 0, 247),
            ParamInternalStateElement('UINT8_T','stabilizer','stop', 0, 248),
            ParamInternalStateElement('UINT8_T','supervisor','infdmp', 0, 249),
            ParamInternalStateElement('UINT8_T','syslink','probe', 0, 250),
            ParamInternalStateElement('UINT8_T','system','highlight', 0, 251),
            ParamInternalStateElement('UINT8_T','system','storageStats', 0, 252),
            ParamInternalStateElement('UINT8_T','system','storageReformat', 0, 253),
            ParamInternalStateElement('INT8_T','system','arm', 0, 254),
            ParamInternalStateElement('UINT8_T','system','taskDump', 0, 255),
            ParamInternalStateElement('INT8_T','system','selftestPassed', 0, 256),
            ParamInternalStateElement('UINT8_T','system','assertInfo', 0, 257),
            ParamInternalStateElement('UINT8_T','system','testLogParam', 0, 258),
            ParamInternalStateElement('UINT8_T','system','doAssert', 0, 259),
            ParamInternalStateElement('FLOAT','tdoa2','stddev', 0, 260),
            ParamInternalStateElement('FLOAT','tdoa3','stddev', 0, 261),
            ParamInternalStateElement('UINT8_T','tdoaEngine','logId', 0, 262),
            ParamInternalStateElement('UINT8_T','tdoaEngine','logOthrId', 0, 263),
            ParamInternalStateElement('UINT8_T','tdoaEngine','matchAlgo', 0, 264),
            ParamInternalStateElement('UINT8_T','ukf','resetEstimation', 0, 265),
            ParamInternalStateElement('UINT8_T','ukf','useNavFilter', 0, 266),
            ParamInternalStateElement('FLOAT','ukf','sigmaInitPos_xy', 0, 267),
            ParamInternalStateElement('FLOAT','ukf','sigmaInitPos_z', 0, 268),
            ParamInternalStateElement('FLOAT','ukf','sigmaInitVel', 0, 269),
            ParamInternalStateElement('FLOAT','ukf','sigmaInitAtt', 0, 270),
            ParamInternalStateElement('FLOAT','ukf','procNoiseA_h', 0, 271),
            ParamInternalStateElement('FLOAT','ukf','procNoiseA_z', 0, 272),
            ParamInternalStateElement('FLOAT','ukf','procNoiseVel_h', 0, 273),
            ParamInternalStateElement('FLOAT','ukf','procNoiseVel_z', 0, 274),
            ParamInternalStateElement('FLOAT','ukf','procNoiseRate_h', 0, 275),
            ParamInternalStateElement('FLOAT','ukf','procNoiseRate_z', 0, 276),
            ParamInternalStateElement('FLOAT','ukf','baroNoise', 0, 277),
            ParamInternalStateElement('FLOAT','ukf','qualityGateTof', 0, 278),
            ParamInternalStateElement('FLOAT','ukf','qualityGateFlow', 0, 279),
            ParamInternalStateElement('FLOAT','ukf','qualityGateTdoa', 0, 280),
            ParamInternalStateElement('FLOAT','ukf','qualityGateBaro', 0, 281),
            ParamInternalStateElement('FLOAT','ukf','qualityGateSweep', 0, 282),
            ParamInternalStateElement('FLOAT','ukf','ukfw0', 0, 283),
            ParamInternalStateElement('UINT8_T','usd','canLog', 0, 284),
            ParamInternalStateElement('UINT8_T','usd','logging', 0, 285),
            ParamInternalStateElement('UINT8_T','usec','reset', 0, 286),
            ParamInternalStateElement('FLOAT','velCtlPid','vxKp', 0, 287),
            ParamInternalStateElement('FLOAT','velCtlPid','vxKi', 0, 288),
            ParamInternalStateElement('FLOAT','velCtlPid','vxKd', 0, 289),
            ParamInternalStateElement('FLOAT','velCtlPid','vxKFF', 0, 290),
            ParamInternalStateElement('FLOAT','velCtlPid','vyKp', 0, 291),
            ParamInternalStateElement('FLOAT','velCtlPid','vyKi', 0, 292),
            ParamInternalStateElement('FLOAT','velCtlPid','vyKd', 0, 293),
            ParamInternalStateElement('FLOAT','velCtlPid','vyKFF', 0, 294),
            ParamInternalStateElement('FLOAT','velCtlPid','vzKp', 0, 295),
            ParamInternalStateElement('FLOAT','velCtlPid','vzKi', 0, 296),
            ParamInternalStateElement('FLOAT','velCtlPid','vzKd', 0, 297),
            ParamInternalStateElement('FLOAT','velCtlPid','vzKFF', 0, 298)
        ]
        self._log_blocks : dict[int, LogBlock] = {} 
        self._position_logger = None
        self._engine = None
        self._position_log_queue = None
        if log_file is not None:
            self._filename = log_file
            logging.info(f'logging positions at:\n{BOLD}{self._filename}{ENDC}')
            self._position_log_queue = Queue()
        self._setpoint_expire_timer = ResettableTimer(self.SETPOINT_EXPIRE_TIME, lambda: self._expire_setpoint())

    def log_toc(self):
        return list(map(lambda s: s.encoded(), self._log_toc))
    
    def param_toc(self):
        return list(map(lambda s: s.encoded(), self._param_toc))
    
    def get_param_value(self, index : int):
        return self._param_toc[index].get_value()
        
    def get_param_type(self, index : int):
        return self._param_toc[index].get_type()
    
    def set_param_value(self, index : int, new_value: bytearray):
        return self._param_toc[index].set_value(new_value)
    
    def get_log_toc_variable(self, index):
        if index < 0 or index >= len(self._log_toc):
            return None
        return self._log_toc[index]

    def add_block(self, id: int):
        if(id not in self._log_blocks):
            self._log_blocks[id] = LogBlock(id, self)
        return self._log_blocks[id]
    
    def delete_block(self, id: int):
        if(id in self._log_blocks):
            self.stop_block(id)
            del self._log_blocks[id]
            return 0
        return errno.ENOENT
    
    def start_block(self, id: int, period_in_ms: int, socket: socket.socket, addr):
        if(id in self._log_blocks):
            self._log_blocks[id].start(period_in_ms / 1000, socket, addr)
            return 0
        return errno.ENOENT
    
    def stop_block(self, id: int):
        if(id in self._log_blocks):
            self._log_blocks[id].stop()
            return 0
        return errno.ENOENT
    
    def stop_all_blocks(self):
        for id in self._log_blocks:
            self._log_blocks[id].stop()
            
    
    def set_hover_setpoint(self, vx, vy, yawrate, z):
        logging.debug(f'(HOV) = [vx-{vx:.2f}, vy-{vy:.2f}, yawrate-{yawrate:.2f} -- z-{z:.5f}]')
        self._start_engine()
        self._setpoint_expire_timer.reset()
        actual_z = self._log_toc[420]._value
        actual_yaw = self._log_toc[429]._value
        vx_rot, vy_rot = self._rotate_velocities(vx,vy,actual_yaw)
        self._engine.vx = vx_rot
        self._engine.vy = vy_rot
        self._engine.vz = self._position_to_velocity(z, actual_z, self.MAX_VELOCITY)
        self._engine.yawrate = yawrate
        logging.debug(f'(ENGINE) = [{self._engine.vx:.2f}, {self._engine.vy:.2f}, {self._engine.vz:.5f}, {self._engine.yawrate:.2f}]')

    def set_position_setpoint(self, x, y, z, yaw):
        logging.debug(f'(POS) = [x-{x:.2f}, y-{y:.2f}, z-{z:.2f} -- yaw-{yaw:.2f}]')
        self._start_engine()
        self._setpoint_expire_timer.reset()
        actual_x = self._log_toc[418]._value
        actual_y = self._log_toc[419]._value
        actual_z = self._log_toc[420]._value
        actual_yaw = self._log_toc[429]._value
        dx = abs(x-actual_x)
        dy = abs(y-actual_y)
        dz = abs(z-actual_z)
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        if distance != 0:
            self._engine.vx = self._position_to_velocity(x, actual_x, self.MAX_VELOCITY*dx/distance)
            self._engine.vy = self._position_to_velocity(y, actual_y, self.MAX_VELOCITY*dy/distance)
            self._engine.vz = self._position_to_velocity(z, actual_z, self.MAX_VELOCITY*dz/distance)
        self._engine.yawrate = self._position_to_velocity(yaw, actual_yaw, self.MAX_RATE)
    
    def set_velocity_world_setpoint(self, vx, vy, vz, yawrate):
        logging.debug(f'(VEL) = [vx={vx:.2f}, vy={vy:.2f}, vz={vz:.2f}, yawrate={yawrate:.2f}]')
        self._start_engine()
        self._setpoint_expire_timer.reset()
        actual_yaw = self._log_toc[429]._value
        vx_rot, vy_rot = self._rotate_velocities(vx,vy,actual_yaw)
        self._engine.vx = vx_rot
        self._engine.vy = vy_rot
        self._engine.vz = vz
        self._engine.yawrate = yawrate
    
    def set_stop_setpoint(self):
        self._start_engine()
        self._engine.z = 0
        self._engine.vx = 0
        self._engine.vy = 0
        self._engine.vz = 0
        self._engine.yawrate = 0
        self._stop_engine()
    
    def _expire_setpoint(self):
        self._start_engine()
        self._engine.vx = 0
        self._engine.vy = 0
        self._engine.vz = 0
        self._engine.yawrate = 0

    def _start_engine(self):
        if self._engine is None:
            self._engine = SimulatorEngine(self._log_toc, self._position_log_queue)
            self._initialize_position()
            self._engine.start()
            if self._position_log_queue is not None:
                self._position_logger = PositionLogger(self._position_log_queue, self._filename)
                self._position_logger.start()

    def _stop_engine(self):
        if self._engine is not None:
            self._engine.stop()
        if self._position_logger is not None:
            self._position_logger.stop()
        self.stop_all_blocks()

    def _rotate_velocities(self, vx, vy, yaw_deg):
        yaw_rad = math.radians(yaw_deg)
        vx_rot = vx * math.cos(yaw_rad) - vy * math.sin(yaw_rad)
        vy_rot = vx * math.sin(yaw_rad) + vy * math.cos(yaw_rad)
        return vx_rot, vy_rot

    def _position_to_velocity(self, target_position, actual_value, max_speed):
        delta_max = max_speed * self.SETPOINT_EXPIRE_TIME
        delta_fin = min(delta_max, abs(target_position - actual_value))
        sign = abs(target_position - actual_value) / (target_position - actual_value) if target_position != actual_value else 0
        return (delta_fin / self.SETPOINT_EXPIRE_TIME)*sign

    def _initialize_position(self):
        self._log_toc[118].update_value(self._param_toc[131]._value)
        self._log_toc[119].update_value(self._param_toc[132]._value)
        self._log_toc[120].update_value(self._param_toc[133]._value)
        self._log_toc[129].update_value(self._param_toc[134]._value)

class LogInternalStateElement:
    def __init__(self, type, group, name, default, index):
        self._encoded = LOG_TYPES[type][0] + f'{group}\x00{name}\x00'.encode('ISO-8859-1')
        self._value = default
        self._type = type
        self._fetch_type = type
        self._group = group
        self._name = name
        self._index = index
    
    def encoded(self):
        return self._encoded
    
    def pack(self):
        return struct.pack(LOG_TYPES[self._fetch_type][1], self._value)

    def update_value(self, value):
        self._value = value 
    
    def set_fetched_type(self, type: int):
        for t, type_info in LOG_TYPES.items():
            if type_info[2] == type:
                self._fetch_type = t
                break

class LogBlock():
    def __init__(self, id, simulator: CrazyflieSimulator):
        self._id = id
        self._variables : list[LogInternalStateElement] = []
        self._simulator = simulator
        self._started = False
        self._deamon = None
        self._socket = None
        self._addr = None
        
    def add_variable(self, var_id, stored_type, fetched_type):
        toc_var : LogInternalStateElement = self._simulator.get_log_toc_variable(var_id)
        if toc_var != None and LOG_TYPES[toc_var._type][2] == stored_type:
            if(fetched_type != stored_type):
                toc_var.set_fetched_type(fetched_type)
            self._variables.append(toc_var)
    
    def start(self, period_in_s, socket: socket.socket, addr):
        if not self._started:
            self._started = True
            self._period_in_s = period_in_s
            self._socket = socket
            self._addr = addr
            self._deamon = LogBlockDeamon(self)
            self._deamon.start()
            logging.warn(f'Logging started for block {self._id}')
        else:
            logging.debug(f'Block {self._id} already started')

    def stop(self):
        if self._started:
            self._deamon.stop()
            self._started = False
            self._deamon = None
            # self._socket = None
            # self._addr = None
            logging.warn(f'Logging stopped for block {self._id}')
        else:
            logging.debug(f'Block {self._id} was not started')

    def send_log(self):
        if self._socket is not None and self._addr is not None:
            logging.debug(f'Send LOG for block {self._id}')
            pk = CRTPPacket()
            pk.port = CRTPPort.LOGGING
            pk.channel = 2
            pk.data = self._get_encoded_data()
            raw = (pk.header,) + struct.unpack('B' * len(pk.data), pk.data)
            self._socket.sendto(bytes(raw), self._addr)
        else:
            logging.error(f'{ERROR}No socket or address, cannot LOG for block {self._id}{ENDC}')

    def _get_encoded_data(self):
        id = bytes((self._id,))             # 1 Byte
        timestamp = self._get_timestamp()   # 3 Byte
        log_data = self._get_log_data()     # up to 27 Bytes
        return id + timestamp + log_data
    
    def _get_timestamp(self):
        current_timestamp = int(time.time())
        packed_timestamp = struct.pack('<BBB', (current_timestamp >> 16) & 0xFF, (current_timestamp >> 8) & 0xFF, current_timestamp & 0xFF)
        return packed_timestamp

    def _get_log_data(self):
        data = bytes()
        pippo : list[str] = []
        for variable in self._variables:
            if variable._name == 'x' or variable._name == 'y' or variable._name == 'z':
                pippo.append(f'{variable._name}:{round(variable._value, 3)}')
            data += variable.pack()
        if len(pippo) > 0:
            pass
        return data

class LogBlockDeamon(Thread):
    def __init__(self, block: LogBlock):
        Thread.__init__(self)
        self._block = block
        self._stop = False

    def run(self):
        while not self._stop:
            time.sleep(self._block._period_in_s)
            self._block.send_log()
    
    def stop(self):
        self._stop = True

class ParamInternalStateElement:
    def __init__(self, type, group, name, default, index):
        self._encoded = PARAM_TYPES[type][0] + f'{group}\x00{name}'.encode('ISO-8859-1')
        self._value = default
        self._type = type
        self._group = group
        self._name = name
        self._index = index
    
    def encoded(self):
        return self._encoded
    
    def update_value(self, value):
        self._value = value 

    def get_value(self):
        return bytearray(struct.pack(PARAM_TYPES[self._type][1], self._value))
    
    def get_type(self):
        return bytearray(PARAM_TYPES[self._type][0])
    
    def set_value(self, new_value: bytearray):
        self.update_value(struct.unpack(PARAM_TYPES[self._type][1], new_value)[0])
        return bytearray(struct.pack(PARAM_TYPES[self._type][1], self._value))
        
class SimulatorEngine(Thread):
    def __init__(self, log_toc : list[LogInternalStateElement], queue: Queue):
        Thread.__init__(self)
        self._stop = False
        self._clock = 0.03
        self.vx = 0
        self.vy = 0
        self.vz = 0
        self.yawrate = 0
        self._var_map = {
            'x' : log_toc[418],
            'y' : log_toc[419],
            'z' : log_toc[420],
            'vx' : log_toc[421],
            'vy' : log_toc[422],
            'vz' : log_toc[423],
            'ax' : log_toc[424],
            'ay' : log_toc[425],
            'az' : log_toc[426],
            'yaw' : log_toc[429],
        }
        if queue is None:
            self._is_logging = False
        else:
            self._is_logging = True
            self._queue = queue
    
    def run(self):
        while not self._stop:
            cycle_start = time.time()
            time.sleep(self._clock)
            cycle_delta = time.time() - cycle_start
            x = self.vx * cycle_delta + self._var_map['x']._value
            y = self.vy * cycle_delta + self._var_map['y']._value
            z = self.vz * cycle_delta + self._var_map['z']._value
            yaw = self.yawrate * cycle_delta + self._var_map['yaw']._value 
            ax = (self.vx - self._var_map['vx']._value) / cycle_delta
            ay = (self.vy - self._var_map['vy']._value) / cycle_delta
            az = (self.vz - self._var_map['vz']._value) / cycle_delta
            self._var_map['x'].update_value(x)
            self._var_map['y'].update_value(y)
            self._var_map['z'].update_value(z)
            self._var_map['vx'].update_value(self.vx)
            self._var_map['vy'].update_value(self.vy)
            self._var_map['vz'].update_value(self.vz)
            self._var_map['ax'].update_value(ax)
            self._var_map['ay'].update_value(ay)
            self._var_map['az'].update_value(az)
            self._var_map['yaw'].update_value(yaw)
            if self._is_logging:
                self._queue.put([x, y, z, self.vx, self.vy, self.vz, ax, ay, az, yaw, cycle_start, cycle_delta])
            # cycle_start = time.time()
            # x = self.vx * self._clock + self._var_map['x']._value
            # y = self.vy * self._clock + self._var_map['y']._value
            # z = self.vz * self._clock + self._var_map['z']._value
            # yaw = self.yawrate * self._clock + self._var_map['yaw']._value 
            # ax = (self.vx - self._var_map['vx']._value) / self._clock
            # ay = (self.vy - self._var_map['vy']._value) / self._clock
            # az = (self.vz - self._var_map['vz']._value) / self._clock
            # self._var_map['x'].update_value(x)
            # self._var_map['y'].update_value(y)
            # self._var_map['z'].update_value(z)
            # self._var_map['vx'].update_value(self.vx)
            # self._var_map['vy'].update_value(self.vy)
            # self._var_map['vz'].update_value(self.vz)
            # self._var_map['ax'].update_value(ax)
            # self._var_map['ay'].update_value(ay)
            # self._var_map['az'].update_value(az)
            # self._var_map['yaw'].update_value(yaw)
            # if self._is_logging:
            #     self._queue.put([x, y, z, self.vx, self.vy, self.vz, ax, ay, az, yaw])
            # cycle_delta = time.time() - cycle_start 
            # if cycle_delta < self._clock:
            #     time.sleep(self._clock - cycle_delta)
            # else:
            #     logging.warn(f'{WARNING}ENGINE clock overflow{ENDC}')
    
    def stop(self):
        self._stop = True

class PositionLogger(Thread):
    def __init__(self, queue: Queue, filename):
        Thread.__init__(self)
        self._queue = queue
        self._stop = False
        self._filename = filename
        self._write_to_csv([['x','y','z','vx','vy','vz','ax','ay','az','yaw','time', 'delta']])

    def run(self):
        while not self._stop:
            time.sleep(5)

            # Process the data
            size = self._queue.qsize()
            data_to_process = []
            while len(data_to_process) < size:
                data_to_process.append(self._queue.get())
            self._write_to_csv(data_to_process)

        data_to_process = []
        # Flush last data
        while self._queue.qsize() > 0:
            data_to_process.append(self._queue.get())
        self._write_to_csv(data_to_process)
        
    def _write_to_csv(self, data):
        with open(self._filename, 'a+', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(data)

    def stop(self):
        self._stop = True

class ResettableTimer:
    def __init__(self, interval, function):
        self._interval = interval
        self._function = function
        self._timer = Timer(self._interval, self._function)

    def start(self):
        self._timer.start()

    def reset(self):
        self._timer.cancel()
        self._timer = Timer(self._interval, self._function)
        self.start()

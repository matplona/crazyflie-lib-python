from functools import reduce
import logging
import sys
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import cflib.crtp

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
sys.path.append('c:\\Users\\plona\\PC\\TESI\\crazyflie-lib-python')

from multiprocessing import current_process
import time
from math import sqrt
from cflib.positioning.motion_commander import MotionCommander
from environment import grid, origin_dx, origin_dy, landmarks

print(current_process().pid)
input('start')

next_landmark = 0
way_points = {}
is_moving = False
next_point =  {}
for row in range(len(grid)):
        way_points[row] = {}
        for col in range(len(grid[0])):
            way_points[row][col] = False

def wait_for_position_estimator(scf):
    print('Waiting for estimator to find position...')

    log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
    log_config.add_variable('kalman.varPX', 'float')
    log_config.add_variable('kalman.varPY', 'float')
    log_config.add_variable('kalman.varPZ', 'float')

    var_y_history = [1000] * 10
    var_x_history = [1000] * 10
    var_z_history = [1000] * 10

    threshold = 0.001

    with SyncLogger(scf, log_config) as logger:
        for log_entry in logger:
            data = log_entry[1]

            var_x_history.append(data['kalman.varPX'])
            var_x_history.pop(0)
            var_y_history.append(data['kalman.varPY'])
            var_y_history.pop(0)
            var_z_history.append(data['kalman.varPZ'])
            var_z_history.pop(0)

            min_x = min(var_x_history)
            max_x = max(var_x_history)
            min_y = min(var_y_history)
            max_y = max(var_y_history)
            min_z = min(var_z_history)
            max_z = max(var_z_history)
            if (max_x - min_x) < threshold and (
                    max_y - min_y) < threshold and (
                    max_z - min_z) < threshold:
                break

def reset_estimator(scf):
    cf = scf.cf
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')
    wait_for_position_estimator(cf)

def predicate(state):
    global is_moving, next_point, next_landmark
    curr = get_grid_point(state) 
    return not is_moving and (next_point == {} or (curr["row"] == next_point["row"] and curr["col"] == next_point["col"])) and next_landmark < 4

def visited(row, col):
    global way_points
    return way_points[row][col]

def visit(row, col, z):
    global way_points, next_point
    next_point["row"] = row
    next_point["col"] = col
    next_point["z"] = z
    way_points[row][col]=True

def in_range(curr: dict, row, col):
    in_range_row = row >= curr['row'] -1 and row <= curr['row'] +1
    in_range_col = col >= curr['col'] -1 and col <= curr['col'] +1
    return in_range_col and in_range_row

def is_fly_allowed(row, col):
    global grid
    return grid[row][col] < 9

def get_grid_point(state : dict):
    global grid, origin_dx, origin_dy
    x = state['stateEstimate.x'] - origin_dx
    y = state['stateEstimate.y'] - origin_dy
    z = state['stateEstimate.z'] - 0.3
    return { 
        'col' : int(round(x * 10, 0)),
        'row' : int(round(y * 10, 0)),
        'z': int(round(z * 10, 0))
    }

def compute_distance(row, col):
    global landmarks, next_landmark
    row_span = abs(landmarks[next_landmark]['row'] - row)
    col_span = abs(landmarks[next_landmark]['col'] - col)
    return sqrt(row_span*row_span + col_span*col_span)

def get_next_cell(state: dict):
    global grid, next_landmark
    curr = get_grid_point(state)
    min = 500
    min_point = {
        'z': curr['z'],
        'x': curr['col'],
        'y': curr['row']
    }
    for row in range(len(grid)):
        for col in range(len(grid[0])):
            if is_fly_allowed(row, col) and in_range(curr, row, col) and not visited(row, col):
                distance = compute_distance(row, col)
                if distance < min:
                    min = distance
                    min_point['row'] = row
                    min_point['col'] = col
                    min_point['z'] = grid[row][col]
    
    if 'row' not in min_point or 'row' not in min_point:
        next_landmark = 5
        return None
    
    logging.warning(f"({curr['row']}, {curr['col']}, {curr['z']}) -> ({min_point['row']}, {min_point['col']}, {min_point['z']})")
    visit(min_point['row'], min_point['col'], min_point['z'])
    return {
        'z': min_point['z'],
        'x': (min_point['col'] - curr['col']) / 9.8,
        'y': (min_point['row'] - curr['row']) / 9.8
    }

def adjust_height(curr_height, next_cell_height):
    target = (next_cell_height / 10) + 0.3
    return target - curr_height

def callback_multi(timestamp, data : dict, logconfig):
    if len(data) == 0:
        return
    global gmc
    front = data['range.front']
    back = data['range.back']
    right = data['range.right']
    left = data['range.left']
    vx = get_vx(front, back)
    vy = get_vy(right, left)
    if gmc == None or (vx == 0 and vy == 0):
        return
    if is_safe(back, front, left, right):
        gmc.start_linear_motion(vx, vy, 0)
    else:
        gmc.land()

class ActionLimit():
    MIN = 60
    MAX = 100
    SAFE = 50

class VelocityLimit():
    MIN = 0
    MAX = 1

def compute_velocity(value) -> float:
    value = ActionLimit.MIN if value < ActionLimit.MIN else value
    value = ActionLimit.MAX if value > ActionLimit.MAX else value
    return (((value - ActionLimit.MAX) * (VelocityLimit.MAX - VelocityLimit.MIN)) / (ActionLimit.MIN - ActionLimit.MAX)) + VelocityLimit.MIN

def get_vx(front, back)-> float:
    vx = 0
    if(ActionLimit.MIN <= back <= ActionLimit.MAX):
        vx += compute_velocity(back)
    if(ActionLimit.MIN <= front <= ActionLimit.MAX):
        vx -= compute_velocity(front)
    return vx

def get_vy(right, left)-> float:
    vy = 0
    if(ActionLimit.MIN <= right <= ActionLimit.MAX):
        vy += compute_velocity(right)
    if(ActionLimit.MIN <= left <= ActionLimit.MAX):
        vy -= compute_velocity(left)
    return vy

def is_safe(*args):
    return reduce(lambda acc, arg: acc and arg>=ActionLimit.SAFE, args, True)

def callback(timestamp, data : dict, logconfig ):
    if len(data) == 0:
        return
    global is_moving, next_landmark, next_point, gmc, landmarks
    if gmc == None or not predicate(data):
       return
    logging.warning(f"data: ({origin_dx-data['stateEstimate.x']}, {origin_dy -data['stateEstimate.y']}, {data['stateEstimate.z']}) {is_moving}")
    is_moving = True
    next_point = {}
    next_cell = get_next_cell(data)
    if next_cell == None: 
        return
    adjusted_height = adjust_height(data['stateEstimate.z'], next_cell['z'])
    logging.warning(f"moving by: ({next_cell['x']}, {next_cell['y']}, {adjusted_height})")

    if next_cell['x'] == 0 and next_cell['y'] == 0 and adjusted_height == 0:
        print('not moving')
    else:
        mc.move_distance(next_cell['x'], next_cell['y'], adjusted_height)
        time.sleep(0.2)

    if next_cell['z'] == 1:
        z = data['stateEstimate.z'] + adjusted_height
        logging.info(f"landing: down by {z}")
        mc.move_distance(0,0, -z)
        logging.info(f"landed")
        time.sleep(2)
        next_landmark = next_landmark + 1
        if next_landmark < 4:
            time.sleep(1)
            logging.info(f"taking off: up by {z}")
            mc.move_distance(0,0, z)
            logging.info(f"took off")
    is_moving = False

gmc : MotionCommander= None
if __name__ == '__main__':
    logging.basicConfig(level=logging.WARN)
    uri = 'udp://127.0.0.1:1808'
    cflib.crtp.init_drivers()
    with SyncCrazyflie(uri, cf=Crazyflie()) as scf:
        reset_estimator(scf)
        log1 = LogConfig(name='State estimate', period_in_ms=100)
        log2 = LogConfig(name='Range', period_in_ms= 11)
        log1.add_variable('stateEstimate.x', 'float')
        log1.add_variable('stateEstimate.y', 'float')
        log1.add_variable('stateEstimate.z', 'float')
        
        log2.add_variable("range.front", 'uint16_t')
        log2.add_variable("range.back", 'uint16_t')
        log2.add_variable("range.right", 'uint16_t')
        log2.add_variable("range.left", 'uint16_t')
        log2.add_variable("range.up", 'uint16_t')

        scf.cf.log.add_config(log1)
        scf.cf.log.add_config(log2)
        
        log1.data_received_cb.add_callback(callback)
        log2.data_received_cb.add_callback(callback_multi)
        
        is_moving = True
        log1.start()
        with MotionCommander(scf.cf) as mc:
            gmc = mc
            time.sleep(1)
            is_moving = False
            while next_landmark < 4:
                time.sleep(1)
                
            log1.stop()
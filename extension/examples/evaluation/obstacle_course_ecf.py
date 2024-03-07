import logging
import sys
sys.path.append('c:\\Users\\plona\\PC\\TESI\\crazyflie-lib-python')

from multiprocessing import current_process
import time
from math import sqrt
from extension.extended_crazyflie import ExtendedCrazyFlie
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
    x = state['x'] - origin_dx
    y = state['y'] - origin_dy
    z = state['z'] - 0.3
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

def callback(state: dict, mc : MotionCommander):
    global is_moving, next_landmark, next_point
    is_moving = True
    next_point = {}
    next_cell = get_next_cell(state)
    if next_cell == None: 
        return
    adjusted_height = adjust_height(state['z'], next_cell['z'])
    logging.info(f"adjusted_height: {adjusted_height}")

    if next_cell['x'] == 0 and next_cell['y'] == 0 and adjusted_height == 0:
        print('not moving')
    else:
        mc.move_distance(next_cell['x'], next_cell['y'], adjusted_height)
        time.sleep(0.2)

    if next_cell['z'] == 1:
        z = state['z'] + adjusted_height
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

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    uri = 'udp://127.0.0.1:1808'
    with ExtendedCrazyFlie(uri) as ecf:
        with MotionCommander(ecf.cf) as mc:
            time.sleep(1)
            ecf.coordination_manager.observe(
                ecf.state_estimate.observable_name,
                callback,
                predicate,
                [mc]
            )
            while next_landmark < 4:
                time.sleep(1)
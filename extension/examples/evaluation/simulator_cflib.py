import logging
import sys
sys.path.append('c:\\Users\\plona\\PC\\TESI\\crazyflie-lib-python')

import time
from math import sqrt
from cflib.utils import uri_helper
from extension.extended_crazyflie import ExtendedCrazyFlie
from cflib.positioning.motion_commander import MotionCommander
from environment import grid, origin_dx, origin_dy, landmarks

next_landmark = 0
way_points = {}
is_moving = False
for row in range(len(grid)):
        way_points[row] = {}
        for col in range(len(grid[0])):
            way_points[row][col] = False

def predicate(state):
    global is_moving
    return not is_moving

def visited(row, col):
    global way_points
    return way_points[row][col]

def visit(row, col):
    global way_points
    way_points[row][col]=True

def in_range(curr: dict, row, col):
    in_range_row = row >= curr['row'] -1 and row <= curr['row'] +1
    in_range_col = col >= curr['col'] -1 and col <= curr['col'] +1
    return in_range_col and in_range_row

def is_fly_allowed(row, col):
    global grid
    return grid[row][col] != 8 and grid[row][col] != 9

def get_grid_point(state : dict):
    global grid, origin_dx, origin_dy
    x = state['x'] - origin_dx
    y = state['y'] - origin_dy
    return {
        'col' : int(x * 10 // 1),
        'row' : int(y * 10 // 1),
        'state': grid[int(y * 10 // 1)][int(x * 10 // 1)]
    }

def compute_distance(row, col):
    global landmarks, next_landmark
    row_span = abs(landmarks[next_landmark]['row'] - row)
    col_span = abs(landmarks[next_landmark]['col'] - col)
    return sqrt(row_span*row_span + col_span*col_span)

def get_next_cell(state: dict):
    global grid
    curr = get_grid_point(state)
    min = 500
    min_point = {
        'state': curr['state'],
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
    visit(min_point['row'], min_point['col'])
    return {
        'state': min_point['state'],
        'x': (min_point['col'] - curr['col']) / 10,
        'y': (min_point['row'] - curr['row']) / 10
    }

def adjust_height(curr_height, next_cell_type):
    target_height = 0.5
    if next_cell_type == 5:
        target_height = 0.25
    if next_cell_type == 6:
        target_height = 0.75
    return target_height - curr_height

def callback(state: dict, mc : MotionCommander ):
    global is_moving, next_landmark
    is_moving = True
    next_cell = get_next_cell(state)
    adjusted_height = adjust_height(state['z'], next_cell['state'])
    if adjusted_height >= 0.1 or adjusted_height <= -0.1:
        mc.move_distance(0,0, state['z'] + adjusted_height)
        time.sleep(0.2)
    if next_cell['x'] == 0 and next_cell['y'] == 0:
        print('not moving')
    else:
        mc.move_distance(next_cell['x'], next_cell['y'], 0)

    if next_cell['state'] == 2 or next_cell['state'] == 3:
        mc.land()
        time.sleep(2)
        next_landmark = next_landmark + 1
        if next_cell['state'] == 2 :
            time.sleep(1)
            mc.take_off(0.5)
    is_moving = False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    uri = 'udp://127.0.0.1:1808'
    with ExtendedCrazyFlie(uri) as ecf:
        input('run')
        with MotionCommander(ecf.cf) as mc:
            time.sleep(1)
            ecf.state_estimate.record_positions(10)
            ecf.coordination_manager.observe(
                ecf.state_estimate.observable_name,
                callback,
                predicate,
                [mc]
            )
            time.sleep(10)
            ecf.state_estimate.plot_positions_3D()
            # while next_landmark < 4:
            #     time.sleep(1)
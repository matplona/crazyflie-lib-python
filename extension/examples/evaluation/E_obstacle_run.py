import sys
 
# setting path
sys.path.append('c:\\Users\\plona\\PC\\TESI\\crazyflie-lib-python')

import logging
import time
from math import sqrt
from cflib.utils import uri_helper
from extension.decks.deck import DeckType
from extension.decks.lighthouse.lighthouse import Lighthouse
from extension.extended_crazyflie import ExtendedCrazyFlie
from cflib.positioning.motion_commander import MotionCommander

grid = [
    #0,1,2,3,4,5,6,7,8,9, 11  13  15  17  19
    #                   10  12  14  16  18
    [9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9], #0
    [9,8,8,8,8,8,8,6,6,8,8,8,5,5,8,8,8,8,8,9], #1
    [9,8,0,0,0,0,0,6,6,0,0,0,5,5,0,0,0,0,8,9], #2
    [9,8,0,0,2,0,0,6,6,0,0,0,5,5,0,0,0,0,8,9], #3
    [9,8,0,0,0,0,0,6,6,0,0,0,5,5,0,0,2,0,8,9], #4
    [9,8,8,8,0,0,0,6,6,0,0,0,5,5,0,0,0,0,8,9], #5
    [9,9,9,8,0,8,8,6,6,8,8,8,5,5,8,0,0,0,8,9], #6
    [9,8,8,8,0,8,9,9,9,9,9,9,9,9,8,0,8,8,8,9], #7
    [9,8,0,0,0,8,9,8,8,8,8,8,8,9,8,0,8,9,9,9], #8
    [9,8,0,0,0,8,9,8,0,3,0,0,8,9,8,0,8,8,8,9], #9
    [9,8,0,8,8,8,9,8,8,8,0,0,8,9,8,0,0,0,8,9], #10
    [9,8,0,8,9,9,9,9,9,8,0,0,8,9,8,8,8,0,8,9], #11
    [9,8,0,8,8,8,8,8,8,8,0,0,8,9,9,9,8,0,8,9], #12
    [9,8,2,0,0,0,0,0,0,0,0,0,8,9,8,8,8,0,8,9], #13
    [9,8,8,8,8,8,8,8,8,8,8,8,8,9,8,0,0,0,8,9], #14
    [9,9,9,9,9,9,9,9,9,9,9,9,9,9,8,0,1,0,8,9], #15
]


origin_dx = -1.6
origin_dy = -1.5
landmarks = [
    {'row':4, 'col': 16},
    {'row':4, 'col': 4},
    {'row':13, 'col': 2},
    {'row':9, 'col': 9},
]
next_landmark = 0
way_points = {}
for row in range(len(grid)):
        way_points[row] = {}
        for col in range(len(grid[0])):
            way_points[row][col] = False

is_moving = False
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
    print('[%s, %s] => [%s, %s]' %( y, x, int(y * 10 // 1), int(x * 10 // 1)) )
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
    # print('FLY FROM [%s, %s] TO [%s, %s]' %(curr['row'], curr['col'], min_point['row'], min_point['col']))
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

def callback(state: dict):
    global is_moving, next_landmark
    is_moving = True
    next_cell = get_next_cell(state)
    adjusted_height = adjust_height(state['z'], next_cell['state'])
    if adjusted_height >= 0.1 or adjusted_height <= -0.1:
        time.sleep(2)
        # mc.move_distance(0,0, state['z'] + adjusted_height)
    print('MOOVING DISTANCE [%s, %s]' % (next_cell['x'], next_cell['y']))
    # mc.move_distance(next_cell['x'], next_cell['y'], 0)

    if next_cell['state'] == 2 or next_cell['state'] == 3:
        # mc.land()
        time.sleep(2)
        next_landmark = next_landmark + 1
        if next_cell['state'] == 2 :
            time.sleep(1)
            # mc.take_off(0.5)
    is_moving = False
logging.basicConfig(level=logging.INFO)
if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
    with ExtendedCrazyFlie(uri) as ecf:
        ecf.battery.print_state()
        print('[%s, %s]' %( ecf.state_estimate.x, ecf.state_estimate.y))
        input('run')
        ecf.coordination_manager.observe(
            ecf.state_estimate.observable_name,
            callback,
            predicate,
        )
        ecf.parameters_manager.set_value('motorPowerSet', 'enable', 1)
        ecf.parameters_manager.set_value('motorPowerSet', 'm1', 10000)
        ecf.parameters_manager.set_value('motorPowerSet', 'm2', 10000)
        ecf.parameters_manager.set_value('motorPowerSet', 'm3', 10000)
        ecf.parameters_manager.set_value('motorPowerSet', 'm4', 10000)
        while next_landmark < 4:
            time.sleep(1)


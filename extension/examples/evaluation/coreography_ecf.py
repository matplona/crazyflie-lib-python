import logging
import sys
sys.path.append('c:\\Users\\plona\\PC\\TESI\\crazyflie-lib-python')

import time
import math
from extension.extended_crazyflie import ExtendedCrazyFlie
from cflib.positioning.motion_commander import MotionCommander
from environment import grid, origin_dx, origin_dy, landmarks

next_landmark = 0
way_points = {}
is_moving = False
next_point =  {}
for row in range(len(grid)):
        way_points[row] = {}
        for col in range(len(grid[0])):
            way_points[row][col] = False

def predicate(state):
    global is_moving, next_point
    curr = get_grid_point(state) 
    return not is_moving and (next_point == {} or (curr["row"] == next_point["row"] and curr["col"] == next_point["col"]))

def visited(row, col):
    global way_points
    return way_points[row][col]

def visit(row, col):
    global way_points, next_point
    next_point["row"] = row
    next_point["col"] = col
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
    return {
        'col' : int(round(x * 10, 0)),
        'row' : int(round(y * 10, 0)),
        'z': grid[int(round(y * 10, 0))][int(round(x * 10, 0))]
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
    if 'row' not in min_point or 'row' not in min_point:
        next_landmark = 5
        return None
    
    logging.info(f"({curr['row']}, {curr['col']}) -> ({min_point['row']}, {min_point['col']})")
    visit(min_point['row'], min_point['col'])
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
    if -0.1 <= adjusted_height <= 0.1:
        adjusted_height = 0
    if next_cell['x'] == 0 and next_cell['y'] == 0 and adjusted_height == 0:
        print('not moving')
    else:
        mc.move_distance(next_cell['x'], next_cell['y'], adjusted_height)
        time.sleep(0.2)

    if next_cell['z'] == 1:
        z = state['z'] + adjusted_height
        mc.move_distance(0,0, -z)
        time.sleep(2)
        next_landmark = next_landmark + 1
        if next_landmark < 4:
            time.sleep(1)
            mc.move_distance(0,0, z)
    is_moving = False

def move(state: dict, ecf: ExtendedCrazyFlie, start: float):
    delta_time = time.time() - start
    if delta_time < 3:
        ecf.cf.commander.send_velocity_world_setpoint(0, 0, 1, 0)
    elif delta_time < 12:
        end_execution = 12
        constant_vel = 50
        ecf.cf.commander.send_velocity_world_setpoint(1, 0, -0.3, constant_vel + (end_execution - delta_time) * 10 )
    elif delta_time < 16:
        start_execution = 12
        end_execution = 16
        z = easeInOutQuad((delta_time - start_execution)/(end_execution - start_execution))
        if (delta_time - start_execution) > (end_execution - start_execution) / 2:
            z = 1 - z
        ecf.cf.commander.send_velocity_world_setpoint(1, 0, z * 2 , 0 )
    elif delta_time < 20:
        ecf.cf.commander.send_velocity_world_setpoint(1, 0, 0, 45)
    elif delta_time < 24:
        start_execution = 20
        end_execution = 24
        z = easeInOutQuad((delta_time - start_execution)/(end_execution - start_execution))
        if (delta_time - start_execution) > (end_execution - start_execution) / 2:
            z = 1 - z
        ecf.cf.commander.send_velocity_world_setpoint(1, 0, -z * 2 , 0 )
    elif delta_time < 28:
            ecf.cf.commander.send_velocity_world_setpoint(1, 0, 0, 45)
    elif delta_time < 32:
        start_execution = 28
        end_execution = 32
        z = easeInOutQuad((delta_time - start_execution)/(end_execution - start_execution))
        if (delta_time - start_execution) > (end_execution - start_execution) / 2:
            z = 1 - z
        ecf.cf.commander.send_velocity_world_setpoint(1, 0, z * 2 , 0 )
    elif delta_time < 34:
        ecf.cf.commander.send_velocity_world_setpoint(1, 0, 0, 45)
    elif delta_time < 36:
        ecf.cf.commander.send_velocity_world_setpoint(0, 0, 0.5, 0 )
    elif delta_time < 42:
        start_execution = 36
        end_execution = 42
        vy = math.sin(((delta_time - start_execution)* 2*math.pi)/(end_execution - start_execution))
        vz = math.cos(((delta_time - start_execution)* 2*math.pi)/(end_execution - start_execution))
        ecf.cf.commander.send_velocity_world_setpoint(0, vy, vz, 0 )
    elif delta_time < 46:
        start_execution = 42
        end_execution = 46
        vy = math.sin(((delta_time - start_execution)* 2*math.pi)/(end_execution - start_execution))
        vz = math.cos(((delta_time - start_execution)* 2*math.pi)/(end_execution - start_execution))
        ecf.cf.commander.send_velocity_world_setpoint(0, -vy, vz, 0 )
        logging.info("last")
    elif delta_time < 50:
        start_execution = 46
        end_execution = 50
        vx = math.sin(((delta_time - start_execution)* 2*math.pi)/(end_execution - start_execution))
        vz = math.cos(((delta_time - start_execution)* 2*math.pi)/(end_execution - start_execution))
        ecf.cf.commander.send_velocity_world_setpoint(vx, 0, vz, 0 )
    elif delta_time < 54:
        start_execution = 50
        end_execution = 54
        vx = math.sin(((delta_time - start_execution)* 2*math.pi)/(end_execution - start_execution))
        vz = math.cos(((delta_time - start_execution)* 2*math.pi)/(end_execution - start_execution))
        ecf.cf.commander.send_velocity_world_setpoint(-vx, 0, vz, 0 )
    elif delta_time < 57:
        ecf.cf.commander.send_velocity_world_setpoint(0, 0, -1, 0 )


def easeInOutQuad(t):
    t *= 2
    if t < 1:
        return t * t / 2
    else:
        t -= 1
        return -(t * (t - 2) - 1) / 2    


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    uri = 'udp://127.0.0.1:1808'
    with ExtendedCrazyFlie(uri) as ecf:
        start = time.time()
        ecf.coordination_manager.observe(
            observable_name=ecf.state_estimate.observable_name,
            action=move,
            context=[ecf, start]
        )
        time.sleep(60)
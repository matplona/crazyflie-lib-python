import sys
from extension.simulator.crazyflie_simulator import CrazyflieSimulator
# setting path
sys.path.append('c:\\Users\\plona\\PC\\TESI\\crazyflie-lib-python')
import logging
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def analyze_data(filename):
    if os.path.isfile(filename):
        df = pd.read_csv(filename)
        # Extract the required columns
        x = df['x']
        y = df['y']
        z = df['z']
        vx = df['vx']
        vy = df['vy']
        vz = df['vz']
        v = np.sqrt(vx**2 + vy**2 + vz**2)
        # Normalize the vx values to the range [0, 1]
        normalized_v = (v - v.min()) / (v.max() - v.min())
        colors = plt.cm.get_cmap('RdYlGn').reversed()(normalized_v)
        # Create a 3D plot
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(x, y, z,  c=colors)
        # Set labels and title
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title('3D Scatter Plot')

        # # Add tooltips
        # cursor = mplcursors.cursor(scatter, hover=True)
        # tooltip_template = '({x:.2f}, {y:.2f}, {z:.2f})\nVx: {vx:.2f}'
        # cursor.connect('add', lambda sel: sel.annotation.set_text(tooltip_template.format(x=sel.target[0], y=sel.target[1], z=sel.target[2])))

        # Add a colorbar
        sm = plt.cm.ScalarMappable(cmap='RdYlGn', norm=plt.Normalize(vmin=v.min(), vmax=v.max()))
        sm.set_array([])
        fig.colorbar(sm)

        # Show the plot
        plt.show()
    else:
        # File does not exist
        print(f"The file '{filename}' does not exist.")
    return


def run(log):
    simulator = CrazyflieSimulator(log)
    tick = 60
    while tick > 0:
        simulator.set_hover_setpoint(0, 0, 0, 1)
        tick =  tick - 1
        time.sleep(0.2)
    tick = 60
    while tick > 0:
        simulator.set_hover_setpoint(1, 1, 0, 1)
        tick =  tick - 1
        time.sleep(0.2)
    tick = 30
    while tick > 0:
        simulator.set_hover_setpoint(0, 0, 0, 0)
        tick =  tick - 1
        time.sleep(0.2)
    simulator.set_stop_setpoint()
    simulator = None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s]: %(message)s')
    script_dir = os.path.dirname(__file__)
    TIME = round(time.time())
    rel_path =  f'data/data-{TIME}.csv'
    filename = os.path.join(script_dir, rel_path)
    run(filename)
    analyze_data(filename)
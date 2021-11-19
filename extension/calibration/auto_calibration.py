import argparse
from cflib.crazyflie.swarm import CachedCfFactory
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from calibration import *

CGREEN = '\033[92m'
CYELLOW = '\033[93m'
CBLUE = '\033[94m'
CRED = '\033[91m'
CEND = '\033[0m'

def connect_and_calibrate(cf):
    writer = WriteBsGeo(cf)
    writer.estimate_and_write()
    if not writer._valid :
        raise Exception("The enviroment geometry is not valid.")


parser = argparse.ArgumentParser()
# Required positional argument
parser.add_argument('--number', help='CrazyFlie Address (only final bytes) eg 00 or 01 ...', required=True)
parser.add_argument('--type', help='Interface type for URI (default radio)', default='radio')
parser.add_argument('--id', help='Interface ID for URI (default 0)', default='0')
parser.add_argument('--channel', help='Interface channel for URI (default 80)', default='80')
parser.add_argument('--speed', help='Interface speed for URI (default 2M)', default='2M')
parser.add_argument('--address', help='Interface type for URI (default E7E7E7E7)', default='E7E7E7E7')
parser.add_argument('--swarm', type=int, help="Calibrate a swarm of crazyflie. Expect number of crazyflie in the swarm as argument. this will be used as range to compute URIs")
parser.add_argument('--swarm_master', help="Crazyflie Address (only final bytes) eg 00 or 01 ... This address will be the master of the swarm", default='00')
parser.add_argument('--swarm_range', type=int, nargs=2, help="Calibrate a swarm, the numbers of the crazyflie are incremental inside the range (min,max) where both min and maz ar parameter for this command")
args : argparse.Namespace = parser.parse_args()
URI = '{}://{}/{}/{}/{}{}'.format(args.type, args.id, args.channel, args.speed, args.address, args.number)
SWARM = False
if(args.swarm_master):
    MASTER_URI = '{}://{}/{}/{}/{}{}'.format(args.type, args.id, args.channel, args.speed, args.address, args.swarm_master)
    URIS = set()
    SWARM = True
    if(args.swarm):
        items = int(args.swarm)
        if(items < 2 or items > 0xff):
            print('[{}!{}]\t'.format(CRED, CEND) + "Invalid number of crazyflie in the swarm")
            exit(-1)
        if(items < int(args.swarm_master, 16)):
            print('[{}!{}]\t'.format(CRED, CEND) + "Master is not in the range")
            exit(-1)
        for i in range(0, items):
            URIS.add('{}://{}/{}/{}/{}{:02d}'.format(args.type, args.id, args.channel, args.speed, args.address, i))
    elif(args.swarm_range):
        min = int(args.swarm_range[0],16)
        max = int(args.swarm_range[1],16)
        if(min > max):
            temp = max
            max = min
            min = temp
        if(min < 0 or max > 0xff):
            print('[{}!{}]\t'.format(CRED, CEND) + "Invalid MIN or MAX in the range")
            exit(-1)
        if(int(args.swarm_master, 16) < min or int(args.swarm_master, 16) > max):
            print('[{}!{}]\t'.format(CRED, CEND) + "Master is not in the range")
            exit(-1)
        for i in range(min, max+1):
            URIS.add('{}://{}/{}/{}/{}{:02d}'.format(args.type, args.id, args.channel, args.speed, args.address, i))
    else:
        print('[{}!{}]\t'.format(CRED, CEND) + "Missing argument --swarm or --swarm_range")
        exit(-1)
if __name__ == '__main__':
    cflib.crtp.init_drivers()
    if(SWARM):
        print("[{}+{}]\tEstimate geometry for SWARM:".format(CYELLOW, CEND))
        for uri in URIS:
            if(uri == MASTER_URI):
                print("\t[{}M{}]\tURI {}{}{}".format(CGREEN, CEND, CGREEN, uri, CEND))
            else:
                print("\t[{}o{}]\tURI {}{}{}".format(CBLUE, CEND, CBLUE, uri, CEND))
        try:
            factory = CachedCfFactory(rw_cache='./cache')
            with Swarm(URIS, factory=factory) as swarm:
                swarm_writer = WriteBsGeoSwarm(swarm)
                swarm_writer.estimate_and_write(MASTER_URI)
            print('[{}✓{}]\tEstimation completed and written to ALL Crazyflies'.format(CGREEN,CEND))
        except Exception as e:
            print('[{}!{}]\t'.format(CRED, CEND) + str(e))
    else:
        print("[{}+{}]\tEstimate geometry for URI {}{}{}".format(CYELLOW, CEND, CBLUE, URI, CEND))
        try:
            with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
                connect_and_calibrate(scf.cf)
            print('[{}✓{}]\tEstimation completed and written to Crazyflie'.format(CGREEN,CEND))
        except Exception as e:
            print('[{}!{}]\t'.format(CRED, CEND) + str(e))
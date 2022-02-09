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
subparser = parser.add_subparsers(dest='command')
single = subparser.add_parser("single", help="Estimate and write geometry for a single drone")
swarm = subparser.add_parser("swarm", help="Estimate and write geometry for a swarm of drones")
# Required positional argument
single.add_argument('--number', help='CrazyFlie Address (only final bytes) eg 00 or 01 ...', required=True)
single.add_argument('--type', help='Interface type for URI (default radio)', default='radio')
single.add_argument('--id', help='Interface ID for URI (default 0)', default='0')
single.add_argument('--channel', help='Interface channel for URI (default 80)', default='80')
single.add_argument('--speed', help='Interface speed for URI (default 2M)', default='2M')
single.add_argument('--address', help='Interface type for URI (default E7E7E7E7)', default='E7E7E7E7')
swarm.add_argument('--master_number', help="Crazyflie Address (only final bytes) eg 00 or 01 for the master of the swarm", required=True)
swarm.add_argument('--master_type', help='Interface type for URI (default radio) for the master of the swarm', default='radio')
swarm.add_argument('--master_id', help='Interface ID for URI (default 0) for the master of the swarm', default='0')
swarm.add_argument('--master_channel', help='Interface channel for URI (default 80) for the master of the swarm', default='80')
swarm.add_argument('--master_speed', help='Interface speed for URI (default 2M) for the master of the swarm', default='2M')
swarm.add_argument('--master_address', help='Interface type for URI (default E7E7E7E7) for the master of the swarm', default='E7E7E7E7')
swarm_identifiers = swarm.add_mutually_exclusive_group(required=True)
swarm_identifiers.add_argument('--swarm_dimension', type=int, help="Calibrate a swarm of crazyflie. Expect number of crazyflie in the swarm as argument. this will be used as range to compute URIs")
swarm_identifiers.add_argument('--swarm_range', nargs=2, help="Calibrate a swarm, the numbers of the crazyflie are incremental inside the range (min,max) where both min and maz ar parameter for this command")
args : argparse.Namespace = parser.parse_args()
SWARM = False
if(args.command=='swarm'):
    number = format(int(args.master_number,16), '02x').upper()
    MASTER_URI = '{}://{}/{}/{}/{}{}'.format(args.master_type, args.master_id, args.master_channel, args.master_speed, args.master_address, number)
    URIS = set()
    SWARM = True
    if(args.swarm_dimension):
        items = int(args.swarm_dimension)
        if(items < 2 or items > 0xff):
            print('[{}!{}]\t'.format(CRED, CEND) + "Invalid number of crazyflie in the swarm")
            exit(-1)
        if(items < int(args.master_number, 16)):
            print('[{}!{}]\t'.format(CRED, CEND) + "Master is not in the range")
            exit(-1)
        for i in range(0, items):
            number = format(i, '02x').upper()
            URIS.add('{}://{}/{}/{}/{}{}'.format(args.master_type, args.master_id, args.master_channel, args.master_speed, args.master_address, number))
    elif(args.swarm_range):
        try:
            min = int(args.swarm_range[0], 16)
            max = int(args.swarm_range[1], 16)
        except Exception as e1:
            print('[{}!{}]\t'.format(CRED, CEND) + "--swarm_range expect two arguments in HEX from")
            exit(-1)
        if(min > max):
            temp = max
            max = min
            min = temp
        if(min < 0 or max > 0xff):
            print('[{}!{}]\t'.format(CRED, CEND) + "Invalid MIN or MAX in the range")
            exit(-1)
        if(int(args.master_number, 16) < min or int(args.master_number, 16) > max):
            print('[{}!{}]\t'.format(CRED, CEND) + "Master is not in the range")
            exit(-1)
        for i in range(min, max+1):
            number = format(i, '02x').upper()
            URIS.add('{}://{}/{}/{}/{}{}'.format(args.master_type, args.master_id, args.master_channel, args.master_speed, args.master_address, number))
    else:
        print('[{}!{}]\t'.format(CRED, CEND) + "Missing argument --swarm_dimension or --swarm_range")
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
        URI = '{}://{}/{}/{}/{}{}'.format(args.type, args.id, args.channel, args.speed, args.address, args.number)
        print("[{}+{}]\tEstimate geometry for URI {}{}{}".format(CYELLOW, CEND, CBLUE, URI, CEND))
        try:
            with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
                connect_and_calibrate(scf.cf)
            print('[{}✓{}]\tEstimation completed and written to Crazyflie'.format(CGREEN,CEND))
        except Exception as e:
            print('[{}!{}]\t'.format(CRED, CEND) + str(e))
import csv
import os
import socket
import struct
import logging
import time
from cflib.crtp.crtpstack import CRTPPacket, CRTPPort
from extension.simulator.crazyflie_simulator import CrazyflieSimulator, LogBlock
from extension.simulator.analyze_data import analyze_data

logging.basicConfig(level=logging.WARN, format='[%(levelname)s]: %(message)s')

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

class RequestMatch:
    def __init__(self, name, header, match, response):
        self._name = name
        self._header = header
        self._match = match
        if(callable(response)):
            self._response = response
        else:
            self._response = CRTPPacket(header, response)
        
    def matches(self, pk : CRTPPacket):
        return self._header == pk.header and self._match(pk.data)
    
    def send_response(self, socket : socket.socket, addr, data : bytearray):
        pk : CRTPPacket
        if(callable(self._response)):
            pk = CRTPPacket(self._header, self._response(data))
        else:
            pk = self._response
        if len(pk.data) > 0:
            raw = (pk.header,) + struct.unpack('B' * len(pk.data), pk.data)
            logging.info(f'{OKGREEN}Sending response for [{self._name}]:\n\tPORT: {pk.port}\tCHANNEL: {pk.channel}\tDATA: 0x{pk.data.hex()}{ENDC}')
            socket.sendto(bytes(raw), addr)
            network_log([0,len(raw)])


    def name(self):
        return self._name
    
class RequestMapper:
    def __init__(self, cfSim: CrazyflieSimulator, socket: socket.socket):
        # H  ak 
        # 92 03 00 00 00 00 00 00
        self._log_toc = cfSim.log_toc()
        self._param_toc = cfSim.param_toc()
        self._simulator = cfSim
        self._socket = socket
        self._network_filename = 'network'
        self._repo = {
            CRTPPort.PARAM : {
                0 : [   
                    RequestMatch('(PARAM)get_toc_info_v2', 44, lambda data: data[0] == 3,  bytes((3,)) + struct.pack('<HI', len(self._param_toc), 0)),
                    RequestMatch('(PARAM)get_toc_item_v2', 44, lambda data: data[0] == 2,  lambda data: self._get_toc_item(data, self._param_toc)),
                ],
                1 : [RequestMatch('(PARAM)param_get', 45, lambda _: True,  lambda data: self._get_param_value(data))],
                2 : [RequestMatch('(PARAM)param_set', 46, lambda _: True,  lambda data: self._set_param_value(data))]
            },
            CRTPPort.COMMANDER : {
                0 : [
                    RequestMatch('(COMMANDER_GENERIC)stop_setpoint', 60, lambda _: True,  lambda _: self._stop_setpoint(self._simulator)),
                ]
            },
            CRTPPort.MEM : {
                0: [RequestMatch('(MEM)get_mem_number', 76, lambda data: data[0] == 1,  (1,0))],
            },
            CRTPPort.LOGGING: {
                0 : [   
                    RequestMatch('(LOGGING)get_toc_info_v2', 92, lambda data: data[0] == 3,  bytes((3,)) + struct.pack('<HI', len(self._log_toc), 0)),
                    RequestMatch('(LOGGING)get_toc_item_v2', 92, lambda data: data[0] == 2,  lambda data: self._get_toc_item(data, self._log_toc)),
                ],
                1 : [
                    RequestMatch('(LOGGING)create_block', 93, lambda data: data[0] == 6 or data[0] == 7,  lambda data: self._create_block(data, self._simulator)),
                    RequestMatch('(LOGGING)create_block', 93, lambda data: data[0] == 2,  lambda data: self._delete_block(data, self._simulator)),
                    RequestMatch('(LOGGING)start_logging_block', 93, lambda data: data[0] == 3, lambda data: self._start_logging_block(data, self._simulator)),
                    RequestMatch('(LOGGING)stop_logging_block', 93, lambda data: data[0] == 4, lambda data: self._stop_logging_block(data, self._simulator)),
                    RequestMatch('(LOGGING)get_toc', 93, lambda _: True,  (5,0,0)),
                ]
            },
            CRTPPort.COMMANDER_GENERIC: {
                0 : [
                    RequestMatch('(COMMANDER_GENERIC)hover_setpoint', 124, lambda data: data[0] == 5,  lambda data: self._hover_setpoint(data, self._simulator)),
                    RequestMatch('(COMMANDER_GENERIC)position_setpoint', 124, lambda data: data[0] == 7,  lambda data: self._position_setpoint(data, self._simulator)),
                    RequestMatch('(COMMANDER_GENERIC)velocity_world_setpoint', 124, lambda data: data[0] == 1,  lambda data: self._velocity_world_setpoint(data, self._simulator)),
                    RequestMatch('(COMMANDER_GENERIC)stop_setpoint', 124, lambda data: data[0] == 0,  lambda _: self._stop_setpoint(self._simulator)),
                ]
            },
            CRTPPort.PLATFORM: {
                1 : [RequestMatch('(PLATFORM)get_version', 221, lambda data: data[0] == 0,  (0,4))]
            },
            CRTPPort.LINKCTRL: {
                0 : [RequestMatch('(LINKCRTL)echo', 252, lambda _: True,  lambda data: data)],  #REPLY
                1 : [RequestMatch('(LINKCRTL)request_protocol_version', 253, lambda _: True,  'Bitcraze Crazyflie'.encode('utf-8'))],
                2 : [RequestMatch('(LINKCRTL)echo', 254, lambda _: True,  bytes())], #IGNORE
                3 : [RequestMatch('(LINKCRTL)echo', 255, lambda _: True,  bytes())], #IGNORE
            },
        }

    def set_client_address(self, addr):
        self._addr = addr

    def has_response(self, req_pk : CRTPPacket):
        has_port_channel = req_pk.port in self._repo and req_pk.channel in self._repo[req_pk.port]
        if(has_port_channel):
            for m in self._repo[req_pk.port][req_pk.channel]:
                if m.matches(req_pk):
                    logging.debug(f'Found request Match: {m.name()}')
                    return True
        return False

    def get_response(self, req_pk : CRTPPacket):
        for m in self._repo[req_pk.port][req_pk.channel]:
                if m.matches(req_pk):
                    return m
    
    def _get_toc_item(self, data : bytearray, toc):
        index = struct.unpack('<H', data[1:])[0]
        logging.debug(f'Retrieving TOC item @{index}')
        item = toc[index]
        if(item):
            return  bytes((2,)) +  data[1:] + item
        return (0,)
    
    def _get_param_value(self, data: bytearray):
        index = struct.unpack('<H', data)[0]
        value = self._simulator.get_param_value(index)
        param_type = self._simulator.get_param_type(index)
        logging.debug(f'Param @{index} get value = 0x{value.hex()}')
        return data + param_type + value

    def _set_param_value(self, data: bytearray):
        index = struct.unpack('<H', data[:2])[0]
        new_value = data[2:]
        updated_value = self._simulator.set_param_value(index, new_value)
        logging.debug(f'Param @{index} updated value = 0x{updated_value.hex()}')
        return data[:2] + updated_value
    
    def _create_block(self, data:bytearray, sim : CrazyflieSimulator):
        block_id = struct.unpack('<b', data[1:2])[0]
        block : LogBlock = sim.add_block(block_id)
        for i in range(2, len(data[2:]), 3):
            stored_type = (data[i] & 0x0f << 4) >> 4
            fetched_type = data[i] & 0x0f
            var_id = struct.unpack('<H', data[i+1:i+3])[0]
            block.add_variable(var_id, stored_type, fetched_type)
        return data[:2] + bytes((0,))
    
    def _delete_block(self, data: bytearray, sim : CrazyflieSimulator):
        block_id = struct.unpack('<b', data[1:2])[0]
        err_code = sim.delete_block(block_id)
        return data[:2] + bytes((err_code,))
    
    def _start_logging_block(self, data: bytearray, sim : CrazyflieSimulator):
        block_id = struct.unpack('<b', data[1:2])[0]
        period = struct.unpack('<b', data[2:])[0]
        err_code = sim.start_block(block_id, period * 10, self._socket, self._addr)
        return data[:2] + bytes((err_code,))
    
    def _stop_logging_block(self, data: bytearray, sim : CrazyflieSimulator):
        block_id = struct.unpack('<b', data[1:2])[0]
        err_code = sim.stop_block(block_id)
        return data[:2] + bytes((err_code,))
    
    def _hover_setpoint(self, data: bytearray, sim : CrazyflieSimulator):
        vx, vy, yawrate, z = struct.unpack('<ffff', data[1:])
        sim.set_hover_setpoint(vx, vy, yawrate, z)
        return bytes()
    
    def _position_setpoint(self, data: bytearray, sim : CrazyflieSimulator):
        x, y, z, yaw = struct.unpack('<ffff', data[1:])
        sim.set_position_setpoint( x, y, z, yaw)
        return bytes()
    
    def _velocity_world_setpoint(self, data: bytearray, sim : CrazyflieSimulator):
        vx, vy, vz, yawrate = struct.unpack('<ffff', data[1:])
        sim.set_velocity_world_setpoint(vx, vy, vz, yawrate)
        return bytes()
    
    def _stop_setpoint(self, sim : CrazyflieSimulator):
        sim.set_stop_setpoint()
        return bytes()



def write_to_csv(data):
    global filename_network
    with open(filename_network, 'a+', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)
        
def network_log(data):
    global network_log_array
    network_log_array.append(data)

def get_log_data():
    global network_log_array
    load_in = 0 
    load_out = 0
    for data in network_log_array[1:]:
        load_in += data[0]
        load_out += data[1]
    logging.warning(f"traffic: ({load_in})in ({load_out})out")

if __name__ == '__main__':
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('127.0.0.1', 1808)

    # Bind the socket to the server address
    server_socket.bind(server_address)

    print(f'{OKCYAN}Server started at {server_address[0]} on port {server_address[1]}{ENDC}')

    script_dir = os.path.dirname(__file__)
    rel_path =  f'data/data-{round(time.time())}.csv'
    rel_path_network =  f'data/network-{round(time.time())}.csv'
    filename = os.path.join(script_dir, rel_path)
    filename_network = os.path.join(script_dir, rel_path_network)
    network_log_array = []
    # filename =None



    simulator = CrazyflieSimulator(log_file=filename)
    mapper = RequestMapper(simulator, server_socket)
    print(f'{OKGREEN + BOLD}CRAZYFLIE SIM READY{ENDC}')
    data, client_address = server_socket.recvfrom(1024)
    network_log(['in', 'out'])
    network_log([len(data), 0])

    if data == bytes(b'\xc3\xbf\x01\x01\x01'):
        print(f'{OKCYAN}Connection established with client {BOLD + UNDERLINE}{client_address}{ENDC}')
        mapper.set_client_address(client_address)
    error = False
    # Listen for incoming data
    while True:
        try:
            data, client_address = server_socket.recvfrom(1024)
            network_log([len(data), 0])

        except ConnectionResetError as e:
            logging.critical(f'{ERROR}Connection Interrupted{ENDC}')
            error = True
        
        if data == bytes(b'\xc3\xbf\x01\x02\x02') or error:
            print(f'{RED}Connection closed with client {BOLD + UNDERLINE}{client_address}{ENDC}')
            time.sleep(3)
            simulator.set_stop_setpoint()
            simulator = None
            mapper = None
            print(f'{OKBLUE}PROCESSING DATA... {ENDC}')
            write_to_csv(network_log_array)
            get_log_data()
            analyze_data(filename, "")
            
            # print(f'{WARNING + BOLD}REBOOT CRAZYFLIE SIM{ENDC}')
            # server_socket.bind(server_address)
            # print(f'{OKCYAN}Server restarted at {server_address[0]} on port {server_address[1]}{ENDC}')
            # simulator = CrazyflieSimulator(log_file=filename)
            # mapper = RequestMapper(simulator, server_socket)
            # print(f'{OKGREEN + BOLD}CRAZYFLIE SIM READY{ENDC}')
            # error = False
            break

        data_array = struct.unpack('B' * len(data), data)
        pk = CRTPPacket(data_array[0], data_array[1:])
        # Process the received data
        logging.info(f'{MAGENTA}Received data: {data.hex()} HEADER {pk.header}:\n\tPORT: {pk.port}\tCHANNEL: {pk.channel}\tDATA: 0x{pk.data.hex()}{ENDC}')
        if mapper.has_response(pk):
            res = mapper.get_response(pk)
            res.send_response(server_socket, client_address, pk.data)

        else:
            logging.fatal(f'{ERROR}Unknown mapping for pk: HEADER {pk.header}:\n\tPORT: {pk.port}\tCHANNEL: {pk.channel}\tDATA: 0x{pk.data.hex()}{ENDC}')
            break
    
    logging.critical(f'{ERROR}Stopping server{ENDC}')

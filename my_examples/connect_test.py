import cflib.crtp
from cflib.crazyflie import Crazyflie
from time import sleep

connected = 0

def crazyflie_connected(link_uri):
    global connected
    connected = 1
    print('Connected to %s' % link_uri)
    

cflib.crtp.init_drivers()
available = cflib.crtp.scan_interfaces()
for i in available:
    print("Interface with URI [%s] found and name/comment [%s]" % (i[0], i[1]))
if not available:
    print("Not available")

crazyflie = Crazyflie()
crazyflie.connected.add_callback(crazyflie_connected)
crazyflie.open_link("radio://0/80/2M")

while(not connected):
    sleep(1)



roll    = 0.0
pitch   = 0.0
yawrate = 0
thrust  = 0
crazyflie.commander.send_setpoint(roll, pitch, yawrate, thrust)
thrust = 10002
crazyflie.commander.send_setpoint(roll, pitch, yawrate, thrust)

sleep(2)

thrust = 0
crazyflie.commander.send_setpoint(roll, pitch, yawrate, thrust)


print("closing link")
crazyflie.close_link()
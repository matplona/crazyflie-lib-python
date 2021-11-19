from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import Log, LogConfig, LogVariable
class Logger:
    def __init__(self, scf : SyncCrazyflie) -> None:
        self._cf : Crazyflie = scf.cf
        self._variables = {}
        self._logs = []
    
    def _get_size(self, type) -> int:
        if(type=='uint8_t' or type=='int8_t'):
            return 1
        elif(type=='uint16_t' or type=='int16_t' or type=='FP16'):
            return 2
        elif(type=='float' or type=='uint32_t' or type=='int32_t'):
            return 4
        else:
            raise Exception("{} is an invalid variable type".format(type)) 

    def add_variable(self, group, name, period_in_ms, type) -> None:
        """
        [!] The datatype is the transferred datatype, it will be converted from internal type to transferred type before transfers:
            *   float                                                   # 4 Bytes
            *   uint8_t and int8_t                                      # 1 Byte
            *   uint16_t and int16_t                                    # 2 Bytes
            *   uint32_t and int32_t                                    # 4 Bytes
            *   FP16: 16bit version of floating point (less precision)  # 2 Bytes
        [!] variables must be in the ToC
        """
        variable_log = None
        size = self._get_size(type)
        #search a log with exact period that can host the variable
        added = False
        for log in self._logs:
            if log["period"] == period_in_ms and log["size"] + size <= 26:
                #if the period is correct and there is space add the variable to the log
                log["log"].add_variable("{}.{}".format(group,name), type)
                log["size"] += size
                added = True
                variable_log = log
                break
        if not added:
            #if we fail adding the variable we need to create a new log that can host it
            log = self._add_log(period_in_ms)
            log["log"].add_variable("{}.{}".format(group,name), type)
            log["size"] += size
            test : LogConfig = log["log"]
            var : LogVariable = test.variables[0]
            print("{}:\t{}\t{}".format(test.name, test.valid, self._cf.log.state))
            
            self._cf.log.add_config(log["log"])
            variable_log = log
        #add variable to dict of variables
        self._variables["{}.{}".format(group,name)] = {
                "type": type,
                "period" : period_in_ms,
                "has_cb": False,
                "log": variable_log
            }
        print(variable_log)

    def _add_log(self, period_in_ms) -> LogConfig:
        """
        [!] log must be <= 26 Bytes (e.g., 6 floats + 1 FP16)
        """
        name = "Config_{}".format(len(self._logs))
        if(period_in_ms < 10):
            period_in_ms = 10
        log = LogConfig(name=name, period_in_ms=period_in_ms)
        new_entry = {
            "log":log,
            "period":period_in_ms,
            "size": 0
            }
        self._logs.append(new_entry)
        log.data_received_cb.add_callback(self._cb)
        return new_entry

    def _cb (self, timestamp, data, logconf):
        #cycle among data ,
        for name, value in data.items():
            # TODO add the possibility to insert a predicate (a function f(value) -> Boolean)
            if self._variables[name]["has_cb"]:
                #call the callback with the value as parameter
                self._variables[name]["cb"](timestamp, value)

URI = 'radio://0/80/2M/E7E7E7E700'
import cflib.crtp
from cflib.crazyflie import Crazyflie
if __name__ == '__main__':
    cflib.crtp.init_drivers()
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        logger = Logger(scf)
        logger.add_variable("pm", "vbat", 3000, "float")
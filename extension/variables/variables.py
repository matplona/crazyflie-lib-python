from cflib import crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig
from enum import Enum
import time


class RunningState(Enum):
    STOPPED = 0
    RUNNING = 1

class Logger:
    __instances = {}

    @staticmethod
    def getInstance(scf : SyncCrazyflie) :
        """call this method to get the right instance of the logger given the SyncCrazyFlie"""
        if scf.cf.link_uri in Logger.__instances:
            return Logger.__instances.get(scf.cf.link_uri)
        #if not return create a new instance and add in the dict then return it
        Logger.__instances[scf.cf.link_uri] = None
        logger : Logger = Logger(scf)
        Logger.__instances[scf.cf.link_uri] = logger
        return logger

    def __init__(self, scf : SyncCrazyflie) -> None:
        if scf.cf.link_uri not in Logger.__instances :
            raise("This is not the right way to get an Instance, please call the static method getInstance(scf)")
        else:
            self.__cf : crazyflie.Crazyflie = scf.cf
            self.__variables = {}
            self.__logs = []
    
    def __get_size(self, type) -> int:
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
        Add a variable to the logger.
        [!] The datatype is the transferred datatype, it will be converted from internal type to transferred type before transfers:
            *   float                                                   # 4 Bytes
            *   uint8_t and int8_t                                      # 1 Byte
            *   uint16_t and int16_t                                    # 2 Bytes
            *   uint32_t and int32_t                                    # 4 Bytes
            *   FP16: 16bit version of floating point (less precision)  # 2 Bytes
        [!] variables must be in the ToC
        """
        variable_log = None
        if("{}.{}".format(group,name) in self.__variables):
            #if variable already exist raise exception
            raise Exception("Duplicate variable in logger.")
        size = self.__get_size(type)
        #search a log with exact period that can host the variable
        added = False
        for log in self.__logs:
            if log["period"] == period_in_ms and log["size"] + size <= 26:
                # if the period is correct and there is space add the variable to the log
                log["log"].add_variable("{}.{}".format(group,name), type)
                # refreshing the content of the log inside the CF
                log["log"].delete()
                log["log"].create()
                # update the size of the log
                log["size"] += size
                added = True
                variable_log = log
                break
        if not added:
            #if we fail adding the variable we need to create a new log that can host it
            log = self.__add_log(period_in_ms)
            log["log"].add_variable("{}.{}".format(group,name), type)
            log["size"] += size
            self.__cf.log.add_config(log["log"])
            variable_log = log
        #add variable to dict of variables
        self.__variables["{}.{}".format(group,name)] = {
                "type": type,
                "period" : period_in_ms,
                "log": variable_log,
                "predicate" : lambda _ : True, #by default no predicate constraint
                "cb": lambda timestamp, name, value : None # by default cb just returns
            }

    def __add_log(self, period_in_ms) -> LogConfig:
        # [!] log must be <= 26 Bytes (e.g., 6 floats + 1 FP16)
        name = "Config_{}".format(len(self.__logs))
        if(period_in_ms < 10):
            period_in_ms = 10
        log = LogConfig(name=name, period_in_ms=period_in_ms)
        new_entry = {
                "log":log,
                "period":period_in_ms,
                "size": 0,
                "status" : RunningState.STOPPED
            }
        self.__logs.append(new_entry)
        log.data_received_cb.add_callback(self.__cb)
        return new_entry

    def __cb (self, timestamp, data, logconf):
        """
        When log data are ready we check if the predicate of the variable is satisfied and if so, we call it's cb
        """
        #for each line of the log
        for name, value in data.items():
            variable = self.__variables[name]
            #check if the predicate is true
            if variable["predicate"](value):
                #call the callback with the following parameter:
                #   -   timestamp
                #   -   group.name
                #   -   value
                variable["cb"](timestamp, name, value)

    def start_logging_variable(self, group, name):
        """Start logging the variable specified"""
        log : LogConfig = self.__variables["{}.{}".format(group,name)]["log"]
        if(log["status"] == RunningState.STOPPED):
            log["log"].start()
            log["status"] = RunningState.RUNNING  
    def stop_logging_variable(self, group, name):
        """Stop logging the variable specified"""
        log : LogConfig = self.__variables["{}.{}".format(group,name)]["log"]
        if(log["status"] == RunningState.RUNNING):
            log["log"].stop()
            log["status"] = RunningState.STOPPED

    def start_logging_group(self, group):
        """Start logging all the variable in the group specified"""
        for name, var in self.__variables.items():
            if(name.startswith(group) and var["log"]["status"]== RunningState.STOPPED):
                var["log"]["log"].start()
                var["log"]["status"] = RunningState.RUNNING
    def stop_logging_group(self, group):
        """Stop logging all the variable in the group specified"""
        for name, var in self.__variables.items():
            if(name.startswith(group) and var["log"]["status"]== RunningState.RUNNING):
                var["log"]["log"].stop()
                var["log"]["status"] = RunningState.STOPPED
    
    def start_logging_all(self):
        """Start logging all the variable added"""
        for log in self.__logs:
            if(log["status"]==RunningState.STOPPED):
                log["log"].start()
                log["status"] = RunningState.RUNNING
    def stop_logging_all(self):
        """Stop logging all the variable added"""
        for log in self.__logs:
            if(log["status"]==RunningState.RUNNING):
                log["log"].stop()
                log["status"] = RunningState.STOPPED

    def set_watcher(self, group, name, cb):
        """
        Add a callback to the variable specified, when start logging this function will be called
        with 3 parameter: timestamp, name and value.
        """
        if(cb.__code__.co_argcount != 3 ):
            pass#raise Exception("Watcher must accept exacty 3 parameter.")
        variable = self.__variables["{}.{}".format(group,name)]
        variable["cb"] = cb
    def set_predicate(self, group, name, pred):
        """
        Add a predicate to the variable specified, when start logging before calling the watcher
        it will be called the function pred with the value as parameter, if pred returns True the 
        watcher is called otherwise not.
        The function pred must be a function that takes a parameter and returns a bool.
        """
        if(pred.__code__.co_argcount != 1):
            raise Exception("Predicate must accept exacty 1 parameter.")
        variable = self.__variables["{}.{}".format(group,name)]
        variable["predicate"] = pred

class Setter:
    __instances = {}

    @staticmethod
    def getInstance(scf : SyncCrazyflie) :
        """call this method to get the right instance of the setter given the SyncCrazyFlie"""
        if scf.cf.link_uri in Setter.__instances:
            return Setter.__instances.get(scf.cf.link_uri)
        #if not return create a new instance and add in the dict then return it
        s = Setter(scf)
        Setter.__instances[scf.cf.link_uri] = s
        return s

    def __init__(self, scf : SyncCrazyflie) -> None:
        if scf.cf.link_uri not in Setter.__instances :
            raise("This is not the right way to get an Instance, please call the static method getInstance(scf)")
        else:
            self.__cf : crazyflie = scf.cf
            self.__variables = {}

    def __cb(self, name, value):
        ts = int(time.time()*1000)
        value = float(value)
        #check if the predicate is true
        if(self.__variables[name]["predicate"](value)):
            #call the callback with the following parameter:
                #   -   timestamp
                #   -   group.name
                #   -   value
            self.__variables[name]["cb"](ts, name, value)

    def add_variable(self, group, name):
        self.__variables["{}.{}".format(group, name)] = {
            "group":group,
            "name":name,
            "cb": lambda timestamp, name, value : None, # initial empty watcher
            "predicate" : lambda value : True # inital not constrainted predicate
        }
        self.__cf.param.add_update_callback(group, name, self.__cb)

    def set_watcher(self, group, name, cb):
        """
        Add a callback to the variable specified, when the value of this variable change, this function will be 
        called with 3 parameter: timestamp, name and value.
        [!] ATTENTION: the timestamp is generated by the python script not by the CF
        """
        if(cb.__code__.co_argcount != 3):
            raise Exception("Watcher must accept exacty 3 parameter.")
        if("{}.{}".format(group, name) in self.__variables):
            self.__variables["{}.{}".format(group, name)]["cb"] = cb
        else:
            raise Exception("Variable not found in the setter, you may add it before use.")

    def set_predicate(self, group, name, pred):
        """
        Add a predicate to the variable such that it call the watcher only when the predicate returns true
        """
        if(pred.__code__.co_argcount != 1):
            raise Exception("Predicate must accept exacty 1 parameter.")
        if("{}.{}".format(group, name) in self.__variables):
            self.__variables["{}.{}".format(group, name)]["predicate"] = pred
        else:
            raise Exception("Variable not found in the setter, you may add it before use.")

    def set_value(self, group, name, value, template="{:f}"):
        """
        Set the value of a parameter direcly on board of the CF. Parameter must be according to the toc
        """
        if("{}.{}".format(group, name) in self.__variables):
            self.__cf.param.set_value("{}.{}".format(group, name), template.format(value))
        else:
            raise Exception("Variable not found in the setter, you may add it before use.")

    def get_value(self, group, name):
        """
        Get the value of a parameter direcly on board of the CF. Parameter must be according to the toc
        """
        if("{}.{}".format(group, name) in self.__variables):
            return self.__cf.param.get_value("{}.{}".format(group, name))
        else:
            raise Exception("Variable not found in the setter, you may add it before use.")
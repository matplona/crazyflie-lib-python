from cflib import crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig
import time
from typing import Any, Callable

# type aliases
Callback = Callable[[int, str, Any], None]
GroupCallback = Callable[[int, str, dict], None]
Predicate = Callable[[Any], bool]
GroupPredicate = Callable[[dict], bool]

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
        if(group in self.__variables and name in self.__variables[group]):
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
        
        # if is the first of the group
        if(group not in self.__variables):
            # add group because
            self.__variables[group] = {
                "group_predicate" : lambda _ : True, # by default no predicate constraint
                "group_cb": None, # by default None cb
                "count": 0, # indicates the num of var in the group that are currently logging
            }
        # add the variable to the group
        self.__variables[group][name] = {
            "type": type,
            "period" : period_in_ms,
            "log": variable_log,
            "is_running": False, # initially not running
            "predicate" : lambda _ : True, # by default no predicate constraint
            "cb": None, # by default None cb
            "clock" : 0, # initialize lamport clock
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
            "count": 0, # num of variable that have started logging
        }
        self.__logs.append(new_entry)
        log.data_received_cb.add_callback(self.__cb)
        return new_entry

    def __cb(self, timestamp, data : dict, logconfig):
        for name, value in data.items():
            # get the name and the group
            var_name : str = name.split(".")[0]
            group_name : str = name.split(".")[1]
            group_ref = self.__variables[group_name]
            var_ref = self.__variables[group_name][var_name]
            clock : int = var_ref['clock']
            var_ref['clock'] += 1 # increment the lamport clock

            # if is the first variable in the group with this clock
            if clock not in group_ref['history']:
                # create the entry in the history
                group_ref['history'][clock] = {}
            
            # add the value in the history
            group_ref['history'][clock][var_name] = value

            # if is the last of the group with this clock
            if len(group_ref['history'][clock]) == group_ref['count']:
                # remove from history and call group callback if needed
                if group_ref['group_cb'] is not None:
                    data = group_ref['history'].pop(clock) # remove from dict
                    if(group_ref['group_predicate'](data)): # if predicate is SAT
                        group_ref['group_cb'](timestamp, group_name, data) # callback with data

            # call variable callback if needed
            if var_ref['cb'] is not None:
                if var_ref['predicate'](value):
                    var_ref['cb'](timestamp, name, value)

    def start_logging_variable(self, group, name):
        """Start logging the variable specified"""
        if not self.__variables[group][name]['is_running']:
            log : LogConfig = self.__variables[group][name]["log"]
            self.__variables[group][name]['is_running'] = True
            log['count'] += 1 # increment count of variable that has been started
            if(log['count'] == 1):
                log["log"].start()

    def stop_logging_variable(self, group, name):
        """Stop logging the variable specified"""
        if self.__variables[group][name]['is_running']:
            log : LogConfig = self.__variables[group][name]["log"]
            self.__variables[group][name]['is_running'] = False
            log['count'] -= 1 # decrement count of variable that has been started
            if(log['count'] == 0):
                log["log"].stop()

    def start_logging_group(self, group):
        """Start logging all the variable in the group specified"""
        for name in self.__variables[group].keys():
            self.start_logging_variable(group, name)

    def stop_logging_group(self, group):
        """Stop logging all the variable in the group specified"""
        for name in self.__variables[group].keys():
            self.stop_logging_variable(group, name)
    
    def start_logging_all(self):
        """Start logging all the variable added"""
        for group in self.__variables.keys():
            self.start_logging_group(group)
    def stop_logging_all(self):
        """Stop logging all the variable added"""
        for group in self.__variables.keys():
            self.stop_logging_group(group)

    def set_group_watcher(self, group, cb : GroupCallback):
        """
        Add a callback to the group specified, when start logging this function will be called
        with 3 parameter: timestamp (of the last logged), group name and data. Where data is a 
        dict containing the association name:value for each variable in the group
        """
        self.__variables[group]["group_cb"] = cb

    def set_variable_watcher(self, group, name, cb : Callback):
        """
        Add a callback to the variable specified, when start logging this function will be called
        with 3 parameter: timestamp, name and value.
        """
        self.__variables[group][name]['cb'] = cb

    def set_group_predicate(self, group, pred : GroupPredicate):
        """
        Add a predicate to the group specified, when start logging before calling the watcher
        it will be called the function pred with the data as parameter, if pred returns True the 
        watcher is called otherwise not.
        The function pred must be a function that takes a dict and returns a bool.
        Notice: the parameter data is a dict containing the association name:value for 
        each variable in the group
        """
        self.__variables[group]['group_predicate'] = pred

    def set_variable_predicate(self, group, name, pred : Predicate):
        """
        Add a predicate to the variable specified, when start logging before calling the watcher
        it will be called the function pred with the value as parameter, if pred returns True the 
        watcher is called otherwise not.
        The function pred must be a function that takes a parameter and returns a bool.
        """
        self.__variables[group][name]['predicate'] = pred




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
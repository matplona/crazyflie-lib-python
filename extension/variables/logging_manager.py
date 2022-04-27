from tokenize import group
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
import time
from typing import Any, Callable

# type aliases
Callback = Callable[[int, str, Any], None]
GroupCallback = Callable[[int, str, dict], None]
Predicate = Callable[[Any], bool]
GroupPredicate = Callable[[dict], bool]

class LoggingManager:
    __instance = None

    @staticmethod
    def getInstance(cf : Crazyflie) :
        """call this method to get the single instance of the LoggingManager"""
        if LoggingManager.__instance == None:
            LoggingManager.__instance = LoggingManager(cf)
        return LoggingManager.__instance

    def __init__(self, cf : Crazyflie) -> None:
        if self.__instance == None :
            # initialize correctly the instance
            self.__cf : Crazyflie = cf
            self.__variables = {}
            self.__logs = []
        else:
            raise("This is not the right way to get an Instance, please call the static method getInstance()")
    
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
        Add a variable to the LoggingManager.
        [!] The type can differ from the ToC and must be one of the following:
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
            raise Exception("Variable {}.{} already exist in LoggingManager.".format(group,name))
        size = self.__get_size(type)
        #search a log with exact period that can host the variable
        added = False
        for log in self.__logs:
            if log["period"] == period_in_ms and log["size"] + size <= 26:
                # if the period is correct and there is space add the variable to the log
                log["log"].add_variable("{}.{}".format(group,name), type)
                log["updated"] = True # we updated the log configuration by adding a variable
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
        }

    def remove_variable(self, group, name):
        if group not in self.__variables or name not in self.__variables[group]:
            #if variable not exist raise exception
            raise Exception("Variable {}.{} not exist in LoggingManager".format(group,name))
        self.stop_logging_variable(group, name) # stop if needed
        self.__variables[group].pop(name) # remove
        if self.__count_variables(self.__variables[group]) == 0:
            # if no more variables are inside the group remove the group
            self.__variables.pop(group)
    
    def remove_group(self, group : str) -> None:
        if group not in self.__variables:
            #if variable not exist raise exception
            raise Exception("Group {} not exist in LoggingManager".format(group))
        self.stop_logging_group(group) # stop if needed
        self.__variables.pop(group) # remove

    def __add_log(self, period_in_ms) -> LogConfig:
        # [!] log must be <= 26 Bytes (e.g., 6 floats + 1 FP16)
        name = "Config_{}".format(len(self.__logs))
        if(period_in_ms < 10):
            period_in_ms = 10
        if(period_in_ms > 0xFF * 10):
            period_in_ms = 0xFF * 10 # 2550 ms
        log = LogConfig(name=name, period_in_ms=period_in_ms)
        new_entry = {
            "log":log,
            "period":period_in_ms,
            "size": 0,
            "count": 0, # num of variable that have started logging
            "updated": True,
        }
        self.__logs.append(new_entry)
        log.data_received_cb.add_callback(self.__cb)
        return new_entry

    def __count_variables(self, group : str) -> bool:
        count = 0
        for name in self.__variables[group].keys():
            if name not in ['group_predicate', 'group_cb', 'count', 'data']:
                count += 1
        return count

    def __get_variables_name_list(self, group : str) -> list[str]:
        variables = []
        for name in self.__variables[group].keys():
            if name not in ['group_predicate', 'group_cb', 'count', 'data']:
                variables.append(name)
        return variables

    def __cb(self, timestamp, data : dict, logconfig):
        for name, value in data.items():
            # get the name and the group
            var_name : str = name.split(".")[1]
            group_name : str = name.split(".")[0]
            group_ref : dict = self.__variables[group_name]
            var_ref : dict = self.__variables[group_name][var_name]

            if not var_ref['is_running']:
                continue # pass this variable

            # if is the first variable in the group setting the value
            if 'data' not in group_ref:
                # create the entry in the group
                group_ref['data'] = {}
            
            # add the value in the history
            group_ref['data'][var_name] = value

            # if is the last of the group setting the value
            if len(group_ref['data']) == group_ref['count']:
                # remove from history and call group callback if needed
                if group_ref['group_cb'] is not None:
                    data = group_ref.pop('data') # remove from dict
                    if(group_ref['group_predicate'](data)): # if predicate is SAT
                        group_ref['group_cb'](timestamp, group_name, data) # callback with data

            # call variable callback if needed
            if var_ref['cb'] is not None:
                if var_ref['predicate'](value):
                    var_ref['cb'](timestamp, name, value)

    def start_logging_variable(self, group, name):
        """Start logging the variable specified"""
        if group not in self.__variables or name not in self.__variables[group]:
            #if variable not exist raise exception
            raise Exception("Variable {}.{} not exist in LoggingManager".format(group,name))

        if not self.__variables[group][name]['is_running']:
            log : LogConfig = self.__variables[group][name]["log"]
            self.__variables[group][name]['is_running'] = True
            self.__variables[group]['count'] += 1 # increment count of variable that has been started
            log['count'] += 1 # increment count of variable that has been started
            if(log['count'] == 1):
                if log['updated']:
                    # refreshing the content of the log inside the CF
                    log["log"].delete()
                    log["log"].create()
                log["log"].start()

    def stop_logging_variable(self, group, name):
        """Stop logging the variable specified"""
        if group not in self.__variables or name not in self.__variables[group]:
            #if variable not exist raise exception
            raise Exception("Variable {}.{} not exist in LoggingManager".format(group,name))
        if self.__variables[group][name]['is_running']:
            log : LogConfig = self.__variables[group][name]["log"]
            self.__variables[group][name]['is_running'] = False
            self.__variables[group]['count'] -= 1 # decrement count of variable that has been started
            log['count'] -= 1 # decrement count of variable that has been started
            if(log['count'] == 0):
                log["log"].stop() # TODO check the correctness

    def start_logging_group(self, group):
        """Start logging all the variable in the group specified"""
        if group not in self.__variables:
            #if group not exist raise exception
            raise Exception("Group {} not exist in LoggingManager".format(group))
        for name in self.__get_variables_name_list(group):
            self.start_logging_variable(group, name)

    def stop_logging_group(self, group):
        """Stop logging all the variable in the group specified"""
        if group not in self.__variables:
            #if group not exist raise exception
            raise Exception("Group {} not exist in LoggingManager".format(group))
        for name in self.__get_variables_name_list(group):
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
        if group not in self.__variables:
            #if group not exist raise exception
            raise Exception("Group {} not exist in LoggingManager".format(group))
        self.__variables[group]["group_cb"] = cb

    def set_variable_watcher(self, group, name, cb : Callback):
        """
        Add a callback to the variable specified, when start logging this function will be called
        with 3 parameter: timestamp, name and value.
        """
        if group not in self.__variables or name not in self.__variables[group]:
            #if variable not exist raise exception
            raise Exception("Variable {}.{} not exist in LoggingManager".format(group,name))
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
        if group not in self.__variables:
            #if group not exist raise exception
            raise Exception("Group {} not exist in LoggingManager".format(group))
        self.__variables[group]['group_predicate'] = pred

    def set_variable_predicate(self, group, name, pred : Predicate):
        """
        Add a predicate to the variable specified, when start logging before calling the watcher
        it will be called the function pred with the value as parameter, if pred returns True the 
        watcher is called otherwise not.
        The function pred must be a function that takes a parameter and returns a bool.
        """
        if group not in self.__variables or name not in self.__variables[group]:
            #if variable not exist raise exception
            raise Exception("Variable {}.{} not exist in LoggingManager".format(group,name))
        self.__variables[group][name]['predicate'] = pred
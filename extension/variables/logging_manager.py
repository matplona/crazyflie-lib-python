from __future__ import annotations
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie
from cflib.crazyflie.log import Log, LogConfig
import logging
from typing import Any, Callable
from enum import Enum
from colorama import Fore, Style

console = logging.getLogger(__name__)
console.level = logging.DEBUG

# type aliases
Callback = Callable[[int, str, Any], None]
GroupCallback = Callable[[int, str, dict], None]
Predicate = Callable[[Any], bool]
GroupPredicate = Callable[[dict], bool]

class UniqueLogName:
    count = 0
    @staticmethod
    def get_unique_name():
        name = f'Log_{UniqueLogName.count}'
        UniqueLogName.count += 1
        return name

class LogVariableType(Enum):
    default = (0,0) # pair(index, size)
    uint8_t = (1,1)
    int8_t = (2,1)
    uint16_t = (3,2)
    int16_t = (4,2)
    uint32_t = (5,4)
    int32_t = (6,4)
    FP16 = (7,2)
    float = (8,4)
    def get_size(self):
        return self.value[1] # return the second element of the pair

class LoggingManager:
    def __init__(self, ecf : ExtendedCrazyFlie) -> None:
        self.__ecf : ExtendedCrazyFlie = ecf
        self.__variables = {}
        self.__logs : list = []
        self.__ecf.wait_for_params() # waiting reset
        console.info('Log TOC reset completed')

    def __resolve_type(self, type: LogVariableType, name : str) -> LogVariableType:
        if type == LogVariableType.default:
            # resolve the type
            return LogVariableType[self.__ecf.cf.log.toc.get_element_by_complete_name(name).ctype]
        return type

    def add_variable(self, group, name, period_in_ms, type:LogVariableType = LogVariableType.default) -> None:
        """
        Add a variable to the LoggingManager. It will find a Log config to fit the var in with the rigth period,
        creating a new one if it does not exist.
        [!] The type can differ from the ToC
        [!] variables must be in the ToC
        """
        variable_log = None
        if(group in self.__variables and name in self.__variables[group]):
            #if variable already exist raise exception
            raise Exception("Variable {}.{} already exist in LoggingManager.".format(group,name))
        
        type = self.__resolve_type(type, f'{group}.{name}')
        size = type.get_size()
        # search a log with exact period that can host the variable
        added = False
        for log in self.__logs:
            if log["period"] == period_in_ms and log["size"] + size <= log['log'].MAX_LEN:
                # if the period is correct and there is space add the variable to the log
                added = True
                variable_log = log
                break
        if not added:
            #if we fail adding the variable we need to create a new log that can host it
            variable_log = self.__new_log(period_in_ms)
        
        # update the log
        variable_log["log"].add_variable(f"{group}.{name}", type.name)
        variable_log["updated"] = True # we updated the log configuration by adding a variable
        variable_log["size"] += size # update the size of the log
        
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
    def add_group(self, group:str, period_in_ms, type:LogVariableType = LogVariableType.default) -> None:
        for name in self.__ecf.cf.log.toc.toc[group]:
            self.add_variable(group,name, period_in_ms, type)

    def remove_variable(self, group, name):
        if group not in self.__variables or name not in self.__variables[group]:
            # if variable not exist raise exception
            raise Exception("Variable {}.{} not exist in LoggingManager".format(group,name))
        self.stop_logging_variable(group, name) # stop if needed
        removed = self.__variables[group].pop(name) # remove
        log : LogConfig = removed['log']
        if self.__count_variables(group) == 0:
            # if no more variables are inside the group remove the group
            self.__variables.pop(group)
        log['size'] -= removed['type'].get_size() # update the size of the log
        log['updated'] = True
        if log['size'] <= 0:
            self.__delete_log(log)    
    def remove_group(self, group : str) -> None:
        if group not in self.__variables:
            #if variable not exist raise exception
            raise Exception("Group {} not exist in LoggingManager".format(group))
        for var_name in self.__get_variables_name_list(group): # for each var inside the group
            self.remove_variable(group, var_name) # remove the variable

    def __delete_log(self, log_entry):
        cf_log : Log= self.__ecf.cf.log
        self.__logs.remove(log_entry) # remove from local list and get its LogConfig
        config : LogConfig = log_entry['log'] # get its LogConfig
        config.stop()
        config.delete()
        cf_log.log_blocks.remove(config) # remove from the general Log
        # reset the config 
        config.added = False
        config.started = False
        config.cf = None
        config.valid = False
        config.useV2 = False



    def __new_log(self, period_in_ms) -> LogConfig:
        # [!] log must be <= 26 Bytes (e.g., 6 floats + 1 FP16)
        name = UniqueLogName.get_unique_name()
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
        console.debug(f'{Fore.GREEN}[++]{Style.RESET_ALL}\tNew LogConfig created')
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

            # check that the variable are still in the dict
            if group_name not in self.__variables or var_name not in self.__variables[group_name]:
                console.warning(f"[!]\t{group_name}.{var_name} is logging but has been removed")
                continue # pass this variable

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
            raise Exception(f"Variable {group}.{name} not exist in LoggingManager")

        if not self.__variables[group][name]['is_running']:
            log : dict = self.__variables[group][name]['log']
            self.__variables[group][name]['is_running'] = True
            self.__variables[group]['count'] += 1 # increment count of variable that has been started
            log['count'] += 1 # increment count of variable that has been started
            if log['updated']: # and the log was updated and was running
                if log['log'].added: # if it was already added delete the config
                    self.__delete_log(log)
                self.__ecf.cf.log.add_config(log['log']) # (re)add the config to the Log
                log['updated'] = False # after updating the log reset the variable
                # need to restart the log if is running
                if log['count'] > 0:
                    log['log'].start()
            elif log['count'] == 1:
                log['log'].start() # only if is the first start the block
            console.debug(f'{Fore.GREEN}[>]{Style.RESET_ALL}\tStarted logging variable {group}.{name}')

    def stop_logging_variable(self, group, name):
        """Stop logging the variable specified"""
        if group not in self.__variables or name not in self.__variables[group]:
            #if variable not exist raise exception
            raise Exception("Variable {}.{} not exist in LoggingManager".format(group,name))
        if self.__variables[group][name]['is_running']:
            log : dict = self.__variables[group][name]['log']
            self.__variables[group][name]['is_running'] = False
            self.__variables[group]['count'] -= 1 # decrement count of variable that has been started
            log['count'] -= 1 # decrement count of variable that has been started
            if(log['count'] == 0):
                log['log'].stop() # if is the last to be stopped in config we need to stop it
            console.debug(f'{Fore.RED}[<]{Style.RESET_ALL}\tStopped logging variable {group}.{name}')
        

    def start_logging_group(self, group):
        """Start logging all the variable in the group specified"""
        if group not in self.__variables:
            #if group not exist raise exception
            raise Exception("Group {} not exist in LoggingManager".format(group))
        for name in self.__get_variables_name_list(group):
            self.start_logging_variable(group, name)
        console.debug(f'{Fore.GREEN}[>]{Style.RESET_ALL}\tStarted logging group {group}')
        

    def stop_logging_group(self, group):
        """Stop logging all the variable in the group specified"""
        if group not in self.__variables:
            #if group not exist raise exception
            raise Exception("Group {} not exist in LoggingManager".format(group))
        for name in self.__get_variables_name_list(group):
            self.stop_logging_variable(group, name)
        console.debug(f'{Fore.RED}[<]{Style.RESET_ALL}\tStopped logging group {group}')
    
    def start_logging_all(self):
        """Start logging all the variable added"""
        for group in self.__variables.keys():
            self.start_logging_group(group)
    def stop_logging_all(self):
        """Stop logging all the variable added"""
        for group in self.__variables.keys():
            self.stop_logging_group(group)

    def close(self):
        """Stop logging all the variables and delete all the LogConfig stored on the CF"""
        self.stop_logging_all()
        block : LogConfig
        for block in self.__ecf.cf.log.log_blocks:
            # delete the block inside the CF
            block.delete()

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
from __future__ import annotations
import re
from typing import TYPE_CHECKING

from extension.decks.deck import Deck, DeckType
if TYPE_CHECKING:
    from extension.extended_crazyflie import ExtendedCrazyFlie

from enum import Enum

class Effect(Enum):
    off = 0
    white_spinner = 1
    color_spinner = 2
    tilt = 3
    brightness = 4
    color_spinner_2 = 5
    double_spinner = 6
    solid_color_effect = 7
    factory_test = 8
    battery_status = 9
    boat_lights = 10
    alert = 11
    gravity = 12
    virtual_memory = 13
    fade_color = 14
    communication_signal_strength = 15
    status_localization_service = 16
    LED_timing_from_memory = 17
    lighthouse_positioning = 18

class Color:
    def __init__(self, r:int, g:int, b:int) -> None:
        self.__r : int = r
        self.__g : int = g
        self.__b : int = b
    
    @property
    def r(self) -> int:
        return self.__r
    @property
    def g(self) -> int:
        return self.__g
    @property
    def b(self) -> int:
        return self.__b

    @r.setter
    def r(self, r : int):
        try :
            r = int(r)
        except:
            raise TypeError("Invalid type: provided {} instead of {}".format(type(r), int))
        if r < 0: r = 0
        if r > 255: r = 255
        self.__r = r

    @g.setter
    def g(self, g : int):
        try :
            g = int(g)
        except:
            raise TypeError("Invalid type: provided {} instead of {}".format(type(g), int))
        if g < 0: g = 0
        if g > 255: g = 255
        self.__g = g

    @b.setter
    def b(self, b : int):
        try :
            b = int(b)
        except:
            raise TypeError("Invalid type: provided {} instead of {}".format(type(b), int))
        if b < 0: b = 0
        if b > 255: b = 255
        self.__b = b
    
    def __eq__(self, other):
        if isinstance(other, Color):
            return [self.r,self.g,self.b] == [other.r,other.g,other.b]
        return False

    def __str__(self) -> str:
        return "({}, {}, {})".format(self.__r, self.__g, self.__b)

    @staticmethod
    def from_hex(hex : str):
        """
        Create a color starting from an hex string:
        e.g., '#FFFFFF' => Color(255,255,255) => white
        """
        hex = hex.capitalize()
        if re.match("#{1}([0-9]|[A-F]){6}$", hex) is None:
            raise Exception("Hex string must be in the form #xxxxxx ")
        return(Color.from_uint(int(hex[1:], 16)))

    @staticmethod
    def from_uint(color : int):
        color_bytes = color.to_bytes(3, 'big', signed=False)
        return Color(
            color_bytes[0],
            color_bytes[1],
            color_bytes[2]
        )

    def to_uint32(self) -> int:
        encoded_array = (
            (0).to_bytes(1,'big', signed=False) + 
            self.__r.to_bytes(1,'big', signed=False) + 
            self.__g.to_bytes(1,'big', signed=False) + 
            self.__b.to_bytes(1,'big', signed=False)
        )
        return int.from_bytes(encoded_array, 'big', signed=False)

    def decrease_intensity(self, percent : float):
        """
        Decrease the value of each component (r,g,b) by a percentage from 0 to 1.
            0 means color unchanged
            1 means color off
        """
        if percent < 0 : percent = 0
        if percent > 1 : percent = 1
        self.r = self.__r - self.__r*percent # setter is called
        self.g = self.__g - self.__g*percent # setter is called
        self.b = self.__b - self.__b*percent # setter is called
    
    def increase_intensity(self, percent : float):
        """
        Increase the value of each component (r,g,b) by a percentage from 0 to 1 up to 255.
            0 means color unchanged
            1 means color white
        """
        if percent < 0 : percent = 0
        if percent > 1 : percent = 1
        self.r = 255 - (255 - self.__r) * (1 - percent) # setter is called
        self.g = 255 - (255 - self.__g) * (1 - percent) # setter is called
        self.b = 255 - (255 - self.__b) * (1 - percent) # setter is called
    

class Colors(Enum):
    off = Color(0, 0, 0)
    red = Color(255, 0, 0)
    blue = Color(0, 0, 255)
    green = Color(0, 255, 0)
    white = Color(255, 255, 255)
    grey = Color(127, 127, 127) # to be checked
    cyan = Color(0, 255, 255)
    light_cyan = Color(127, 255, 255)
    yellow = Color(255, 255, 0)
    canary = Color(255, 255, 127)
    fuchsia = Color(255, 0, 255)
    pink = Color(255, 127, 255)
    peach = Color(255, 127, 127)
    lime = Color(127, 255, 127)
    indigo = Color(127, 127, 255)
    light_blue = Color(0, 127, 255)
    teal = Color(0, 127, 127)
    orange = Color(255, 127, 0)
    purple = Color(127, 0, 127)
    olive = Color(127, 127, 0)

class LedRing(Deck):
    super().__init__(DeckType.bcLedRing) #initialize super
    __effect : int = 0
    __solid_effect_color : Color = Color(20,20,20)
    __headlight : bool = False
    __fade_effect_color : Color = Color(20,20,20)
    __fade_effect_time : float = 0.0
    def __init__(self, ecf : ExtendedCrazyFlie) -> None:
        self.__ecf : ExtendedCrazyFlie = ecf
        self.observable_name = "{}@ledring".format(ecf.cf.link_uri)

        # set up observables for the state
        self.__ecf.coordination_manager.add_observable(self.observable_name, self.__get_state())

        # register variables to the parameter manager
        self.__ecf.parameters_manager.add_variable('ring', 'effect')
        self.__ecf.parameters_manager.add_variable('ring', 'headlightEnable')
        self.__ecf.parameters_manager.add_variable('ring', 'fadeColor')
        self.__ecf.parameters_manager.add_variable('ring', 'fadeTime')
        self.__ecf.parameters_manager.add_variable('ring', 'solidRed')
        self.__ecf.parameters_manager.add_variable('ring', 'solidGreen')
        self.__ecf.parameters_manager.add_variable('ring', 'solidBlue')

        # register watcher to the variables
        self.__ecf.parameters_manager.set_watcher('ring', 'effect', self.__cb)
        self.__ecf.parameters_manager.set_watcher('ring', 'headlightEnable', self.__cb)
        self.__ecf.parameters_manager.set_watcher('ring', 'fadeColor', self.__cb)
        self.__ecf.parameters_manager.set_watcher('ring', 'fadeTime', self.__cb)
        self.__ecf.parameters_manager.set_watcher('ring', 'solidRed', self.__cb)
        self.__ecf.parameters_manager.set_watcher('ring', 'solidGreen', self.__cb)
        self.__ecf.parameters_manager.set_watcher('ring', 'solidBlue', self.__cb)

        # register battery limits to be coherent with animations
        self.__ecf.parameters_manager.set_value('ring', 'emptyCharge', ecf.battery.get_low_voltage())
        self.__ecf.parameters_manager.set_value('ring', 'fullCharge', ecf.battery.get_full_voltage())

        # get value stored in the cf to setup the values
        self.__fade_effect_color = Color.from_uint(
            self.__ecf.parameters_manager.get_value('ring', 'fadeColor')
        )
        self.__fade_effect_time = self.__ecf.parameters_manager.get_value('ring', 'fadeTime')
        self.__headlight = self.__ecf.parameters_manager.get_value('ring', 'headlightEnable') != 0
        self.__solid_effect_color = Color(
            self.__ecf.parameters_manager.get_value('ring', 'solidRed'),
            self.__ecf.parameters_manager.get_value('ring', 'solidGreen'),
            self.__ecf.parameters_manager.get_value('ring', 'solidBlue'),
        )
        self.__effect = self.__ecf.parameters_manager.get_value('ring', 'effect')
    
    @property
    def effect(self) -> Effect:
        return Effect(self.__effect)
    @property
    def headlight(self) -> bool:
        return self.__headlight
    @property
    def solid_effect_color(self) -> Color:
        return self.__solid_effect_color
    @property
    def fade_effect_color(self) -> Color:
        return self.__fade_effect_color
    @property
    def fade_effect_time(self) -> float:
        return self.__fade_effect_time

    def __get_state(self):
        return {
            'effect': self.__effect,
            'headlight': self.__headlight,
            'solid_effect_color': self.__solid_effect_color,
            'fade_effect_color': self.__fade_effect_color,
            'fade_effect_time': self.__fade_effect_time,
        }

    def change_effect(self, effect : Effect):
        self.__ecf.parameters_manager.set_value('ring', 'effect', effect.value)
    def toggle_headlight(self):
        self.__ecf.parameters_manager.set_value('ring', 'headlightEnable', 1 if (not self.__headlight) else 0)
    def headlight_switch(self, on = True):
        self.__ecf.parameters_manager.set_value('ring', 'headlightEnable', 1 if on else 0)
    def change_solid_effect_color(self, color : Color):
        self.__ecf.parameters_manager.set_value('ring', 'solidRed', color.r)
        self.__ecf.parameters_manager.set_value('ring', 'solidGreen', color.g)
        self.__ecf.parameters_manager.set_value('ring', 'solidBlue', color.b)
    def change_fade_effect_color(self, color : Color):
        self.__ecf.parameters_manager.set_value('ring', 'fadeColor', color.to_uint32())
    def change_fade_effect_time(self, time : float):
        self.__ecf.parameters_manager.set_value('ring', 'fadeTime', time)
        

    def __cb(self, ts, name, value):
        set_map = {
            'ring.effect':self.__set_effect,
            'ring.headlightEnable':self.__set_headlight,
            'ring.fadeColor':self.__set_fade_color,
            'ring.fadeTime':self.__set_fade_time,
            'ring.solidRed':self.__set_solid_red,
            'ring.solidGreen':self.__set_solid_green,
            'ring.solidBlue':self.__set_solid_blue,
        }
        set_map[name](value) # execute the appropriate setter with the value
    
    # setter
    def __set_effect(self, value: int):
        self.__effect = value
        self.__ecf.coordination_manager.update_observable_state(self.__get_state())
    def __set_headlight(self, value: int):
        self.__headlight = value
        self.__ecf.coordination_manager.update_observable_state(self.__get_state())
    def __set_fade_color(self, value: int):
        self.__fade_effect_color = Color.from_uint(value)
        self.__ecf.coordination_manager.update_observable_state(self.__get_state())
    def __set_fade_time(self, value: float):
        self.__fade_effect_time = value
        self.__ecf.coordination_manager.update_observable_state(self.__get_state())
    def __set_solid_red(self, value: int):
        self.__solid_effect_color.r = value
        self.__ecf.coordination_manager.update_observable_state(self.__get_state())
    def __set_solid_green(self, value: int):
        self.__solid_effect_color.g = value
        self.__ecf.coordination_manager.update_observable_state(self.__get_state())
    def __set_solid_blue(self, value: int):
        self.__solid_effect_color.b = value
        self.__ecf.coordination_manager.update_observable_state(self.__get_state())

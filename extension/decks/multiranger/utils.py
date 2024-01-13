import enum
from functools import reduce

class Behavior (enum.Enum):
    NONE = 0
    OBJECT_TRACKING = 1
    OBSTACLE_AVOIDANCE = 2

class ActionLimit():
    #measure unit millimeters
    MIN = 150
    MAX = 500
    SAFE = 100

class VelocityLimit():
    #measure unit meters/second
    MIN = 0
    MAX = 1

# this function wil compute a velocity inversely proportional to the distance of the hand
# form the drone using inverse rescaling from the interval (ActionLimit.MIN, ActionLimit.MAX)
# to the interval (VelocityLimit.MIN, VelocityLimit.MAX) i.e.:
# if the value is ActionLimit.MAX or more the velocity would be VelocityLimit.MIN
# if the value is ActionLimit.MIN or less the velocity would be VelocityLimit.MAX
# if the value is in between ActionLimit the velocity would be in between VelocityLimit
def compute_velocity(value) -> float:
        #fixing values in the range (0, ACTION_LIMIT)
        value = ActionLimit.MIN if value < ActionLimit.MIN else value
        value = ActionLimit.MAX if value > ActionLimit.MAX else value
        # NewValue = (((OldValue - OldMin) * (NewMax - NewMin)) / (OldMax - OldMin)) + NewMin where:
            # OldValue = range_in_mm
            # NewValue = velocity_in_ms
            # OldMin = ActionLimit.MAX (range)
            # OldMax = ActionLimit.MIN (range)
            # NewMin = VelocityLimit.MIN (velocity)
            # NewMax = VelocityLimit.MAX (velocity)
        # NOTICE: we inverted the ActionLimits to get the inverted range conversion
        return (((value - ActionLimit.MAX) * (VelocityLimit.MAX - VelocityLimit.MIN)) / (ActionLimit.MIN - ActionLimit.MAX)) + VelocityLimit.MIN


# this function will compute the Velocity in the x-axis direction
def get_vx(front, back)-> float:
    vx = 0
    if(ActionLimit.MIN <= back <= ActionLimit.MAX):
        #back gives a push in the positive x direction
        vx += compute_velocity(back)
    if(ActionLimit.MIN <= front <= ActionLimit.MAX):
        #back gives a push in the negative x direction
        vx -= compute_velocity(front)
    return vx
# this function will compute the Velocity in the x-axis direction
def get_vy(right, left)-> float:
    vy = 0
    if(ActionLimit.MIN <= right <= ActionLimit.MAX):
        #back gives a push in the positive y direction
        vy += compute_velocity(right)
    if(ActionLimit.MIN <= left <= ActionLimit.MAX):
        #back gives a push in the negative y direction
        vy -= compute_velocity(left)
    return vy


SPEED_CLIP = 0.5

def is_safe(*args):
    return reduce(lambda acc, arg: acc and arg>=ActionLimit.SAFE, args, True)

def normalize(x):
    if x==0 : return x # aviod div0
    # normailze will transform x into SPEED_CLIP mantaining the sign
    return (x/abs(x))*SPEED_CLIP

def clip(x):
    sign = 1 if x==0 else x/abs(x) # store the sign (-1 or +1)
    x = abs(x) # apply the absolute value
    if x > VelocityLimit.MAX-SPEED_CLIP:
        # means that the hand is closer so we need to reduce the speed progressively
        # e.g.:
        #   x = 1.6  => x = 0.4
        #   x = 2.0  => x = 0
        x = VelocityLimit.MAX - x
    # clip will normalize only if greather than 0.5 and reapply the correct sign
    return sign * (normalize(x) if x > SPEED_CLIP else x)
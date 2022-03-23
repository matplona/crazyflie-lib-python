from typing import Callable, Any

# type alias
# An Action is a callback function takes as input the new state of the domain and the additional parameters and return nothing
Action = Callable[[dict, list], None]

# A Condition is a function that takes as input the new state of the domain and return True or False
Condition = Callable[[dict], bool]
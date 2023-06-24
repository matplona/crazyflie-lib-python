from typing import Callable

# type alias
# An Action is a callback function takes as input the new state of the domain and the additional parameters and return nothing
Action = Callable[..., None]

# A Condition is a function that takes as input the new state of the domain and return True or False
Condition = Callable[[dict], bool]
MultiCondition = Callable[[list[dict]], bool]
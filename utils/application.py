"""
Author: Ali Mokhtari (ali.mokhtaary@gmail.com)
Created on Jan, 18, 2022

"""

from enum import Enum, unique
from functools import total_ordering


@total_ordering
class Application:

    def __init__(self, name, models):
        self.name = name
        self.models =  models
        self.status = AppStatus.MINIMAL 
        self.loaded_model_size = 0
        self.stats = {'requested_times': [], 
                       'allocated_memory':[],
                    }
    
    def __gt__(self, other):
        return self.loaded_model_size > other.loaded_model_size   
    
@unique
class AppStatus(Enum):    
    MINIMAL = 2
    AGGRESSIVE = 3
    
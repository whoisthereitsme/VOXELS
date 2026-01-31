from __future__ import annotations  # MUST BE FIRST

# EXCEPTION IMPORTS
from .timer import Timer, time      # NON SORTED -> HERE BECAUSE Timer IS USED IMMEDIATELY
timer = Timer()

# IMPORTS FROM STANDARD LIBRARY AND THIRD-PARTY LIBRARIES
from typing import TYPE_CHECKING, Any, Iterator, TypeVar, Generic, Union, Tuple, List, Dict, Callable, Optional
from pathlib import Path
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFont


# SIMPLE IMPORTS
import math
import numpy as np
import torch 
import heapq
import threading
import json
import time
import pathlib
import sys
import os
import random
import shutil
import datetime
import bisect
import pygame
import moderngl
import traceback
import stat


# my own modules (utils)
from .types import POS, SIZE


# Exports
__all__ = [
    "math",
    "time",
    "np",
    "NDArray",
    "torch",
    "TYPE_CHECKING",
    "annotations",
    "Any",
    "Iterator",
    "TypeVar",
    "Generic",
    "Union",
    "Tuple",
    "List",
    "Dict",
    "Callable",
    "Optional",
    "Image",
    "ImageDraw",
    "ImageFont",
    "Timer",
    "heapq",
    "threading",
    "json",
    "Path",
    "POS",
    "SIZE",
    "pathlib",
    "sys",
    "os",
    "random",
    "shutil",
    "datetime",
    "bisect",
    "pygame",
    "moderngl",
    "timer", # include the instance timer -> can be used as utils.timer
    "traceback",
    "stat",
]

# END OF FILE
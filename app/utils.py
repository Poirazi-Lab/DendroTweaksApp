import re
from importlib import import_module
import numpy as np

import colorsys

from logger import logger

def dynamic_import(module_name, class_name):
    module = import_module(module_name)
    return getattr(module, class_name)

# def dynamic_import(filename):
#     module = import_module(f"channel.collection.{filename}")
#     return getattr(module, filename)


def match_name(func):
    def wrapper(sec):
        if isinstance(sec, str):
            name = sec
        else:
            name = sec.name()

        if not '[' in name:
            name = f'{name}[0]'

        match = re.search(r"(([A-Za-z]+)\[(\d+)\])?\.?(([A-Za-z]+)_?\d?\[(\d+)\])", name)
        

        return func(match)
    return wrapper

@match_name
def get_sec_name(match):
    return match.group(4)

@match_name
def get_sec_type(match):
    return match.group(5)

@match_name
def get_sec_id(match):
    return match.group(6)

def lambda_f(sec, f):
    return 1e5*np.sqrt(sec.diam/(4*np.pi*f*sec.Ra*sec.cm))

def get_seg_name(seg, round_x=True):
    if round_x:
        return f'{get_sec_name(seg.sec)}({round(seg.x, 5)})'
    else:
        return f'{get_sec_name(seg.sec)}({seg.x})'

# def parse_name(name):
#     if not '[' in name:
#         name = f'{name}[0]'
#     match = re.search(r"(([A-Za-z]+)\[(\d+)\])?\.?(([A-Za-z]+)_?\d?\[(\d+)\])", name)
#     return match

# def get_sec_name(sec):
#     match = parse_name(sec if isinstance(sec, str) else sec.name())
#     return match.group(4) if match else None

# def get_sec_type(sec):
#     match = parse_name(sec if isinstance(sec, str) else sec.name())
#     return match.group(5) if match else None

# def get_sec_id(sec):
#     match = parse_name(sec if isinstance(sec, str) else sec.name())
#     return match.group(6) if match else None


import time
from functools import wraps
            
def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        logger.info(f'Runtime: {end - start:.10f} seconds')
        return result
    return wrapper


def hex_to_rgb(hex_color):
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_color):
    return ''.join([f'{i:02x}' for i in rgb_color])

def decrease_saturation_and_brightness(color_list, saturation_decrease, brightness_decrease):
    new_colors = []
    for hex_color in color_list:
        # Remove '#' from hex color and convert to RGB
        rgb = hex_to_rgb(hex_color[1:])
        # Normalize RGB values to 0-1
        rgb_normalized = [x/255.0 for x in rgb]
        # Convert RGB to HSV
        hsv = colorsys.rgb_to_hsv(*rgb_normalized)
        # Decrease saturation and brightness by given amounts
        new_hsv = (hsv[0], max(0, hsv[1]-saturation_decrease), max(0, hsv[2]-brightness_decrease))
        # Convert back to RGB
        new_rgb_normalized = colorsys.hsv_to_rgb(*new_hsv)
        # Convert RGB values back to 0-255
        new_rgb = [int(x*255) for x in new_rgb_normalized]
        # Convert RGB to hex and add to new color list
        new_colors.append('#' + rgb_to_hex(new_rgb))
    return new_colors


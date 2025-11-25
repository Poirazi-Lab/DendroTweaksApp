# SPDX-FileCopyrightText: 2025 Poirazi Lab <dendrotweaks@dendrites.gr>
# SPDX-License-Identifier: MPL-2.0

import logging

import inspect


logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(levelname)-10s - %(filename)s - %(funcName)s : %(message)s',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'app.log',
            'mode': 'w',
            'formatter': 'default',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
    },
}

# logging.config.dictConfig(config=logging_config)

class CustomHandler(logging.Handler):
    def __init__(self, file_handler, console_handler):
        super().__init__()
        self.file_handler = file_handler
        self.console_handler = console_handler

    def emit(self, record):
        if record.name == 'decorator':
            self.file_handler.setFormatter(decorator_formatter)
            self.console_handler.setFormatter(decorator_formatter)
        else:
            self.file_handler.setFormatter(formatter)
            self.console_handler.setFormatter(formatter)
        self.file_handler.emit(record)
        self.console_handler.emit(record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)-10s - %(filename)s - %(funcName)s : %(message)s')

# Create a file handler and a console handler
file_handler = logging.FileHandler('app.log', mode='w')
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

decorator_logger = logging.getLogger('decorator')
decorator_logger.setLevel(logging.DEBUG)
decorator_formatter = logging.Formatter('%(levelname)-10s - %(filename)s : %(message)s')

# Create a custom handler and add it to both loggers
custom_handler = CustomHandler(file_handler, console_handler)
logger.addHandler(custom_handler)
decorator_logger.addHandler(custom_handler)


import functools
import os

def log(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f'START {func.__qualname__} ...')
        result = func(*args, **kwargs)
        logger.debug('END')
        return result
    return wrapper

# def log(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         # Get the current frame and extract file and function name
#         frame = inspect.currentframe().f_back
#         file_name = os.path.basename(frame.f_code.co_filename)
#         func_name = frame.f_code.co_name

#         # Log the start of the function call
#         logger.debug('START...', extra={'filename': file_name, 'funcName': func_name})
#         result = func(*args, **kwargs)
#         # Log the end of the function call
#         logger.debug('END', extra={'filename': file_name, 'funcName': func_name})
#         return result
#     return wrapper
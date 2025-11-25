# SPDX-FileCopyrightText: 2025 Poirazi Lab <dendrotweaks@dendrites.gr>
# SPDX-License-Identifier: MPL-2.0

from bokeh.models import Slider, NumericInput, Spinner
from bokeh.layouts import row
import math

class AdjustableSpinner():
    def __init__(self, title, value, step=None, visible=True):

        step = self.calculate_step(value) if step is None else step

        self.spinner = Spinner(title=title, low=-1e5, high=1e5, step=step, value=value, width=200, format='0[.][##########]')
        self.ninput = NumericInput(title='Step', value=step, width=70, mode='float')

        # self.ninput.js_link('value', self.spinner, 'step')
        def ninput_callback(attr, old, new):
            self.spinner.step = new

        self.ninput.on_change('value', ninput_callback)

    def calculate_step(self, value):
        magnitude = math.floor(math.log10(abs(value))) if value != 0 else 0
        base_step = 10**(magnitude)
        return base_step

    def get_widget(self):
        return row(self.spinner, self.ninput)

    def on_change(self, attr, callback):
        self.spinner.on_change(attr, callback)

    @property
    def _callbacks(self):
        return self.spinner._callbacks

    @property
    def _event_callbacks(self):
        return self.spinner._event_callbacks

    def remove_on_change(self, attr, callback):
        self.spinner.remove_on_change(attr, callback)

    @property
    def value(self):
        return self.spinner.value

    @value.setter
    def value(self, value):
        self.spinner.value = value

    @property
    def title(self):
        return self.spinner.title

    @property
    def visible(self):
        return self.spinner.visible

    @visible.setter
    def visible(self, value):
        self.spinner.visible = value
        self.ninput.visible = value


class remove_callbacks:
    def __init__(self, widget):
        self.widget = widget
        self.change_callbacks = {}
        self.event_callbacks = {}

    def __enter__(self):
        # Handle on_change callbacks
        for event_type in self.widget._callbacks:
            self.change_callbacks[event_type] = [callback for callback in self.widget._callbacks[event_type]]
            for callback in self.change_callbacks[event_type]:
                self.widget.remove_on_change(event_type, callback)

        # Handle on_event callbacks
        for event_type in self.widget._event_callbacks:
            if isinstance(event_type, Event):
                event_type = event_type.event_name
            self.event_callbacks[event_type] = [callback for callback in self.widget._event_callbacks[event_type]]
            for callback in self.event_callbacks[event_type]:
                self.widget.remove_on_event(event_type, callback)

    def __exit__(self, type, value, traceback):
        # Re-add on_change callbacks
        for event_type in self.change_callbacks:
            for callback in self.change_callbacks[event_type]:
                self.widget.on_change(event_type, callback)

        # Re-add on_event callbacks
        for event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                self.widget.on_event(event_type, callback)


from logger import decorator_logger
from functools import wraps

def log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        decorator_logger.debug(f"{func.__qualname__.split('.')[-1]} : START ...")
        result = func(*args, **kwargs)
        decorator_logger.debug(f"{func.__qualname__.split('.')[-1]} : END\n")
        return result
    return wrapper
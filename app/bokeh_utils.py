from bokeh.models import Slider, NumericInput
from bokeh.layouts import row

class SmartSlider():
    
    def __init__(self, name, value):
        self.slider = Slider(title=name, start=0, end=1, step=0.01, value=value, width=200, format='0[.]00000')
        self.ninput = NumericInput(title=name, value=value, width=100, mode='float')

        def ninput_callback(attr, old, new):
            value = self.ninput.value
            start = - 10 * value
            if start < 0:
                start = 0
            end = 10 * value
            step = value / 10
            self.slider.start = start
            self.slider.end = end
            self.slider.step = step
            self.slider.value = value
            # self.slider.format = f'0[.]0{len(str(value).split(".")[1])}'

        self.ninput.on_change('value', ninput_callback)
        
    def get_widget(self):
        return row(self.ninput, self.slider)

    @property
    def value(self):
        return self.slider.value

    @property
    def title(self):
        return self.slider.title

    @value.setter
    def value(self, value):
        self.slider.value = value
        self.ninput.value = value

    def on_change(self, attr, callback):
        self.slider.on_change(attr, callback)
        self.ninput.on_change('value', callback)

    @property
    def title(self):
        return self.slider.title


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
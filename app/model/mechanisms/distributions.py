from functools import partial
from logger import logger

from numpy import exp, sin

class Distribution:
    """
    Represents a distribution function.

    Args:
        f_type (str): The type of distribution function.
        *args: Variable length argument list for the distribution function.
        **kwargs: Arbitrary keyword arguments for the distribution function.

    Attributes:
        f (callable): The distribution function.

    Methods:
        __call__(*args, **kwargs): Calls the distribution function.
        __eq__(other): Checks if two Distribution objects are equal.
        __hash__(): Returns the hash value of the Distribution object.
        __repr__(): Returns a string representation of the Distribution object.
    """

    def __init__(self, f_type: str, *args: float, **kwargs: float):
        self.f = partial(self.function_map[f_type], *args, **kwargs)

    def __repr__(self):        
        return f'Distr {self.f.func.__name__}(' + ','.join(str(x) for x in self.f.args) +  ', '.join(f'{key}={value}' for key, value in self.f.keywords.items()) + ')'

    def __str__(self):
        return self.__repr__().replace('Distr ', '')

    @staticmethod
    def uniform(distance: float, value: float) -> float:
        """
        Uniform distribution function.

        Args:
            distance (float): The distance parameter.
            value: The value parameter.

        Returns:
            The value parameter.
        """
        return value

    @staticmethod
    def linear(distance: float, intercept: float, slope: float) -> float:
        """
        Linear distribution function.

        Args:
            distance (float): The distance parameter.
            slope (float): The slope parameter.
            intercept (float): The intercept parameter.

        Returns:
            The result of the linear equation: slope * distance + intercept.
        """
        return slope * distance + intercept

    @staticmethod
    def exponential(distance: float, vertical_shift:float = 0, scale_factor: float =1, growth_rate: float=1, horizontal_shift: float = 0) -> float:
        """
        Exponential distribution function.

        Args:
            distance (float): The distance parameter.
            vertical_shift (float): The vertical shift parameter.
            scale_factor (float): The scale factor parameter.
            growth_rate (float): The growth rate parameter.
            horizontal_shift (float): The horizontal shift parameter.

        Returns:
            The result of the exponential equation: vertical_shift + scale_factor * exp(growth_rate * (distance - horizontal_shift)).
        """
        return vertical_shift + scale_factor * exp(growth_rate * (distance - horizontal_shift))

    @staticmethod
    def sigmoid(distance: float, vertical_shift=0, scale_factor=1, growth_rate=1, horizontal_shift=0) -> float:
        """
        Sigmoid distribution function.

        Args:
            distance (float): The distance parameter.
            vertical_shift (float): The vertical shift parameter.
            scale_factor (float): The scale factor parameter.
            growth_rate (float): The growth rate parameter.
            horizontal_shift (float): The horizontal shift parameter.

        Returns:
            The result of the sigmoid equation: vertical_shift + scale_factor / (1 + exp(-growth_rate * (distance - horizontal_shift))).
        """
        return vertical_shift + scale_factor / (1 + exp(-growth_rate*(distance - horizontal_shift)))

    @staticmethod
    def sinusoidal(distance: float, amplitude: float, frequency: float, phase: float) -> float:
        """
        Sinusoidal distribution function.

        Args:
            distance (float): The distance parameter.
            amplitude (float): The amplitude parameter.
            frequency (float): The frequency parameter.
            phase (float): The phase parameter.

        Returns:
            The result of the sinusoidal equation: amplitude * sin(frequency * distance + phase).
        """
        return amplitude * sin(frequency * distance + phase)

    @staticmethod
    def step(distance: float, max_value: float,  min_value: float, start: float, end: float) -> float:
        """
        Step distribution function.

        Args:
            distance (float): The distance parameter.
            min_value (float): The minimum value parameter.
            max_value (float): The maximum value parameter.
            start (float): The start parameter.
            end (float): The end parameter.

        Returns:
            The result of the step equation: min_value if distance < start, max_value if distance > end, and a linear interpolation between min_value and max_value if start <= distance <= end.
        """
        if start < distance < end:
            return max_value
        else:
            return min_value

    # ... define other distributions ...

    function_map = {
        'uniform': uniform,
        'linear': linear,
        'exponential': exponential,
        'sigmoid': sigmoid,
        'sinusoidal': sinusoidal,
        'step': step,
        # ... add other distributions ...
    }

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)

    def __eq__(self, other):
        if isinstance(other, Distribution):
            return (self.f.func == other.f.func and 
                    self.f.args == other.f.args and 
                    self.f.keywords == other.f.keywords)
        return False

    def __hash__(self):
        return hash((str(self.f.func), self.f.args, frozenset(self.f.keywords.items())))

    def update(self, *args: float, **kwargs: float):
        # args = self.f.args + args
        # kwargs = {**self.f.keywords, **kwargs}
        logger.info(f'Keywords: {self.f.keywords}')
        logger.info(f'kwargs: {kwargs}')
        self.f.keywords.update(kwargs)
        logger.info(f'Keywords: {self.f.keywords}')
        # self.f = partial(self.f.func, *args, **kwargs)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['f_type'], *data['args'], **data['kwargs'])

    def to_dict(self):
        return {'f_type': self.f.func.__name__, 
                'args': self.f.args, 
                'kwargs': self.f.keywords}

    def plot(self, ax, x, label=None):
        ax.plot(x, [self.f(xi) for xi in x], label=label)
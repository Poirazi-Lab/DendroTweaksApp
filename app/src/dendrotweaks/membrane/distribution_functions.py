from typing import Callable, Dict
import numpy as np

# Define simple functions and store them alongside their defaults in FUNCTIONS

def uniform(position, value=0):
    """
    Constant function that returns a constant value for any position.

    Parameters
    ----------
    position : float or np.ndarray
        The position at which to evaluate the function.
    value : float
        The constant value to return.

    Returns
    -------
    float or np.ndarray
        The value of the constant function at the given position.
    """
    if isinstance(position, np.ndarray):
        return np.full_like(position, value)
    else:
        return value


def linear(position, slope=1, intercept=0):
    """
    Linear function that returns a linearly changing value for any position.

    Parameters
    ----------
    position : float or np.ndarray
        The position at which to evaluate the function.
    slope : float
        The slope of the linear function.
    intercept : float
        The intercept of the linear function.

    Returns
    -------
    float or np.ndarray
        The value of the linear function at the given position.
    """
    return slope * position + intercept


# aka ParametrizedFunction
class DistributionFunction:
    """
    A callable class for creating and managing distribution functions.

    Parameters
    ----------
    function_name : str
        The name of the function to use.
    \**parameters
        The parameters to use for the function.

    Attributes
    ----------
    function : Callable
        The function to use for evaluation.
    parameters : dict
        The parameters to use for the function.

    Examples
    --------

    >>> func = Distribution('uniform', value=0)
    >>> func(5)
    0
    """

    FUNCTIONS = {
        'uniform': {'func': uniform, 'defaults': {'value': 0}},
        'linear': {'func': linear, 'defaults': {'slope': 1, 'intercept': 0}}
    }

    @staticmethod
    def from_dict(data: Dict[str, any]) -> 'Distribution':
        """
        Create a new Distribution from a dictionary.

        Parameters
        ----------
        data : dict
            The dictionary containing the function data.

        Returns
        -------
        Distribution
            The new Distribution instance.
        """
        return DistributionFunction(data['function'], **data['parameters'])

    def __init__(self, function_name: str, **parameters: Dict[str, float]) -> None:
        """
        Create a new parameterized function.

        Parameters
        ----------
        function_name : str
            The name of the function to use.
        \**parameters
            The parameters to use for the function.
        """
        func_data = self.FUNCTIONS[function_name]
        self.function = func_data['func']
        # Merge defaults with user parameters
        valid_params = {k: v for k, v in parameters.items()
                        if k in func_data['defaults']}
        self.parameters = {**func_data['defaults'], **valid_params}

    def __repr__(self):
        """
        Return a string representation of the function.

        Returns
        -------
        str
            The string representation of the function.
        """
        return f'{self.function.__name__}({self.parameters})'

    def __call__(self, position):
        """
        Call the function with a given position.

        Parameters
        ----------
        position : float or np.ndarray
            The position at which to evaluate the function.

        Returns
        -------
        float or np.ndarray
            The value of the function at the given position.
        """
        return self.function(position, **self.parameters)

    @property
    def function_name(self):
        """
        Return the name of the function.

        Returns
        -------
        str
            The name of the function.
        """
        return self.function.__name__

    def update_parameters(self, **new_params):
        """
        Update the parameters of the function.

        Parameters
        ----------
        \**new_params
            The new parameters to update the function with.
        """
        valid_params = {k: v for k, v in new_params.items()
                        if k in self.parameters}
        self.parameters.update(valid_params)

    def to_dict(self):
        """
        Export the function to a dictionary format.

        Returns
        -------
        dict
            A dictionary representation of the function.
        """
        return {
            'function': self.function.__name__,
            'parameters': self.parameters
        }
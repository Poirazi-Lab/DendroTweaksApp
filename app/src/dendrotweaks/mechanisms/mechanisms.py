from typing import Dict
import numpy as np
import matplotlib.pyplot as plt

class Mechanism:
    """
    A mechanism object that can be placed on a section of a neuron.

    Attributes:
        name (str): The name of the mechanism.
        _parameters (Dict[str, float]): The parameters of the mechanism.

    Examples:
        >>> mechanism = Mechanism('hh', {'gna': 120, 'gk': 36, 'gl': 0.3})
        >>> mechanism
        Mechanism(hh) with parameters: {'gna_hh': 120, 'gk_hh': 36, 'gl_hh': 0.3}

    Notes:
        - The parameters of the mechanism are stored in a dictionary with the format:
          {parameter_name_mechanism_name: value}.
    """

    def __init__(self, name: str, parameters: Dict[str, float]) -> None:
        """
        Initializes a new mechanism object.

        Parameters:
            name (str): The name of the mechanism.
            parameters (Dict[str, float]): The parameters of the mechanism.
        """
        self.name = name
        self._parameters = parameters

    def __repr__(self) -> str:
        """
        Returns a string representation of the mechanism.

        Returns:
            str: A string representation of the mechanism.
        """
        return f'Mechanism({self.name}) with parameters: {self.parameters}'

    @property
    def parameters(self) -> Dict[str, float]:
        """
        Returns the parameters of the mechanism.

        Returns:
            Dict[str, float]: The parameters of the mechanism.
        """
        return {f'{parameter_name}_{self.name}': value for parameter_name, value in self._parameters.items()}


class IonChannel(Mechanism): #IonChanelView?

    def __init__(self, name: str, **parameters):
        super().__init__(name, parameters)

    # def set_x_range(self, x: np.ndarray) -> None:
    #     """
    #     Sets the range of the independent variable x 
    #     which could be voltage or Ca2+ concentration.

    #     Warning
    #     -------
    #     The variable x is NOT used during the simulation.
    #     It is only used to visualize the channel kinetics.

    #     Parameters:
    #         x (numpy.ndarray): An array with the values of the independent variable x.

    #     Examples
    #     --------
    #     >>> kv = Kv()
    #     >>> v = numpy.linspace(-100, 100, 100)
    #     >>> kv.set_x_range(v)
    #     >>> kv.x
    #     array([-100, -98, -96, ..., 96, 98, 100])
    #     """
    #     self.x = x

    def get_data(self, x) -> Dict[str, Dict[str, float]]:
        
        states = self.compute_kinetic_variables(x)
        data = {
            state_name: {
                'inf': states[i], 
                'tau': states[i + 1]
                }
            for i, state_name in zip(range(0, len(states), 2), 
                                     self.channel_states)
        }
        return data

    def plot_kinetic_variables(self, ax=None) -> None:

        if ax is None:
            fig, ax = plt.subplots(1, 2, figsize=(10, 5))

        if self.independent_var_name == 'v':
            x = np.linspace(-100, 100, 100)
        elif self.independent_var_name == 'cai':
            x = np.logspace(-6, 2, 100)

        data = self.get_data(x)

        for state_name, state in data.items():
            ax[0].plot(x, state['inf'], label=f'{state_name}Inf')
            ax[1].plot(x, state['tau'], label=f'{state_name}Tau')

        ax[0].set_title('Steady state')
        ax[1].set_title('Time constant')
        ax[0].set_xlabel('Voltage (mV)' if self.independent_var_name == 'v' else 'Ca2+ concentration (mM)')
        ax[1].set_xlabel('Voltage (mV)' if self.independent_var_name == 'v' else 'Ca2+ concentration (mM)')
        ax[0].set_ylabel('Open probability (1)')
        ax[1].set_ylabel('Time constant (ms)')
        ax[0].legend()
        ax[1].legend()





class CustomIonChannel(IonChannel):
    
        def __init__(self, name: str):
            super().__init__(name, **{})
            # self.state_vars = {state: 
            #     {
            #     'inf': f'{state}_inf', 
            #     'tau': f'tau_{state}', 
            #     'power': params["power"]
            #     } 
            # for state, params in state_vars.items()}

class StandardIonChannel():
    
        def __init__(self, name: str, state_vars, ion, **parameters):
            self.name = name
            self.parameters = parameters
            self.state_vars = {state: 
                {
                'inf': f'{state}_inf', 
                'tau': f'tau_{state}', 
                'power': params["power"]
                } 
            for state, params in state_vars.items()}


class LeakChannel(Mechanism):

    def __init__(self):
        self.name = 'Leak'
        self._parameters = {'gbar': 0.0001}
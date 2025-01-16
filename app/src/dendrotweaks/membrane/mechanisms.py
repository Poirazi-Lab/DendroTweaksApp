from typing import Dict
import numpy as np
import matplotlib.pyplot as plt



class Mechanism():

    def __init__(self, name):
        self.name = name
        self.params = {}
        self.range_params = {}
        self.domains = {}

    @property
    def params_with_suffix(self):
        return {f"{param}_{self.name}":value for param, value in self.params.items()}

    @property
    def range_params_with_suffix(self):
        return {f"{param}_{self.name}":value for param, value in self.range_params.items()}

    def to_dict(self):
        return {
            'name': self.name,
            'params': self.params
        }

    def is_inserted(self):
        return bool(self.domains)

    def __repr__(self):
        return f"<Mechnaism({self.name})>"


class CaDynamics(Mechanism):

    def __init__(self):
        super().__init__('CaDyn')
        self.params = {
            'tau_rise': 5,
            'tau_decay': 40,
            'ca_inf': 50e-6,
            'depth': 0.1,
        }


class IonChannel(Mechanism):
    
    def __init__(self, name):
        super().__init__(name)
        self.tadj = 1

    def set_tadj(self, temperature):
        q10 = self.params.get("q10", 2.3)
        reference_temp = self.params.get("temp", temperature)
        self.tadj = q10 ** ((temperature - reference_temp) / 10)

    def get_data(self, x=None, temperature: float = 37) -> Dict[str, Dict[str, float]]:

        if x is None:
            if self.independent_var_name == 'v':
                x = np.linspace(-100, 100, 100)
            elif self.independent_var_name == 'cai':
                x = np.logspace(-6, 2, 100)
        
        self.set_tadj(temperature)
        states = self.compute_kinetic_variables(x)
        data = {
            state_name: {
                'inf': states[i], 
                'tau': states[i + 1]
                }
            for i, state_name in zip(range(0, len(states), 2), 
                                     self.states)
        }
        data.update({'x': x})
        print(f'Got data for {self.independent_var_name} '
               f'in range {x[0]} to {x[-1]} at {temperature}°C')
        return data

    def plot_kinetics(self, ax=None, linestyle='solid', **kwargs) -> None:

        if ax is None:
            fig, ax = plt.subplots(1, 2, figsize=(10, 5))

        data = self.get_data(**kwargs)
        x = data.pop('x')

        for state_name, state in data.items():
            ax[0].plot(x, state['inf'], label=f'{state_name}Inf', linestyle=linestyle)
            ax[1].plot(x, state['tau'], label=f'{state_name}Tau', linestyle=linestyle)

        ax[0].set_title('Steady state')
        ax[1].set_title('Time constant')
        ax[0].set_xlabel('Voltage (mV)' if self.independent_var_name == 'v' else 'Ca2+ concentration (mM)')
        ax[1].set_xlabel('Voltage (mV)' if self.independent_var_name == 'v' else 'Ca2+ concentration (mM)')
        ax[0].set_ylabel('Open probability (1)')
        ax[1].set_ylabel('Time constant (ms)')
        ax[0].legend()
        ax[1].legend()




class StandardIonChannel(IonChannel):
    """
    A class representing a voltage-gated ion channel with a standard 
    set of kinetic parameters and equations grounded in the transition-state
    theory. The model is based on the Hodgkin-Huxley formalism.
    """


    STANDARD_PARAMS = [
        'vhalf', 'sigma', 'k', 'delta', 'tau0'
    ]

    @staticmethod
    def steady_state(v, vhalf, sigma):
        return 1 / (1 + np.exp(-(v - vhalf) / sigma))

    def time_constant(self, v, vhalf, sigma, k, delta, tau0):
        return 1 / (self.alpha_prime(v, vhalf, sigma, k, delta) + self.beta_prime(v, vhalf, sigma, k, delta)) + tau0

    @staticmethod
    def alpha_prime(v, vhalf, sigma, k, delta):
        return k * np.exp(delta * (v - vhalf) / sigma)

    @staticmethod
    def beta_prime(v, vhalf, sigma, k, delta):
        return k * np.exp(-(1 - delta) * (v - vhalf) / sigma)

    @staticmethod
    def t_adj(temperature, q10=2.3, reference_temp=23):
        return q10 ** ((temperature - reference_temp) / 10)

    def compute_state(self, v, vhalf, sigma, k, delta, tau0, tadj=1):
        inf = self.steady_state(v, vhalf, sigma)
        tau = self.time_constant(v, vhalf, sigma, k, delta, tau0) / tadj
        return inf, tau

    def __init__(self, name, state_powers, ion=None):
        super().__init__('s' + name)
        
        self.ion = ion
        self.independent_var_name = 'v'

        self._state_powers = state_powers

        self.range_params = [f'{param}_{state}' for state in state_powers
                    for param in self.STANDARD_PARAMS]

        self.params = {
            f'{param}_{state}': None
            for state in state_powers
            for param in self.STANDARD_PARAMS
        }
        self.params.update({
            'gbar': 0.0,
        })

        self.temperature = 37

    @property
    def states(self):
        return [state for state in self._state_powers]

    def compute_kinetic_variables(self, v):
        
        results = []

        for state in self.states:

            vhalf = self.params[f'vhalf_{state}']
            sigma = self.params[f'sigma_{state}']
            k = self.params[f'k_{state}']
            delta = self.params[f'delta_{state}']
            tau0 = self.params[f'tau0_{state}']

            inf = self.steady_state(v, vhalf, sigma)
            tau = self.time_constant(v, vhalf, sigma, k, delta, tau0) / self.tadj

            results.extend([inf, tau])
            
        return results


    def fit(self, data, prioritized_inf=True, round_params=3):
        """
        Fits the standardized set of parameters of the model to the data 
        of the channel kinetics. 
        
        Parameters
        ----------
        data : dict
            A dictionary containing the data for the channel kinetics. The
            dictionary should have the following structure:
            {
                'x': np.array, # The independent variable
                'state1': {'inf': np.array, 'tau': np.array},
                'state2': {'inf': np.array, 'tau': np.array},
                ...
            }
        prioritized_inf : bool, optional
            Whether to prioritize the fit to the 'inf' data. If False, the
            fit will be performed to both 'inf' and 'tau' data. If True, an
            additional fit will be performed to the 'inf' data only. The
            default is True.
        round_params : int, optional
            The number of decimal places to round the fitted parameters to.
            The default is 3.
        """
        from symfit import exp, variables, parameters, Model, Fit

        x = data.pop('x')

        for state, state_data in data.items():
            v, inf, tau = variables('v, inf, tau')
            initial_values = [1, 0.5, 0, 10, 0] if state_data['inf'][0] < state_data['inf'][-1] else [1, 0.5, 0, -10, 0]
            k, delta, vhalf, sigma, tau0 = parameters('k, delta, vhalf, sigma, tau0', value=initial_values)
            
            model = Model({
                inf: 1 / (1 + exp(-(v - vhalf) / sigma)),
                tau: 1 / (k * exp(delta * (v - vhalf) / sigma) + k * exp(-(1 - delta) * (v - vhalf) / sigma)) + tau0,
            })

            fit = Fit(model, v=x, inf=state_data['inf'], tau=state_data['tau'])
            fit_result = fit.execute()

            if prioritized_inf:
                vhalf.value, sigma.value = fit_result.params['vhalf'], fit_result.params['sigma']
                model_inf = Model({inf: 1 / (1 + exp(-(v - vhalf) / sigma))})
                fit_inf = Fit(model_inf, v=x, inf=state_data['inf'])
                fit_result_inf = fit_inf.execute()
                fit_result.params.update(fit_result_inf.params)

            if round_params:
                fit_result.params = {key: round(value, round_params) for key, value in fit_result.params.items()}

            for param in ['k', 'delta', 'tau0', 'vhalf', 'sigma']:
                self.params[f'{param}_{state}'] = fit_result.params[param]
    
    
    def to_dict(self):
        return {
            'suffix': self.name,
            'ion': self.ion,
            'range_params': [
                (param, self.params[param], get_unit(param))
                for param in self.params
            ],
            'state_vars': {
                var: power for var, power in self._state_powers.items()
            },
        }

    @staticmethod
    def get_unit(param):
        if param.startswith('vhalf_'): return 'mV'
        elif param.startswith('sigma_'): return 'mV'
        elif param.startswith('k_'): return '1/ms'
        elif param.startswith('delta_'): return '1'
        elif param.startswith('tau0_'): return 'ms'


class LeakChannel(Mechanism):

    def __init__(self):
        super().__init__(name='Leak')
        self.params = {'gbar': 0.0, 'e': -70}
        self.range_params = {'gbar': 0.0, 'e': -70}
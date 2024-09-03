from model.mechanisms.groups import Group
from model.mechanisms.distributions import Distribution

from collections import defaultdict

from logger import logger

import numpy as np
import matplotlib.pyplot as plt

from symfit import variables, parameters, Model, Fit, exp

from jinja2 import Template

import re

class IonChannel():

    def __init__(self, name, suffix, cell=None):
        self.name = name
        self.suffix = suffix
        self.range_params = []
        self.groups = []
        self.v_range = np.linspace(-100, 100, 1000)
        self.cai_range = np.logspace(-5, 5, 1000)

    # def add_group(self, sec_type: list, distance_range: list, param_name: str):
    #     group = Group(sec_type, distance_range, param_name)
    #     if distribution is not None:
    #         group.distribution = distribution
    #     self.groups.append(group)

    def add_group(self, segments, param_name: str = 'gbar', distribution: Distribution = None, tag=None):
        group_id = len(self.groups)
        group = Group(group_id, segments, param_name)
        if distribution is not None:
            group.distribution = distribution
        self.groups.append(group)

    # def add_default_group(self, param_name: str = 'gbar'):
    #     group = Group(0, segments, f'{param_name}_{self.suffix}', cell=self.cell)
    #     group.distribution = Distribution('uniform', value=0)
    #     self.groups[sec_type].append(group)

    def get_by_name(self, group_name):
        for group in self.groups:
            if group.name == group_name:
                return group
        return None

    # def distribute(self):
    #     for distribution in self._distributions:
    #         for sec in getattr(self.cell, distribution.sec_type):
    #             for seg in sec:
    #                 distance = self.cell.distance_from_soma(seg)
    #                 if distribution.start <= distance <= distribution.end:
    #                     setattr(seg, distribution.param_name, distribution(distance))

    def remove_group(self, group):
        group.distribution = Distribution('uniform', value=0)
        self.groups.remove(group)

    def remove_all_groups(self):
        for group in reversed(self.groups):
            self.remove_group(group)
        logger.debug(f'{self.name} groups removed: {self.groups}')

    def apply_groups(self, domain):
        for group in self.groups[domain]:
            group.apply()

    def plot_distribution(self, sec_type, param_name, ax=None):
        import matplotlib.pyplot as plt
        if ax is None:
            fig, ax = plt.subplots()
        for group in self.groups[sec_type]:
            segs = group.segments
            vals = [getattr(seg, param_name) for seg in segs]
            ax.scatter([self.cell.distance_from_soma(seg) for seg in segs], vals, label=f'{group.start} - {group.end}')
        ax.set_title(f'{self.name} {param_name} distribution')
        ax.set_xlabel('Distance from soma (um)')
        ax.set_ylabel(f'{self.name} {param_name}')
        ax.legend()
        return ax

    def to_dict(self):
        return {'name': self.name, 
                'suffix': self.suffix, 
                'groups': [group.to_dict() for group in self.groups]}


    def plot_states(self, ax=None, ignore=[], linestyle='-', x_scale='linear'):

        if ax is None:
            fig, ax = plt.subplots(1, 2, figsize=(10, 5))
        colors = plt.cm.Set1(np.linspace(0, 1, len(self.state_vars)))
        for (state, value), color in zip(self.state_vars.items(), colors):
            if state in ignore:
                continue
            ax[0].plot(self.x_range, getattr(self, value['inf']), label=state, linestyle=linestyle, color=color if linestyle == '-' else 'k')
            ax[1].plot(self.x_range, getattr(self, value['tau']), label=state, linestyle=linestyle, color=color if linestyle == '-' else 'k')
            
        ax[0].set_title(f'{self.name} steady state')
        ax[0].set_xlabel('V (mV)')
        ax[0].set_ylabel('Inf')
        ax[0].legend()
        ax[0].set_xscale(x_scale)

        ax[1].set_title(f'{self.name} time constant')
        ax[1].set_xlabel('V (mV)')
        ax[1].set_ylabel('Tau (ms)')
        ax[1].legend()
        ax[1].set_xscale(x_scale)

        return ax

        
class Capacitance(IonChannel):

    def __init__(self):
        super().__init__('Capacitance', 'cm')
        
class LeakChannel(IonChannel):

    def __init__(self, cell=None):
        super().__init__('Leak', 'leak', cell)
        self.ion = '_leak'

class CustomIonChannel(IonChannel):

    def __init__(self, name, suffix, cell=None):
        super().__init__(name, suffix, cell)

    def get_data_to_fit(self):
        data = {state: {'inf': getattr(self, self.state_vars[state]['inf']),
                    'tau': getattr(self, self.state_vars[state]['tau'])}
            for state in self.state_vars}
        data.update({'range': self.v_range})
        return data

    def update(self, x_range):
        self.init_state_vars(x_range)

    def init_state_vars(self, x_range):
        for state, params in self.state_vars.items():
            setattr(self, params['inf'], np.zeros_like(x_range))
            setattr(self, params['tau'], np.zeros_like(x_range))

    def update_constant_state_vars(self, x_range):
        def update_attr(attr_name):
            if isinstance(getattr(self, attr_name), (int, float)):
                setattr(self, attr_name, np.ones_like(x_range) * getattr(self, attr_name))

        for state_var, params in self.state_vars.items():
            # logger.debug(f'Updating {state_var} attributes with {params}')
            update_attr(params['inf'])
            update_attr(params['tau'])


class CustomVoltageDependentIonChannel(CustomIonChannel):

    def __init__(self, name, suffix, cell=None):
        super().__init__(name, suffix, cell)
        
class CustomCalciumDependentIonChannel(CustomIonChannel):

    def __init__(self, name, suffix, cell=None):
        super().__init__(name, suffix, cell)



                
class FallbackChannel(CustomIonChannel):
    """ This class is used to store the basic information (name and suffix)
    about a channel, when parsing the mod file fails.
    """
    def __init__(self, mod_file):
        with open(mod_file, 'r') as f:
            mod_text = f.read()
        # use regex to extract suffix from the NEURON block under SUFFIX keyword
        self.suffix = re.search(r'SUFFIX\s+(\w+)', mod_text).group(1)    
        self.name = mod_file.split('/')[-1].replace('.mod', '')

class CaDynamics():

    def __init__(self, mod_file):
        with open(mod_file, 'r') as f:
            mod_text = f.read()
        # use regex to extract suffix from the NEURON block under SUFFIX keyword
        self.suffix = re.search(r'SUFFIX\s+(\w+)', mod_text).group(1)
        self.name = mod_file.split('/')[-1].replace('.mod', '')


def steady_state(v, vhalf, sigma):
    return 1 / (1 + np.exp(-(v - vhalf) / sigma))

def time_constant(v, vhalf, sigma, k, delta, tau0):
    return 1 / (alpha_prime(v, vhalf, sigma, k, delta) + beta_prime(v, vhalf, sigma, k, delta)) + tau0

def alpha_prime(v, vhalf, sigma, k, delta):
    return k * np.exp(delta * (v - vhalf) / sigma)

def beta_prime(v, vhalf, sigma, k, delta):
    return k * np.exp(-(1 - delta) * (v - vhalf) / sigma)

def t_adj(celsius, q10=2.3, temp=23):
    return q10 ** ((celsius - temp) / 10)

class StandardIonChannel(IonChannel):

    def __init__(self, name, suffix, state_vars, ion='', cell=None):
        super().__init__(name, suffix + 's', cell)
        self.ion = ion
        self.celsius = 37
        self.state_vars = {state: {
            'inf': f'{state}_inf', 
            'tau': f'tau_{state}', 
            'power': params["power"]} 
            for state, params in state_vars.items()}

        self.range_params = [param for state in state_vars for param in [
            f'vhalf_{state}', f'sigma_{state}', f'k_{state}', f'delta_{state}', f'tau0_{state}']]

        for state in state_vars:
            setattr(self, f'vhalf_{state}', None)
            setattr(self, f'sigma_{state}', None)
            setattr(self, f'k_{state}', None)
            setattr(self, f'delta_{state}', None)
            setattr(self, f'tau0_{state}', None)

        
        

    def update(self, v_range):
        self.v_range = v_range
        tadj = t_adj(self.celsius)

        for state in self.state_vars:
            setattr(self, f'{state}_inf',
                    steady_state(v_range,
                                 vhalf=getattr(self, f'vhalf_{state}'),
                                 sigma=getattr(self, f'sigma_{state}')))
            setattr(self, f'tau_{state}',
                    time_constant(v=v_range,
                                  vhalf=getattr(self, f'vhalf_{state}'),
                                  sigma=getattr(self, f'sigma_{state}'),
                                  k=getattr(self, f'k_{state}'),
                                  delta=getattr(self, f'delta_{state}'),
                                  tau0=getattr(self, f'tau0_{state}'))/tadj)

    def fit_to_data(self, data, prioritized_inf=True, round_params=3):
        from symfit import exp

        for state in self.state_vars:
            v, inf, tau = variables('v, inf, tau')
            if data[state]['inf'][0] < data[state]['inf'][-1]:
                k, delta, vhalf, sigma, tau0 = parameters(
                    'k, delta, vhalf, sigma, tau0', value=[1, 0.5, 0, 10, 0])
            else:
                k, delta, vhalf, sigma, tau0 = parameters(
                    'k, delta, vhalf, sigma, tau0', value=[1, 0.5, 0, -10, 0])
            
            # First fit to both 'inf' and 'tau'
            model = Model({
                inf: 1 / (1 + exp(-(v - vhalf) / sigma)),
                tau: 1 / (k * exp(delta * (v - vhalf) / sigma) + k * exp(-(1 - delta) * (v - vhalf) / sigma)) + tau0,
            })

            fit = Fit(model, v=data['range'], inf=data[state]['inf'], tau=data[state]['tau'])
            fit_result = fit.execute()

            # Use the resulting parameters as initial values for the second fit
            vhalf.value = fit_result.params['vhalf']
            sigma.value = fit_result.params['sigma']

            # Second fit to 'inf' data only
            if prioritized_inf:
                model_inf = Model({
                    inf: 1 / (1 + exp(-(v - vhalf) / sigma))
                })

                fit_inf = Fit(model_inf, v=data['range'], inf=data[state]['inf'])
                fit_result_inf = fit_inf.execute()

            if round_params:
                fit_result.params = {key: round(value, round_params) for key, value in fit_result.params.items()}
                if prioritized_inf:
                    fit_result_inf.params = {key: round(value, round_params) for key, value in fit_result_inf.params.items()}

            # take only k, delta and tau0 from the first fit and vhalf and sigma from the second fit
            for param, value in fit_result.params.items():
                if param in ['k', 'delta', 'tau0', 'vhalf', 'sigma']:
                    setattr(self, f'{param}_{state}', value)
            
            if prioritized_inf:
                for param, value in fit_result_inf.params.items():
                    if param in ['vhalf', 'sigma']:
                        setattr(self, f'{param}_{state}', value)

    def write_to_mod_file(self, path_to_template, path_to_mod):
        # Read the template file
        with open(path_to_template, 'r') as file:
            template_string = file.read()

        # Create a Jinja2 template from the string
        template = Template(template_string)

        def get_unit(param):
            if param.startswith('vhalf_'): return 'mV'
            elif param.startswith('sigma_'): return 'mV'
            elif param.startswith('k_'): return '1/ms'
            elif param.startswith('delta_'): return '1'
            elif param.startswith('tau0_'): return 'ms'

        # Define the variables for the template
        variables = {
            'suffix': self.suffix,
            'ion': self.ion,
            'range_params': [(param, getattr(self, param), get_unit(param)) for param in self.range_params],
            'state_vars': {var: params['power'] for var, params in self.state_vars.items()},
        }

        # Render the template with the variables
        output = template.render(variables)

        # Write the output to a file
        # check if folder does not exist and create it
        import os
        if not os.path.exists(os.path.dirname(path_to_mod)):
            os.makedirs(os.path.dirname(path_to_mod))
        with open(path_to_mod, 'w') as file:
            file.write(output)

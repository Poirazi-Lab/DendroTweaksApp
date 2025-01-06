from collections import defaultdict
from pprint import pprint

class Section():

    def __init__(self, idx):
        self.idx = idx

    def __repr__(self):
        return f'Section({self.idx})'

    def set_distribution(self, parameter, distribution):
        print(f'For {self} set {parameter} from {distribution}')

class Distribution():

    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __call__(self):
        pass

    def __repr__(self):
        return f'Distribution({self.name})'

class Parameter():
    def __init__(self, name, mechanism_name=None, global_value=None):
        self.name = name
        self.mechanism_name = mechanism_name
        self.global_value = global_value
        self.distributions = {}

    def add_distribution(self, group_name, distr_name, distr_params):
        self.distributions[group_name] = Distribution(distr_name, distr_params)
        if self.mechanism_name is not None:
            self._insert_mechanism(group_name)

    def remove_distribution(self, group_name):
        self.distributions.pop(group_name)
        if self.mechanism_name is not None:
            self._remove_mechanism(group_name)

    def _insert_mechanism(self, group_name):
        for sec in self.groups[group_name]:
            sec.insert(self.mechanism_name)

    def uninsert_mechanism(self, group_name):
        for sec in self.groups[group_name]:
            sec.uninsert(self.mechanism_name)

class Model():

    def __init__(self, name):
        self.name = name
        self.groups = {
            'soma': [Section(0)], 
            'dend': [Section(1), Section(2), Section(3)]
        }
        self.parameters = {
            None: {
                'cm': {
                    'soma': 'uniform',
                    'dend': 'uniform',
                }, 
                'Ra': {
                    'soma': 'uniform',
                    'dend': 'uniform',
                }
            },
            "Leak": {
                'gbar': {
                    'soma': 'uniform',
                    'dend': 'uniform',
                }
            },
        }
        # self.global_parameters = {
        #     "Independent": {
        #         'cm': 1,
        #         'Ra': 100
        #     },
        #     "Leak": {
        #         'gbar': 0.0, # should it be here?
        #         'e': -70,
        #     },
        # }
        # self.distributed_parameters = {
        #     "Leak": {
        #         'gbar': {
        #             'soma': Uniform(0.0001),
        #             'dend': Uniform(0.0001),
        #             'apic': Uniform(0.0001),
        #         }
        #     },
        # }


    def add_distributed_parameter(self, parameter, mechanism):
        if self.parameters.get(mechanism) is None:
            self.parameters[mechanism] = {}
        default_value = self.global_parameters[mechanism].get(parameter)
        self.distributed_parameters[mechanism][parameter] = Uniform(default_value)

    def set_global_parameter(self, parameter, mechanism, value):
        if parameter in self.distributed_parameters[mechanism]:
            self.distributed_parameters[mechanism].pop(parameter)
            if not self.distributed_parameters[mechanism]:
                self.distributed_parameters.pop(mechanism)
        self.global_parameters[mechanism][parameter] = value

    @property
    def global_parameters(self):
        return {
            param_name: param.global_value 
            for mechanism in self.parameters
            for param_name, param in self.parameters[mechanism].items()
            if param.distributions == {}
        }

    @property
    def distributed_parameters(self):
        return {
            param_name: param.distributions
            for mechanism in self.parameters
            for param_name, param in self.parameters[mechanism].items()
            if param.distributions != {}
        }

    @property
    def groups_to_parameters(self):
        d = defaultdict(lambda: defaultdict(list))
        for mechanism in self.parameters:
            for param_name, param in self.parameters[mechanism].items():
                for group_name, distribution in param.distributions.items():
                    d[group_name][mechanism].append({param_name: distribution})
        return {k: dict(v) for k, v in d.items()}
            

    def distribute(self, parameter, mechanism="Independent"):
        param = self.parameters[mechanism][parameter]
        for group_name, distribution in param.distributions.items():
            for sec in self.groups[group_name]:
                sec.set_distribution(parameter, distribution)

    def add_distribution(self, parameter, mechanism, distr_name, distr_params, group_name):
        self.parameters[mechanism][parameter].add_distribution(group_name, distr_name, distr_params)
             

model = Model('Park_2019')
model.add_distribution('cm', 'Independent', 'uniform', {}, 'soma')
model.add_distribution('cm', 'Independent', 'uniform', {}, 'apic')
model.add_distribution('gbar', 'Leak', 'uniform', {}, 'soma')
model.global_parameters
model.distributed_parameters

model.distribute('cm')
pprint(model.groups_to_parameters)
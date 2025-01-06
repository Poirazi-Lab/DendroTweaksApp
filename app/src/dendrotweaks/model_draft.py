from collections import defaultdict
from pprint import pprint
from dataclasses import dataclass

class Section():

    def __init__(self, idx):
        self.idx = idx

    def __repr__(self):
        return f'Section({self.idx})'

    def insert(self, mechanism):
        print(f'For {self} insert {mechanism}')

    def set_distribution(self, parameter, distribution):
        print(f'For {self} set {parameter} from {distribution}')

class Distribution():

    def __init__(self, name, **params):
        self.name = name
        self.params = params

    def __call__(self):
        pass

    def __repr__(self):
        return f'<{self.name.capitalize()}({self.params})>'


@dataclass
class Mechanism:
    name: str
    parameters: dict

@dataclass
class SectionGroup:
    name: str
    sections: list

class Model():

    def __init__(self, name):
        self.name = name
        self._groups = []
        self.parameters = {
            None: {
                'cm': {
                    'soma': Distribution('uniform', value=1),
                    'dend': Distribution('uniform', value=1),
                }, 
                'Ra': {
                    'all': Distribution('uniform', value=100),
                }
            },
            # "Leak": {
            #     'gbar': {
            #         'soma': Distribution('uniform', value=0.0001),
            #         'dend': Distribution('uniform', value=0.0001),
            #     },
            #     'e': {
            #         'all': Distribution('uniform', value=-70),
            #     },
            # },
        }

    @property
    def groups(self):
        return {group.name: group.sections for group in self._groups}

    def add_group(self, name, sections):
        self._groups.append(SectionGroup(name, sections))

    def remove_group(self, name):
        self._groups = [group for group in self._groups if group.name != name]
        for mechanism in self.parameters:
            for parameter in self.parameters[mechanism]:
                parameter.pop(name, None)
                

    def move_group_down(self, name):
        idx = next(i for i, group in enumerate(self._groups) if group.name == name)
        if idx > 0:
            self._groups[idx-1], self._groups[idx] = self._groups[idx], self._groups[idx-1]

    def move_group_up(self, name):
        idx = next(i for i, group in enumerate(self._groups) if group.name == name)
        if idx < len(self._groups) - 1:
            self._groups[idx+1], self._groups[idx] = self._groups[idx], self._groups[idx+1]

    def insert_mechanism(self, mechanism: Mechanism, group_name: str):
        for section in self.groups[group_name]:
            section.insert(mechanism.name)
        for parameter, value in mechanism.parameters.items():
            group_to_distribution = {group_name: Distribution('uniform', value=value)}
            if mechanism.name not in self.parameters:
                self.parameters[mechanism.name] = {}
            if parameter not in self.parameters[mechanism.name]:
                self.parameters[mechanism.name][parameter] = {}
            self.parameters[mechanism.name][parameter].update(group_to_distribution)


    def insert_mechanism(self, mechanism: Mechanism, group_name: str):
        for section in self.groups[group_name]:
            section.insert(mechanism.name)
        
        self.parameters.setdefault(mechanism.name, {})
        
        for parameter, value in mechanism.parameters.items():
            self.parameters[mechanism.name].setdefault(parameter, {})
            self.parameters[mechanism.name][parameter][group_name] = Distribution('uniform', value=value)

    def set_distribution(self, 
                        parameter: str, 
                        mechanism: str, 
                        group: str, 
                        distribution_type: str, 
                        **distribution_params):

        self.parameters[mechanism][parameter][group] = Distribution(distribution_type, **distribution_params)

    def distribute(self, parameter:str, mechanism=None):
        for group_name, distribution in self.parameters[mechanism][parameter].items():
            for section in self.groups[group_name]:
                parameter_mechanism = parameter if mechanism is None else f'{parameter}_{mechanism}'
                section.set_distribution(parameter_mechanism, distribution)


model = Model('Park_2019')
model.add_group('soma', [Section(0)])
model.add_group('dend', [Section(1), Section(2), Section(3)])
model.add_group('all', [Section(0), Section(1), Section(2), Section(3)])

leak = Mechanism('Leak', {'gbar': 0.0001, 'e': -70})
model.insert_mechanism(leak, 'all')
model.set_distribution('gbar', 'Leak', 'all', 'uniform', value=0.0002)
pprint(model.parameters)

model.distribute('gbar', 'Leak')
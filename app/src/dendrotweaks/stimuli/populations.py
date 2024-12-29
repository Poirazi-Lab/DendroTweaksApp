from dendrotweaks.morphology.sec_trees import Section
from dendrotweaks.stimuli.synapses import Synapse

from typing import List
import numpy as np

class Population():
    """
    A population of "virtual" presynaptic neurons.
    """

    def __init__(self, name: str, sections: List[Section], N: int, syn_type: str) -> None:

        self.name = name
        self.sections = sections
        self.syn_type = syn_type

        self.N = N

        self.synapses = {}
        self.n_per_sec = {sec.idx: 0 for sec in sections}

        self.input_params = {
            'rate': 1,
            'noise': 1,
            'start': 100,
            'end': 200,
            'weight': 1,
            'delay': 0
        }

        self.kinetic_params = {
            "gmax": 0.001,
            "tau_rise": 0.2,
            "tau_decay": 1.4,
            "e": 0,
            "gamma": 0.062,
            "mu": 0.28
        }

    def update_kinetic_params(self, params:dict):
        self.kinetic_params.update(**params)
        for syns in self.synapses.values():
            for syn in syns:
                for key, value in params.items():
                    if hasattr(syn._ref_syn, key):
                        setattr(syn._ref_syn, key, value)

    def update_input_params(self, params: dict):
        self.input_params.update(**params)
        self.create_inputs()

    # ALLOCATION METHODS

    def _calculate_n_per_sec(self):
        """Assigns each section a random number of synapses 
        so that the sum of all synapses is equal to N synapses.
        returns a dict {sec:n_syn}"""
        self.n_per_sec = {sec.idx: 0 for sec in self.sections}
        for i in range(self.N):
            sec = np.random.choice(self.sections)
            self.n_per_sec[sec.idx] += 1

    def allocate_synapses(self):
        """Assigns each synapse a section and a location on that section."""
        self.synapses = {}
        self._calculate_n_per_sec()
        for sec in self.sections:
            n_per_sec = self.n_per_sec[sec.idx]
            # assign a random location between 0 and 1
            locs = np.round(np.random.rand(n_per_sec), decimals=2)
            syn_type = self.syn_type
            self.synapses[sec.idx] = [Synapse(syn_type, sec, loc) for loc in locs]

        self.update_kinetic_params(params=self.kinetic_params)


    # CREATION METHODS

    def create_inputs(self):
        """Creates and references the synapses in a simulator."""
        for syns in self.synapses.values():
            for syn in syns:

                syn.create_stim(
                    rate=self.input_params['rate'],
                    noise=self.input_params['noise'],
                    duration=self.input_params['end'] - self.input_params['start'],
                    delay=self.input_params['start']
                )

                syn.create_con(
                    delay=self.input_params['delay'],
                    weight=self.input_params['weight']
                )


    def to_dict(self):
        return {
            'population': {
                'name': self.name,
                'input_params': {**self.input_params},
                'kinetic_params': {**self.kinetic_params},
                'syn_type': self.syn_type,
                'synapses': self._synapses_to_dict(),
            }
        }

    def _synapses_to_dict(self):
        synapses_list = []
        for sec in self.sections:
            if self.synapses[sec.idx]:
                synapses_list.append({
                    'sec_idx': sec.idx,
                    'locs': [syn.loc for syn in self.synapses[sec.idx]]
                })
        return synapses_list
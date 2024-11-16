from typing import List
from dendrotweaks.trees.sec_trees import Section
from neuron import h
import numpy as np

class Synapse():
    """
    A synapse object that can be placed on a section of a neuron.

    Parameters
    ----------
    sec : Section
        The section of the neuron where the synapse is located.
    loc : float
        The location on the section where the synapse is placed, ranging from 0 to 1.

    Attributes
    ----------
    sec : Section
        The section of the neuron where the synapse is located.
    sec_idx : int
        The index of the section.
    loc : float
        The location on the section where the synapse is placed.
    _ref_syn : object, optional
        Reference to the NEURON synapse object.
    _ref_stim : object, optional
        Reference to the NEURON stimulus object.
    _ref_con : object, optional
        Reference to the NEURON connection object.
    """

    def __init__(self, sec: Section, loc: float) -> None:
        """
        Create a new synapse object.

        Parameters:
        ----------
        sec : Section
            The section of the neuron where the synapse is located.
        loc : float
            The location on the section where the synapse is placed, ranging from

        Returns:
        None
        """

        self.sec = sec
        self.sec_idx = sec.idx
        self.loc = loc

        self._ref_syn = None
        self._ref_stim = None
        self._ref_con = None


class Population():
    """
    A population of "virtual" presynaptic neurons.
    """

    def __init__(self, name: str, sections: List[Section], N: int, syn_type: str) -> None:

        self.name = name
        self.sections = sections
        self.syn_type = syn_type
        self.Model = getattr(h, syn_type)

        self.N = N

        self.synapses = {}
        self.n_per_sec = {sec.idx: 0 for sec in sections}

        self._rate = 1
        self._noise = 1
        self._start = 100
        self._end = 200
        self._weight = 1
        self.delay = 0

        self._gmax = 0.001
        self._tau_rise = 0.2
        self._tau_decay = 1.4
        self._e = 0
        self._gamma = 0.062
        self._mu = 0.28

    @property
    def rate(self):
        return self._rate

    @property
    def noise(self):
        return self._noise

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, value):
        self._weight = value
        for syns in self.synapses.values():
            for syn in syns:
                syn._ref_con.weight[0] = value

    @property
    def gmax(self):
        return self._gmax

    @gmax.setter
    def gmax(self, value):
        self._gmax = value
        for syns in self.synapses.values():
            for syn in syns:
                syn._ref_syn.gmax = value

    @property
    def tau_rise(self):
        return self._tau_rise

    @property
    def tau_decay(self):
        return self._tau_decay

    @property
    def e(self):
        return self._e

    @property
    def gamma(self):
        return self._gamma

    @property
    def mu(self):
        return self._mu

    def _calculate_n_per_sec(self):
        """Assigns each section a random number of synapses 
        so that the sum of all synapses is equal to N synapses.
        returns a dict {sec:n_syn}"""
        self.n_per_sec = {sec.idx: 0 for sec in self.sections}
        for i in range(self.N):
            sec = np.random.choice(self.sections)
            self.n_per_sec[sec.idx] += 1

    def assign_sec_and_loc(self):
        self.synapses = {}
        self._calculate_n_per_sec()
        for sec in self.sections:
            n_per_sec = self.n_per_sec[sec.idx]
            # assign a random location between 0 and 1
            locs = np.round(np.random.rand(n_per_sec), decimals=2)
            self.synapses[sec.idx] = [Synapse(sec, loc) for loc in locs]

    def create_and_reference(self):
        for syns in self.synapses.values():
            for syn in syns:
                seg = syn.sec._ref(syn.loc)

                syn._ref_syn = self.Model(seg)
                # syn._ref_syn.gmax = self._gmax

                syn._ref_stim = self._create_vecstim()

                syn._ref_con = h.NetCon(syn._ref_stim[0],
                                        syn._ref_syn,
                                        0,
                                        self.delay,
                                        self.weight)

    def _create_vecstim(self):

        spike_times = create_spike_times(rate=self.rate,
                                         noise=self.noise,
                                         duration=self.end - self.start,
                                         delay=self.start)
        spike_vec = h.Vector(spike_times)
        stim = h.VecStim()
        stim.play(spike_vec)

        return [stim, spike_vec]

    def to_dict(self):
        return {
            'population': {
                'name': self.name,
                'input_params': {
                    'rate': self.rate,
                    'noise': self.noise,
                    'start': self.start,
                    'end': self.end,
                    'weight': self.weight,
                    'delay': self.delay,
                },
                'kinetic_params': {
                    'gmax': self.gmax,
                    'tau_rise': self.tau_rise,
                    'tau_decay': self.tau_decay,
                    'e': self.e,
                    'gamma': self.gamma,
                    'mu': self.mu,
                },
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


def create_spike_times(rate=1, noise=1, duration=300, delay=0):
    """
    Create a spike train with a given regularity.

    Parameters:
    rate (float): The rate of the spike train, in Hz.
    duration (int): The total time to run the simulation for, in ms.
    delay (int): The delay before the spike train starts, in ms.
    regularity (float): A parameter between 0 and 1 that controls the regularity of the spike train. 
                        0 corresponds to a Poisson process, 1 corresponds to a regular spike train.

    Returns:
    np.array: The spike times as a vector, in ms.
    """

    if noise == 1:
        return delay + generate_poisson_process(rate, duration)
    else:
        return delay + generate_jittered_spikes(rate, duration, noise)


def generate_poisson_process(lam, dur):
    """
    Generate a Poisson process.

    Parameters:
    lam (float): The rate parameter (lambda) of the Poisson process, in Hz.
    dur (int): The total time to run the simulation for, in ms.

    Returns:
    np.array: The spike times as a vector, in ms.
    """
    dur_s = dur / 1000
    intervals = np.random.exponential(1/lam, int(lam*dur_s))
    spike_times = np.cumsum(intervals)
    spike_times = spike_times[spike_times <= dur_s]
    spike_times_ms = spike_times * 1000

    return spike_times_ms


def generate_jittered_spikes(rate, dur, noise):
    """
    Generate a jittered spike train.

    Parameters:
    rate (float): The rate of the spike train, in Hz.
    dur (int): The total time to run the simulation for, in ms.
    noise (float): A parameter that controls the amount of noise added to the spike times. 
                   Higher values correspond to more noise (more randomness).

    Returns:
    np.array: The spike times as a vector, in ms.
    """
    dur_s = dur / 1000
    spike_times = np.arange(0, dur_s, 1/rate)

    # Add noise
    noise_values = np.random.normal(0, noise/rate, len(spike_times))
    spike_times += noise_values

    # Ensure spike times are within the duration and sort them
    spike_times = spike_times[(spike_times >= 0) & (spike_times <= dur_s)]
    spike_times.sort()

    spike_times_ms = spike_times * 1000

    return spike_times_ms

from model.mechanisms.distributions import Distribution
# import neuron
from neuron import h
# neuron.load_mechanisms('app/model/mechanisms/mod/Synapses')


from collections import defaultdict
import numpy as np

from functools import cached_property

from logger import logger

from utils import get_seg_name

class Group():
    def __init__(self, idx, segments, param_name):
        self.idx = idx
        self.segments = segments
        self.param_name = param_name
        self._cell = segments[0].sec.cell()

        self._distribution = Distribution('uniform', value=0)

    # @property
    # def segments(self):
    #     return [seg for seg in self._cell.get_segments(self.sec_type) 
    #             if self.start <= self._cell.distance_from_soma(seg) <= self.end]

    # @property
    # def start(self):
    #     return self._start

    # @start.setter
    # def start(self, new_start):
    #     if 0 <= new_start <= self.end:
    #         self._start = new_start
    #         self.apply()
    #     else:
    #         raise ValueError(f'Start must be between 0 and {self.end}.')

    # @property
    # def end(self):
    #     return self._end if self._end is not None else self.max_distance

    # @end.setter
    # def end(self, new_end):
    #     if self.start <= new_end <= self.max_distance:
    #         self._end = new_end
    #         self.apply()
    #     else:
    #         raise ValueError(f'End must be between {self.start} and {self.max_distance}.')

    # @property
    # def max_distance(self):
    #     return max([self._cell.distance_from_soma(seg) for seg in self._cell.get_segments(self.sec_type)])

    # @cached_property
    # def max_distance(self):
    #     return max([cell.distance_from_soma(seg) for seg in self.segments])

    # def add_distribution(self, dtype, **kwargs):
    #     dtype_map = {
    #         "uniform": UniformDistribution,
    #         "linear": LinearDistribution
    #     }
    #     self.distributions.append(dtype_map[dtype](**kwargs))

    @property
    def distribution(self):
        return self._distribution

    @distribution.setter
    def distribution(self, new_distribution):
        self._distribution = new_distribution
        self.apply()

    def _apply_to_seg(self, seg):
        setattr(seg, self.param_name, self.distribution(self._cell.distance_from_soma(seg)))
        # print(f'Applied {self} to {seg} with value {getattr(seg, self.param_name)}.')

    def apply(self):
        for seg in self.segments:
            self._apply_to_seg(seg)
        logger.info(f'Applied {self} to {len(self.segments)} segments.')

    # def apply_distributions(self):
    #     for sec in getattr(cell, self.sec_type):
    #         for seg in sec:
    #             for distribution in self.distributions:
    #                 if distribution.start <= seg.x <= distribution.end:
    #                     setattr(seg, self.param_name, distribution(self.cell.distance_from_soma(seg)))

    # def update_range(self, start, end, value):
    #     self.distribution.add_range(start, end, value)
    

    # def get_data(self):
    #     return {'x': [seg.distance_from_soma for seg in self.segments], 
    #             'y': [self.distribution(seg.distance_from_soma) for seg in self.segments]}

    @property
    def name(self):
        return f'Group {self.idx}_{self.param_name} {self.distribution.f.func.__name__}'

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__().replace('Group ', '')

    def to_dict(self):
        return {'seg_names': [get_seg_name(seg) for seg in self.segments],
                'param_name': self.param_name, 
                'distribution': self.distribution.to_dict()
                }
        

        

class SynapseGroup():

    def __init__(self, idx:int, segments: list, syn_type: str) -> None:
        self.idx = idx
        self.segments = [seg for seg in segments]
        self.syn_type = syn_type
        self.Model = getattr(h, self.syn_type)
        
        self.N = 0
        self.n_per_seg = defaultdict(int)

        self._rate = 0
        self._noise = 0
        self._start = 0
        self._end = 0
        self._weight = 0
        self.delay = 0

        self._gmax = 0.001
        self._tau_rise = 0.2
        self._tau_decay = 1.4
        self._e = 0
        self._gamma = 0.062
        self._mu = 0.28

        self.syns = {}
        self.stims = {}
        self.cons = {}
        self.recs = {}
        
    @property
    def gmax(self):
        return self._gmax

    @gmax.setter
    def gmax(self, new_gmax):
        self._gmax = new_gmax
        for seg, syn in self.syns.items():
            for s in syn:
                s.gmax = self.gmax

    @property
    def tau_rise(self):
        return self._tau_rise

    @tau_rise.setter
    def tau_rise(self, new_tau_rise):
        self._tau_rise = new_tau_rise
        for seg, syn in self.syns.items():
            for s in syn:
                s.tau_rise = self.tau_rise

    @property
    def tau_decay(self):
        return self._tau_decay

    @tau_decay.setter
    def tau_decay(self, new_tau_decay):
        self._tau_decay = new_tau_decay
        for seg, syn in self.syns.items():
            for s in syn:
                s.tau_decay = self.tau_decay

    @property
    def gamma(self):
        return self._gamma

    @gamma.setter
    def gamma(self, new_gamma):
        self._gamma = new_gamma
        for seg, syn in self.syns.items():
            for s in syn:
                s.gamma = self.gamma

    @property
    def mu(self):
        return self._mu

    @mu.setter
    def mu(self, new_mu):
        self._mu = new_mu
        for seg, syn in self.syns.items():
            for s in syn:
                s.mu = self.mu

    @property
    def e(self):
        return self._e

    @e.setter
    def e(self, new_e):
        self._e = new_e
        for seg, syn in self.syns.items():
            for s in syn:
                s.e = self.e

    @property
    def rate(self):
        return self._rate

    @rate.setter
    def rate(self, new_rate):
        self._rate = new_rate
        self.clear_stims()
        self.clear_cons()
        self._add_stims()
        self._add_cons()
        # for seg, stim in self.stims.items():
        #     for s in stim:
        #         s.interval = 1000.0 / self.rate
        #         s.number = int((self.end - self.start) / s.interval)

    @property
    def noise(self):
        return self._noise

    @noise.setter
    def noise(self, new_noise):
        self._noise = new_noise
        self.clear_stims()
        self.clear_cons()
        self._add_stims()
        self._add_cons()

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, new_start):
        self._start = new_start
        self.clear_stims()
        self.clear_cons()
        self._add_stims()
        self._add_cons()
        # for seg, stim in self.stims.items():
        #     for s in stim:
        #         s.start = self.start
        #         s.number = int((self.end - self.start) / s.interval)

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, new_end):
        self._end = new_end
        self.clear_stims()
        self.clear_cons()
        self._add_stims()
        self._add_cons()
        # for seg, stim in self.stims.items():
        #     for s in stim:
        #         s.number = int((self.end - self.start) / s.interval)

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, new_weight):
        self._weight = new_weight
        for seg, con in self.cons.items():
            for c in con:
                c.weight[0] = self.weight

    def calculate_n_per_seg(self):
        """Assigns each segment a random number of synapses 
        so that the sum of all synapses is equal to N synapses.
        returns a dict {seg:n_syn}"""
        
        for i in range(self.N):
            seg = np.random.choice(self.segments)
            self.n_per_seg[seg] += 1

    def add_synapses(self, N):

        self.N = N
        self.calculate_n_per_seg()
        for seg in self.segments:
            n_per_seg = self.n_per_seg[seg]
            self.syns[seg] = [self.Model(seg) for _ in range(n_per_seg)]
            # if not syn_type=='NMDA':
            #     for syn in self.syns[seg]:
            #         syn.e = e
            #         syn.tau1 = tau1
            #         syn.tau2 = tau2
            # else:
            logger.debug(f'Type of synapse: {self.syn_type}.')
            if self.syn_type=='AMPA_NMDA':
                for syn in self.syns[seg]:
                    syn.gmax_AMPA = self.gmax_AMPA
                    syn.gmax_NMDA = self.gmax_NMDA
                    logger.debug(f'Created {self.syn_type} synapse with gmax_AMPA: {syn.gmax_AMPA} and gmax_NMDA: {syn.gmax_NMDA}.')
            else:
                for syn in self.syns[seg]:
                    syn.gmax = self.gmax
                # syn.g = g
        
        

    def add_net_stims(self, rate, noise, start, end):
        self._rate = rate
        self._noise = noise
        self._start = start
        self._end = end
        self._add_stims()

    def _add_stims(self):
        for seg in self.segments:
            n_per_seg = self.n_per_seg[seg]
            self.stims[seg] = [self._create_vecstim() for _ in range(n_per_seg)]
        
        
    def add_net_cons(self, weight, delay):
        self._weight = weight
        self.delay = delay
        self._add_cons()

    def _add_cons(self):
        for seg in self.segments:
            self.cons[seg] = [h.NetCon(stim[0], syn, 0, self.delay, self.weight) for stim, syn in zip(self.stims[seg], self.syns[seg])]
        
    def add_spike_times_recordings(self):
        self.recs = {}
        for seg in self.segments:
            self.recs[seg] = [h.Vector() for _ in range(self.n_per_seg[seg])]
            for con, rec in zip(self.cons[seg], self.recs[seg]):
                con.record(rec)

    def get_spike_times(self):
        spike_times = []
        for seg, rec in self.recs.items():
            spike_times.extend([list(r) for r in rec])
        return spike_times

    # def get_spike_times_data(self):
    #     data = {'x': [], 'y': [], 'color': []}
    #     for seg, recs in self.recs.items():
    #         data['x'].extend([list(r) for r in recs])
    #         data['y'].extend([f"{get_seg_name(seg)}_{i}" for i in range(len(recs))])
    #         data['color'].extend(['blue' for _ in range(len(recs))])
    #     return data

    def get_spike_times_data(self):
        data = {'x': [], 'y': [], 'color': []}
        for seg, stims in self.stims.items():
            data['x'].extend([s[1].to_python() for s in stims])
            data['y'].extend([f"{get_seg_name(seg)}_{i}" for i in range(len(stims))])
            data['color'].extend(['blue' for _ in range(len(stims))])
        return data

    # def apply(self):
    #     for seg in self.segments:
    #         n_per_seg = self.n_per_seg[seg]
    #         self.syns[seg] = [self.Synapse(seg) for _ in range(n_per_seg)]
    #         self.stims[seg] = [self._create_netstim() for _ in range(n_per_seg)]
    #         self.cons[seg] = [h.NetCon(stim, syn) for stim, syn in zip(self.stims[seg], self.syns[seg])]
    
    def _create_vecstim(self):

        spike_times = create_spike_times(rate=self.rate, 
                                        noise=self.noise,
                                        duration=self.end - self.start,
                                        delay=self.start)
        logger.debug(f'Creating VecStim with spike times: {spike_times}.')
        spike_vec = h.Vector(spike_times)
        stim = h.VecStim()
        stim.play(spike_vec)

        return [stim, spike_vec]

    def _create_netstim(self):
        # Create a new NetStim instance
        stim = h.NetStim()

        # Calculate the interval (in ms) from the rate (in Hz)
        stim.interval = 1000.0 / self.rate

        # Calculate the number of spikes from the simulation time, interval, and desired start and end times
        stim.number = int((self.end - self.start) / stim.interval)

        # Set the remaining parameters
        stim.start = self.start

        stim.noise = self.noise

        return stim


    @property
    def name(self):
        return f'SynGroup {self.idx}_{self.syn_type}_{self.N}'

    def clear(self):
        self.clear_syns()
        self.clear_stims()
        self.clear_cons()
        # self.clear_recs()

    def clear_syns(self):
        for seg in self.segments:
            for syn in self.syns[seg]:
                syn = None
            self.syns.pop(seg)

    def clear_stims(self):
        for seg in self.segments:
            for stim in self.stims[seg]:
                stim[0] = None
                stim[1] = None
                stim.pop(0)
                stim.pop(0)
            self.stims.pop(seg)

    def clear_cons(self):
        for seg in self.segments:
            for con in self.cons[seg]:
                con = None
            self.cons.pop(seg)

    # def clear_recs(self):
    #     for seg in self.segments:
    #         for rec in self.recs[seg]:
    #             rec = None
    #         self.recs.pop(seg)
    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__().replace('Group ', '')


class DoubleSynapseGroup(SynapseGroup):

    def __init__(self, idx:int, segments: list) -> None:
        super().__init__(idx, segments, syn_type='AMPA_NMDA')
        logger.debug(f'Creating DoubleSynapseGroup {self.idx} with {len(self.segments)} segments.')
        self.syn_type = 'AMPA_NMDA'
        self.Model = h.AMPA_NMDA
        self._gmax_AMPA = 0.001
        self._gmax_NMDA = 0.7 * 0.001

        self._tau_rise_AMPA = 0.1
        self._tau_decay_AMPA = 2.5

        self._tau_rise_NMDA = 2
        self._tau_decay_NMDA = 30

    @property
    def gmax_AMPA(self):
        return self._gmax_AMPA

    @gmax_AMPA.setter
    def gmax_AMPA(self, new_gmax_AMPA):
        logger.debug(f'gmax_AMPA: {new_gmax_AMPA}')
        self._gmax_AMPA = new_gmax_AMPA
        for seg, syn in self.syns.items():
            for s in syn:
                s.gmax_AMPA = self.gmax_AMPA

    @property
    def tau_rise_AMPA(self):
        return self._tau_rise_AMPA

    @tau_rise_AMPA.setter
    def tau_rise_AMPA(self, new_tau_rise_AMPA):
        logger.debug(f'tau_rise_AMPA: {new_tau_rise_AMPA}')
        self._tau_rise_AMPA = new_tau_rise_AMPA
        for seg, syn in self.syns.items():
            for s in syn:
                s.tau_rise_AMPA = self.tau_rise_AMPA

    @property
    def tau_decay_AMPA(self):
        return self._tau_decay_AMPA

    @tau_decay_AMPA.setter
    def tau_decay_AMPA(self, new_tau_decay_AMPA):
        logger.debug(f'tau_decay_AMPA: {new_tau_decay_AMPA}')
        self._tau_decay_AMPA = new_tau_decay_AMPA
        for seg, syn in self.syns.items():
            for s in syn:
                s.tau_decay_AMPA = self.tau_decay_AMPA

    @property
    def gmax_NMDA(self):
        return self._gmax_NMDA

    @gmax_NMDA.setter
    def gmax_NMDA(self, new_gmax_NMDA):
        logger.debug(f'gmax_NMDA: {new_gmax_NMDA}')
        self._gmax_NMDA = new_gmax_NMDA
        for seg, syn in self.syns.items():
            for s in syn:
                s.gmax_NMDA = self.gmax_NMDA

    @property
    def tau_rise_NMDA(self):
        return self._tau_rise_NMDA

    @tau_rise_NMDA.setter
    def tau_rise_NMDA(self, new_tau_rise_NMDA):
        logger.debug(f'tau_rise_NMDA: {new_tau_rise_NMDA}')
        self._tau_rise_NMDA = new_tau_rise_NMDA
        for seg, syn in self.syns.items():
            for s in syn:
                s.tau_rise_NMDA = self.tau_rise_NMDA

    @property
    def tau_decay_NMDA(self):
        return self._tau_decay_NMDA

    @tau_decay_NMDA.setter
    def tau_decay_NMDA(self, new_tau_decay_NMDA):
        logger.debug(f'tau_decay_NMDA: {new_tau_decay_NMDA}')
        self._tau_decay_NMDA = new_tau_decay_NMDA
        for seg, syn in self.syns.items():
            for s in syn:
                s.tau_decay_NMDA = self.tau_decay_NMDA

      

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


def generate_regular_spikes(rate, dur):
    """
    Generate a regular spike train.
    
    Parameters:
    rate (float): The rate of the spike train, in Hz.
    dur (int): The total time to run the simulation for, in ms.
    
    Returns:
    np.array: The spike times as a vector, in ms.
    """
    dur_s = dur / 1000
    spike_times = np.arange(0, dur_s, 1/rate)
    spike_times_ms = spike_times * 1000
    
    return spike_times_ms
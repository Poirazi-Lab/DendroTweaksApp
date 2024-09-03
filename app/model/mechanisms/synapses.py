from model.mechanisms.groups import SynapseGroup, DoubleSynapseGroup
from neuron import h

from collections import defaultdict
import numpy as np

# class Syn():

#     def __init__(self, seg, e, tau1, tau2, gbar):
#         self._syn = h.Exp2Syn(seg._seg)
#         self._e = e
#         self._tau1 = tau1
#         self._tau2 = tau2
#         self._gbar = gbar

#     @property
#     def e(self):
#         return self._e

#     @e.setter
#     def e(self, new_e):
#         self._e = new_e
#         self._syn.e = self._e

#     @property
#     def tau1(self):
#         return self._tau1

#     @tau1.setter
#     def tau1(self, new_tau1):
#         self._tau1 = new_tau1
#         self._syn.tau1 = self._tau1

#     @property
#     def tau2(self):
#         return self._tau2

#     @tau2.setter
#     def tau2(self, new_tau2):
#         self._tau2 = new_tau2
#         self._syn.tau2 = self._tau2

#     @property
#     def gbar(self):
#         return self._gbar

#     @gbar.setter
#     def gmax(self, new_gbar):
#         self._gbar = new_gbar
#         self._syn.gmax = self._gbar


# class AMPA(Syn):

#     def __init__(self, seg):
#         super().__init__(seg, e=0, tau1=0.1, tau2=1.0, gbar=0.001)

# class NMDA(Syn):

#     def __init__(self, seg):
#         super().__init__(seg, e=0, tau1=0.1, tau2=1.0, gbar=0.001)

# class GABAa(Syn):
    
#     def __init__(self, seg):
#         super().__init__(seg, e=-70, tau1=0.1, tau2=1.0, gbar=0.001)


# class NetStim():

#     def __init__(self, rate: float = 0, noise: float = 0, start: float = 0, end: float = 0) -> None:
#         self._netstim = h.NetStim()
#         self._rate = rate
#         self._noise = noise
#         self._start = start
#         self._end = end
        
#     @property
#     def rate(self):
#         return self._rate

#     @rate.setter
#     def rate(self, new_rate):
#         self._rate = new_rate
#         self._netstim.interval = 1000 / self._rate
        
#     @property
#     def noise(self):
#         return self._noise

#     @noise.setter
#     def noise(self, new_noise):
#         self._noise = new_noise
#         self._netstim.noise = self._noise

#     @property
#     def start(self):
#         return self._start

#     @start.setter
#     def start(self, new_start):
#         self._start = new_start
#         self._netstim.start = self._start * ms

#     @property
#     def end(self):
#         return self._end

#     @end.setter
#     def end(self, new_end):
#         self._end = new_end
#         self._netstim.number = (self._end - self._start) / self._rate



# class NetCon():
        
#         def __init__(self, stim: NetStim, syn: Syn, weight: float = 0, delay: float = 0) -> None:
#             self._netcon = h.NetCon(stim._netstim, syn._syn, 0, delay, weight)
#             self._weight = weight
#             self._delay = delay
#             self.spike_times = h.Vector()
#             self._netcon.record(self.spike_times)

#         @property
#         def weight(self):
#             return self._weight

#         @weight.setter
#         def weight(self, new_weight):
#             self._weight = new_weight
#             self._netcon.weight[0] = self._weight

#         @property
#         def delay(self):
#             return self._delay

#         @delay.setter
#         def delay(self, new_delay):
#             self._delay = new_delay
#             self._netcon.delay = self._delay


class Synapse():
    
    def __init__(self, name):
        self.name = name
        self.groups = []
        # self.e = e
        # self.tau_rise = tau_rise
        # self.tau_decay = tau_decay
        # self.gmax = gmax


    def add_group(self, segments, N_syn, rate=1, noise=0, start=100, end=200, weight=1, delay=0, tag: str = ''):
        group_id = len(self.groups)
        if self.name == 'AMPA_NMDA':
            group = DoubleSynapseGroup(group_id, segments)
            group.add_synapses(N_syn)
        else:
            group = SynapseGroup(group_id, segments, syn_type=self.name)
            group.add_synapses(N_syn)
        group.add_net_stims(rate, noise, start, end)
        group.add_net_cons(weight, delay)
        # group.add_spike_times_recordings()
        self.groups.append(group)

    def remove_group(self, group):
        group.clear()
        self.groups.remove(group)

    def remove_all_groups(self):
        for group in reversed(self.groups):
            self.remove_group(group)

    def get_by_name(self, name):
        for group in self.groups:
            if group.name == name:
                return group
        return None

    def __repr__(self):
        return f'Synapse {self.name} with {len(self.groups)} groups'

    def __str__(self):
        return f'{self.name} with {len(self.groups)} groups'.replace('Synapse', '').title()

# class AMPA(Synapse):

#     def __init__(self):
#         super().__init__('AMPA', e=0, tau1=0.1, tau2=2.5)

# class NMDA(Synapse):

#     def __init__(self):
#         super().__init__('NMDA', e=0, tau1=2, tau2=30.0)

# class AMPA_NMDA(Synapse):

#     def __init__(self):
#         super().__init__('AMPA_NMDA', e=0, tau1=0.1, tau2=2.5)

# class GABAa(Synapse):
        
#         def __init__(self):
#             super().__init__('GABAa', e=-70, tau1=0.2, tau2=1.4)


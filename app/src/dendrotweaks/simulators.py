from collections import defaultdict
import warnings

import matplotlib.pyplot as plt
import neuron
from neuron import h
from neuron.units import ms, mV
h.load_file('stdrun.hoc')
# h.load_file('import3d.hoc')
# h.load_file('nrngui.hoc')
# h.load_file('import3d')

import contextlib

@contextlib.contextmanager
def push_section(section):
    section.push()
    yield
    h.pop_section()

def reset_neuron():

    # h('forall delete_section()')
    # h('forall delete_all()')
    # h('forall delete()')

    for sec in h.allsec():
        with push_section(sec):
            h.delete_section()

reset_neuron()            

class Simulator:
    def __init__(self):
        self.vs = None
        self.t = None
        self.recordings = {}

    def plot_voltage(self, ax=None, segments=None):
        if ax is None:
            fig, ax = plt.subplots()
        if segments is None:
            segments = self.recordings.keys()
        if all(isinstance(seg, int) for seg in segments):
            segments = [seg for seg in self.recordings.keys() if seg.idx in segments]
        for seg in segments:
            ax.plot(self.t, self.vs[seg.idx], label=f'{seg.domain} {seg.idx}')

        if len(segments) < 10:
            ax.legend()
        ax.set_xlabel('Time (ms)')
        ax.set_ylabel('Voltage (mV)')
        

class NEURONSimulator(Simulator):
    """
    A class to represent a NEURON simulator.
    """

    def __init__(self, temperature=37, v_init=-70, dt=0.025, cvode=False):
        super().__init__()
        
        self.temperature = temperature
        self.v_init = v_init * mV

        self.dt = dt
        self._cvode = cvode


    def add_recording(self, sec, loc, var='v'):
        seg = sec(loc)
        if self.recordings.get(seg):
            self.remove_recording(sec, loc)
        self.recordings[seg] = h.Vector().record(getattr(seg._ref, f'_ref_{var}'))

    def remove_recording(self, sec, loc):
        seg = sec(loc)
        if self.recordings.get(seg):
            self.recordings[seg] = None
            self.recordings.pop(seg)

    def remove_all_recordings(self):
        for seg in self.recordings.keys():
            sec, loc = seg._section, seg.x
            self.remove_recording(sec, loc)
        if self.recordings:
            warnings.warn(f'Not all recordings were removed: {self.recordings}')
        self.recordings = {}


    def _init_simulation(self):
        h.CVode().active(self._cvode)
        h.celsius = self.temperature
        h.dt = self.dt
        h.stdinit()
        h.init()
        h.finitialize(self.v_init)
        if h.cvode.active():
            h.cvode.re_init()
        else:
            h.fcurrent()
        h.frecord_init()

    def run(self, duration=300):



        # vs = list(self.recordings.values())
        Is = []

        # for v in self.recordings.values():
        #     # v = h.Vector().record(seg._ref_v)
        #     vs.append(v)

        t = h.Vector().record(h._ref_t)

        # if self.ch is None:
        #     pass
        # else:
        #     for seg in self.recordings.keys():
        #         if getattr(seg, f'_ref_i_{self.ch.suffix}', None) is None:
        #             logger.warning(
        #                 f'No current recorded for {self.ch.suffix} at {seg}. Make i a RANGE variable in mod file.')
        #             continue
        #         I = h.Vector().record(getattr(seg, f'_ref_i_{self.ch.suffix}'))
        #         Is.append(I)

        self._init_simulation()

        h.continuerun(duration * ms)

        
        self.t = t.to_python()
        self.vs = {seg.idx: v.to_python() for seg, v in self.recordings.items()}
    
        return [self.t] * len(self.vs), list(self.vs.values()), Is

        

    def to_dict(self):
        return {
            'temperature': self.temperature,
            'v_init': self.v_init,
            'dt': self.dt,
        }

    def from_dict(self, data):
        self.temperature = data['temperature']
        self.v_init = data['v_init']
        self.dt = data['dt']


class JaxleySimulator(Simulator):
    """
    A class to represent a Jaxley simulator.
    """

    def __init__(self):
        super().__init__()
        ...

    

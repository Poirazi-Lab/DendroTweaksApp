import neuron
from neuron import h
from neuron.units import ms, mV
h.load_file('stdrun.hoc')

import numpy as np

from utils import timeit, get_sec_name, get_seg_name, get_sec_type

from logger import logger

from functools import cached_property

import warnings

import os
import shutil
import tempfile

def load_mechanisms(path_to_mod, suffix='', recompile=True, log=True):
    if hasattr(h, suffix):
        if log: logger.warning(f'Mechanism with suffix {suffix} already exists. Not loading "{path_to_mod}"')
        return

    if recompile:
        cwd = os.getcwd()
        os.chdir(path_to_mod)
        os.system('nrnivmodl')
        os.chdir(cwd)
        if log: logger.info(f'Recompiled mod files in "{path_to_mod}"')

    neuron.load_mechanisms(path_to_mod)
    if log: logger.info(f'Loaded mod files from "{path_to_mod}"')

load_mechanisms('app/model/mechanisms/mod/Synapses/', 
                recompile=not os.path.exists('app/model/mechanisms/mod/Synapses/x86_64/'))

import contextlib

@contextlib.contextmanager
def push_section(section):
    section.push()
    yield
    h.pop_section()

def reset_neuron():
    logger.info('Resetting NEURON')
    # h('forall delete_section()')
    # h('forall delete_all()')
    # h('forall delete()')

    for sec in h.allsec():
        with push_section(sec):
            h.delete_section()

reset_neuron()            


class Cell():
    """
    A class representing a biophysical NEURON model of a single neuron.
    """

    def __init__(self, swc_file):
        self.name = swc_file.split('/')[-1].replace('.swc', '').replace('.asc', '')
        self._load_morphology(swc_file)
        
    ### Morphology methods ###

    @cached_property
    def sections(self):
        return {get_sec_name(sec): sec for sec in self.all}

    @cached_property
    def segments(self):
        return {get_seg_name(seg): seg for sec in self.all for seg in sec}

    @cached_property
    def sec_types(self):
        sec_types = list(set([get_sec_type(sec) for sec in self.all]))
        if "soma" in sec_types:
            sec_types.remove("soma")
            sec_types.insert(0, "soma")
        return sec_types

    def get_segments(self, sec_type='all'):
        return [seg for sec in getattr(self, sec_type) for seg in sec]

    def __iter__(self):
        return iter(self.sections.values())

    def _load_morphology(self, fname):
        if fname.endswith('.swc'):
            self._load_swc(fname)
        elif fname.endswith('.asc'):
            self._load_asc(fname)
        else:
            raise ValueError(f'File format not supported. Supported formats are .swc and .asc.')

    def _load_swc(self, swc_file):
        h.load_file('import3d.hoc')
        swc_importer = h.Import3d_SWC_read()
        swc_importer.input(swc_file)
        imported_cell = h.Import3d_GUI(swc_importer, False)
        imported_cell.instantiate(self)

    def _load_asc(self, asc_file):
        h.load_file('import3d.hoc')
        asc_importer = h.Import3d_Neurolucida3()
        asc_importer.input(asc_file)
        imported_cell = h.Import3d_GUI(asc_importer, False)
        imported_cell.instantiate(self)

    def set_geom_nseg(self, d_lambda=0.1, f=100):
        if self.segments: del self.segments
        for sec in self.all:
            sec.nseg = int((sec.L/(d_lambda*h.lambda_f(f, sec=sec)) + 0.9)/2)*2 + 1
        

    @property
    def total_nseg(self):
        return sum([sec.nseg for sec in self.all])

    def distance_from_soma(self, seg):
        return h.distance(seg, self.soma[0](0.5))

    def distance(self, seg, from_seg=None):
        if from_seg is None:
            from_seg = self.soma[0](0.5)
        return h.distance(from_seg, seg)

class IClamp():

    def __init__(self, seg, amp=0, delay=100, dur=100):
        self._iclamp = h.IClamp(seg)
        self._iclamp.amp = amp
        self._iclamp.delay = delay
        self._iclamp.dur = dur
        
    @property
    def amp(self):
        return self._iclamp.amp

    @amp.setter
    def amp(self, new_amp):
        self._iclamp.amp = new_amp


    @property
    def delay(self):
        return self._iclamp.delay

    @delay.setter
    def delay(self, new_delay):
        self._iclamp.delay = new_delay

    @property
    def dur(self):
        return self._iclamp.dur

    @dur.setter
    def dur(self, new_dur):
        self._iclamp.dur = new_dur

class NetStim():

    def __init__(self, rate, noise, start, end):
        self._netstim = h.NetStim()
        self.update(rate, noise, start, end)

    def update(self, rate, noise, start, end):
        self._netstim.interval = 1000 / rate
        self._netstim.noise = noise
        self._netstim.start = start * ms
        self._netstim.number = (end - start) / rate



class Simulator():

    def __init__(self, celsius=37, v_init=-70, dt=0.025, cvode=False):
        
        self.celsius = celsius
        self.v_init = v_init * mV
        
        self.dt = dt
        self._cvode = cvode

        self.recordings = {}

        self.ch = None
        # self.t = []

    def add_recording(self, seg, var='v'):
        if self.recordings.get(seg):
            self.remove_recording(seg)
            warnings.warn(f'Recording for {var} at {seg} already exists. Overwriting.')
        self.recordings[seg] = h.Vector().record(getattr(seg, f'_ref_{var}'))
        logger.debug(f'Added recording for {var} at {seg}.')
        
    def remove_recording(self, seg, var='v'):
        if self.recordings.get(seg):
            self.recordings[seg] = None
            self.recordings.pop(seg)
            logger.debug(f'Removed recording for {var} at {seg}.')

    def remove_all_recordings(self):
        for seg in list(self.recordings.keys()):
            self.remove_recording(seg)
        # self.recordings = {}
        logger.debug('Removed all recordings.')

       
    def _init_simulation(self):
        h.CVode().active(self._cvode)
        h.celsius = self.celsius
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

        vs = [v for v in self.recordings.values()]
        Is = []
        
        # for v in self.recordings.values():
        #     # v = h.Vector().record(seg._ref_v)
        #     vs.append(v)

        t = h.Vector().record(h._ref_t)
        self.t = t

        if self.ch is None:
            pass
        else:
            for seg in self.recordings.keys():
                if getattr(seg, f'_ref_i_{self.ch.suffix}', None) is None:
                    logger.warning(f'No current recorded for {self.ch.suffix} at {seg}. Make i a RANGE variable in mod file.')
                    continue
                I = h.Vector().record(getattr(seg, f'_ref_i_{self.ch.suffix}'))
                Is.append(I)


        self._init_simulation()
                             
        h.continuerun(duration * ms)

        return [t.to_python() for _ in vs], [v.to_python() for v in vs], [i.to_python() for i in Is]

    def to_dict(self):
        return {
            'celsius': self.celsius,
            'v_init': self.v_init,
            'dt': self.dt,
        }


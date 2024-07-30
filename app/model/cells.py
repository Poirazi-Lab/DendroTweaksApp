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

if os.path.exists('app/model/mechanisms/mod/Synapses/'):
    load_mechanisms('app/model/mechanisms/mod/Synapses/', recompile=False)
else:
    load_mechanisms('model/mechanisms/mod/Synapses/', recompile=False)


# def load_mechanisms(path_to_mod, suffix=''):
#     if hasattr(h, suffix):
#         warnings.warn(f'Mechanism with suffix {suffix} already exists.')
#         return
#     path_to_mod = path_to_mod.replace('//', '/')
#     # Get the parent directory of mod_folder
#     parent_dir = os.path.dirname(os.path.dirname(path_to_mod))
#     print(f'Parent directory:"{parent_dir}"')

#     # Create a temporary directory in the parent directory
#     temp_dir = tempfile.mkdtemp(dir=parent_dir)
#     print(f'Temporary directory: "{temp_dir}"')

#     # Copy the .mod files from mod_folder to the temporary directory
#     for filename in os.listdir(path_to_mod):
#         if filename.endswith('.mod'):
#             print(f'    Coping "{filename}"...')
#             shutil.copy(os.path.join(path_to_mod, filename), temp_dir)

#     # Compile the mechanisms in the temporary directory
#     cwd = os.getcwd()
#     os.chdir(temp_dir)
#     os.system('nrnivmodl')
#     os.chdir(cwd)

#     # Load the mechanisms from the temporary directory
#     neuron.load_mechanisms(temp_dir)

#     # Delete the temporary directory
#     if temp_dir.startswith('model/mechanisms/'):
#         print(f'Removing temporary directory "{temp_dir}"')
#         shutil.rmtree(temp_dir)
#     else:
#         raise ValueError(f'Not removing "{temp_dir}" because it is not a temporary directory.')



# class Section():
#     def __init__(self, sec):
#         self._sec = sec
#         self._children = []
#         self._parent = None
#         self._segments = [Segment(seg) for seg in sec]
#         for seg in self._segments:
#             seg.sec = self

#     def __iter__(self):
#         return iter([Segment(seg) for seg in self._sec])

#     def __call__(self, x):
#         return Segment(self._sec(x))

#     def __eq__(self, other):
#         return self._sec == other._sec

#     def __hash__(self):
#         return hash(self._sec)

#     def psection(self):
#         return self._sec.psection()

#     def n3d(self):
#         return self._sec.n3d()

#     def x3d(self, i):
#         return self._sec.x3d(i)

#     def y3d(self, i):
#         return self._sec.y3d(i)

#     def z3d(self, i):
#         return self._sec.z3d(i)

#     def diam3d(self, i):
#         return self._sec.diam3d(i)

#     def children(self):
#         return [Section(sec) for sec in self._sec.children()]

#     def parent(self):
#         return Section(self._sec.parentseg().sec) if self._sec.parentseg() else None

#     @property
#     def name(self):
#         return self._sec.name().split('.')[-1]

#     @property
#     def sec_type(self):
#         return self.name.split('[')[0]

#     @property
#     def sec_id(self):
#         return self.name.split('[')[1].split(']')[0]

#     @property
#     def cell(self):
#         return self._sec.cell

#     def has_membrane(self, name):
#         return self._sec.has_membrane(mech)

#     @property
#     def pts3d(self):
#         return [(self._sec.x3d(i), self._sec.y3d(i), self._sec.z3d(i)) for i in range(self._sec.n3d())]

#     @property
#     def L(self):
#         return self._sec.L

#     @property
#     def nseg(self):
#         return self._sec.nseg

#     @nseg.setter
#     def nseg(self, new_nseg):
#         self._sec.nseg = new_nseg

#     @property
#     def diam(self):
#         return self._sec.diam

#     def __repr__(self):
#         return f'Sec {self.sec_type}[{self.sec_id}]'

#     def __str__(self):
#         return self.__repr__().replace('Sec ', '')

# class Segment():
#     __slots__ = ['_seg', 'sec']

#     def __init__(self, seg):
#         self._seg = seg
#         self.sec = Section(seg.sec)

#     def __eq__(self, other):
#         return self._seg == other._seg

#     def __hash__(self):
#         return hash(self._seg)

#     @property
#     def name(self):
#         return f'{self.sec.name}({self.x})'

#     @property
#     def sec_type(self):
#         return self.sec.sec_type

#     @property
#     def sec_id(self):
#         return self.sec.sec_id
    
#     @property    
#     def x(self):
#         return round(self._seg.x, 5)

#     @property
#     def cell(self):
#         return self.sec.cell()

#     @property
#     def distance_from_soma(self):
#         return h.distance(self._seg, self.cell.soma[0](0.5))

#     def __repr__(self):
#         return f'Seg {self.sec.sec_type}[{self.sec.sec_id}]({round(self.x, 5)})'

#     def __str__(self):
#         return self.__repr__().replace('Seg ', '')

#     def __getattr__(self, attr):
#         return getattr(self._seg, attr)

#     def __setattr__(self, attr, value):
#         if attr in ('_seg', 'sec'):
#             super().__setattr__(attr, value)
#         else:
#             setattr(self._seg, attr, value)
#     #     else:
#     #         raise AttributeError(f'Attribute {name} is neither a segment attribute nor a membrane mechanism.')


class Cell():
    """
    A class representing a biophysical NEURON model of a single neuron.
    """

    def __init__(self, swc_file):
        self.name = swc_file.split('/')[-1].replace('.swc', '').replace('.asc', '')
        self._load_morphology(swc_file)
        
    ### Morphology methods ###

    # def create_tree_recursively(self, sec, parent=None):
    #     section = Section(sec)
    #     section._parent = parent
    #     for child in sec.children():
    #         section._children.append(Section(child))
    #         self.create_tree_recursively(child_sec, parent=section)
    #     self.sections[section.name] = section
        
    

    # @cached_property
    # def sections(self):
    #     return {sec.name: sec for sec in (Section(s) for s in self.all)}

    # @cached_property
    # def segments(self):
    #     return {seg.name: seg for sec in self.all for seg in (Segment(s) for s in sec)}

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

    # def _record_current(self, ch):
    #     for seg in self.recordings.keys():
    #         if getattr(seg, f'_ref_i_{ch.suffix}', None) is None:
    #             logger.warning(f'No current recorded for {ch.suffix} at {seg}. Make i a RANGE variable in mod file.')
    #             continue
    #         I = h.Vector().record(getattr(seg, f'_ref_i_{ch.suffix}'))
    #         Is.append(I)

    
    # @timeit
    # def run(self, duration=300):
    #     logger.info(f'Starting simulation for {duration} ms')

    #     vs = []
    #     Is = []
        
    #     for v in self.recordings.values():
    #         # v = h.Vector().record(seg._ref_v)
    #         vs.append(v)
    #     t = h.Vector().record(h._ref_t)
        
    #     # if ch is None:
    #     #     pass
    #     # else:
    #     #     for seg in self.recordings.keys():
    #     #         if getattr(seg, f'_ref_i_{ch.suffix}', None) is None:
    #     #             logger.warning(f'No current recorded for {ch.suffix} at {seg}. Make i a RANGE variable in mod file.')
    #     #             continue
    #     #         I = h.Vector().record(getattr(seg, f'_ref_i_{ch.suffix}'))
    #     #         Is.append(I)

    #     self._init_simulation()
                             
    #     h.continuerun(duration * ms)

    #     return np.tile(t, (len(vs), 1)), np.array(vs), np.array(Is)


    
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




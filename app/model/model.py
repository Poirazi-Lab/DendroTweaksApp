from model.cells import Cell, Simulator, IClamp
from model.mechanisms.channels import CustomIonChannel, StandardIonChannel, LeakChannel, Capacitance, DummyChannel
# from mechanisms.synapses import AMPA, NMDA, GABAa
from model.swcmanager import SWCManager

from model.mechanisms.distributions import Distribution
from model.mechanisms.groups import Group

import warnings
from logger import logger

import os

from model.mechanisms.pparser import parser

from importlib import import_module

from model.mechanisms.synapses import Synapse #AMPA, NMDA, GABAa, AMPA_NMDA
from reduce.mini_reduce import reduce_subtree

def dynamic_import(module_name, class_name):
    module = import_module(module_name)
    return getattr(module, class_name)

from model.cells import load_mechanisms

class CellModel():

    def __init__(self, path_to_model=''):

        self.cell = None
        self.parser = parser
        
        self.iclamps = {}
        self.channels = {}
        self.synapses = {'AMPA': Synapse('AMPA'), 'NMDA': Synapse('NMDA'), 'GABAa': Synapse('GABAa'), 'AMPA_NMDA': Synapse('AMPA_NMDA')}

        self.simulator = Simulator()
        self.capacitance = None
        self.equilibrium_potentials = {}
        self.cadyn_suffix = None

        self.swcm = SWCManager()

        self.path_to_model = path_to_model

    def create_cell(self, swc_file):
            
        self.__init__(path_to_model=self.path_to_model)
        self.cell = Cell(swc_file)

    def list_swc_files(self):
        path = self.path_to_model + 'swc/'
        return [f for f in os.listdir(path) if f.endswith('.swc') or f.endswith('.asc')]

    def list_mod_files(self, mod_folder='mod'):
        path = self.path_to_model + f'mechanisms/{mod_folder}/'
        mod_files = [f for f in os.listdir(path) if os.path.isdir(path + f)]
        if "Synapses" in mod_files:
            mod_files.remove("Synapses")
        sorted_mod_files = sorted(mod_files, key=lambda x: x.lower())
        return sorted_mod_files


    def create_from_mod(self, mod_name, mod_folder='mod'):
        try:
            self.parser.parse(mod_file=f'{self.path_to_model}mechanisms/{mod_folder}/{mod_name}/{mod_name}.mod')
            self.parser.write_python(py_file=f'{self.path_to_model}mechanisms/collection/{mod_name}.py')
            Channel = dynamic_import(module_name=f'model.mechanisms.collection.{mod_name}', class_name=mod_name)
            return Channel()
        except:
            ch = DummyChannel(mod_file=f'{self.path_to_model}mechanisms/{mod_folder}/{mod_name}/{mod_name}.mod')
            logger.warning(f'Failed to create channel "{mod_name}" from mod file. Creating an empty channel to insert the {ch.suffix} mechanism.')
            return ch

    def add_capacitance(self):
        self.capacitance = Capacitance()
        self.capacitance.add_group(list(self.cell.segments.values()), 
                                        'cm', 
                                        Distribution('uniform', value=1))

    def add_ca_dynamics(self, mod_name='Park_Ca_dyn'):
        if self.cadyn_suffix:
            warnings.warn(f'Ca dynamics already exists. Overwriting.')
            self.remove_ca_dynamics()

        self.parser.parse_basic(mod_file=f'{self.path_to_model}mechanisms/mod_cadyn/{mod_name}/{mod_name}.mod')
        self.cadyn_suffix = self.parser.suffix
        load_mechanisms(f'{self.path_to_model}mechanisms/mod_cadyn/{mod_name}/', suffix=self.cadyn_suffix, recompile=True)
        for sec in self.cell.all:
            sec.insert(self.cadyn_suffix)

    def remove_ca_dynamics(self):
        for sec in self.cell.all:
            if sec.has_membrane(self.cadyn_suffix):
                sec.uninsert(self.cadyn_suffix)
        self.cadyn_suffix = None
        logger.info(f'Removed Ca dynamics.')
        

    def add_channel(self, mod_name, recompile=True):

        if self.channels.get(mod_name):
            warnings.warn(f'Channel {mod_name} already exists. Overwriting.')
            self.remove_channel(mod_name)

        mod_folder = 'mod_standard'  if 'standard' in mod_name else 'mod'

        if mod_name == 'Leak':
            ch = LeakChannel()
        # elif 'standard' in mod_name:
        #     self.parser.parse(mod_file=f'{self.path_to_model}mechanisms/mod_standard/{mod_name}/{mod_name}.mod')
        #     ch =  StandardIonChannel(name=mod_name, 
        #                              suffix=self.parser.ast['mod_file']['neuron_block']['suffix'],
        #                              ion=self.parser.ion,
        #                              state_vars=self.parser.state_vars)
        else:
            ch = self.create_from_mod(mod_name, mod_folder=mod_folder)

        # if recompile: self.recompile_mods(f'{self.path_to_model}/mechanisms/mod/{mod_name}/')
        load_mechanisms(f'{self.path_to_model}mechanisms/{mod_folder}/{mod_name}/', suffix=ch.suffix, recompile=recompile)

        for sec in self.cell.all:
            sec.insert(ch.suffix)

        
        self.channels[ch.name] = ch

        logger.info(f'Added channel "{ch.name}" with suffix "{ch.suffix}"\n\n\n')

        return ch

    def remove_channel(self, mod_name):

        if self.channels.get(mod_name):
            ch = self.channels[mod_name]
            ch.remove_all_groups()
            for sec in self.cell.all:
                if sec.has_membrane(ch.suffix):
                    sec.uninsert(ch.suffix)
            self.channels[mod_name] = None
            self.channels.pop(mod_name)
            logger.info(f'Removed channel "{ch.name}" with suffix "{ch.suffix}"')

    
    def standardize_channel(self, custom_ch):
        if isinstance(custom_ch, str):
            custom_ch = self.channels[custom_ch]
        if not isinstance(custom_ch, CustomIonChannel):
            warnings.warn(f'Channel "{ch_name}" is not a custom channel. Cannot standardize.')
            return

        logger.info(f'Custom channel: {custom_ch.name}')
        if getattr(custom_ch, 'temp', None) is None:
            custom_ch.temp = 37
            logger.warning(f'No temperature specified for {custom_ch.name}. Setting to {custom_ch.temp} degC')
        custom_ch.celsius = custom_ch.temp
        custom_ch.update(custom_ch.v_range)

        standard_ch = StandardIonChannel(name=custom_ch.name,
                                         suffix=custom_ch.suffix,
                                         ion=custom_ch.ion if hasattr(custom_ch, 'ion') else None,
                                         state_vars=custom_ch.state_vars.copy())

        data = custom_ch.get_data_to_fit()
        standard_ch.fit_to_data(data, prioritized_inf=True)
        standard_ch.write_to_mod_file(path_to_template=self.path_to_model + 'mechanisms/template.mod',
                                      path_to_mod=self.path_to_model + f'mechanisms/mod_standard/{standard_ch.name}_standard/{standard_ch.name}_standard.mod') 


    ### Synapse methods ###

    def add_synapse(self, mod_name):
        Synapse = dynamic_import(module_name=f'mechanisms.synapses', class_name=mod_name)
        self.synapses[mod_name] = Synapse()
        logger.info(f'Added synapse "{mod_name}"')

    def remove_synapse(self, mod_name):
        if self.synapses.get(mod_name):
            self.synapses[mod_name] = None
            self.synapses.pop(mod_name)
            logger.info(f'Removed synapse "{mod_name}"')



    ### IClamp methods ###

    def add_iclamp(self, seg, amp=0, delay=100, dur=100):
        if self.iclamps.get(seg):
            self.remove_iclamp(seg)
            warnings.warn(f'IClamp at {seg} already exists. Overwriting.')
        self.iclamps[seg] = IClamp(seg, amp, delay, dur)
        logger.info(f'Added IClamp at {seg}.')

    def update_iclamp(self, seg, amp, delay, dur):
        if self.iclamps.get(seg):
            self.iclamps[seg].update(amp, delay, dur)
            logger.info(f'Updated IClamp at {seg}.')
        else:
            warnings.warn(f'IClamp at {seg} does not exist. Creating new IClamp.')
            self.add_iclamp(seg, amp, delay, dur)
        
    def remove_iclamp(self, seg):
        if self.iclamps.get(seg):
            self.iclamps[seg] = None
            self.iclamps.pop(seg)
            logger.info(f'Removed IClamp at {seg}.')

    def remove_all_iclamps(self):
        for seg in list(self.iclamps.keys()):
            self.remove_iclamp(seg)
        logger.info('Removed all IClamps.')

    

    def remove_all_synapses(self):
        for syn in self.synapses.values():
            syn.remove_all_groups()


    def update_e(self, ion:str='_leak', value: float=-70) -> None:
        self.equilibrium_potentials[ion] = value
        for sec in self.cell.all:
            for seg in sec:
                logger.debug(f'Setting e{ion} at {sec.name()}({seg.x}) to {value}')
                setattr(seg, f'e{ion}', value)


    ### Simulation methods ###

    def run(self, duration):
        return self.simulator.run(duration)

    ### Reduction methods ###

    def reduce_subtree(self, root):
        reduce_subtree(cell=self.cell,
                       root=root)

    ### Export methods ###

    def to_dict(self):
        # only channels
        return {'channels': [ch.to_dict() for ch in self.channels.values()], 
                'equilibrium_potentials': self.equilibrium_potentials,
                'capacitance': self.capacitance.to_dict() if self.capacitance else None,
                'simulator': self.simulator.to_dict(),
                'path_to_model': self.path_to_model}

    def to_swc(self, path):
        self.swcm.from_hoc(hoc_sections=self.cell.all, soma_format='3PS')
        self.swcm.export2swc(path)

    def to_json(self, path):
        
        import json

        data = self.to_dict()

        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def from_json(self, path):
        
        import json

        with open(path, 'r') as f:
            data = json.load(f)

        for ch in data['channels']:
            # mod_file = f"{data['path_to_model']}/mechanisms/{ch['name']}/{ch['name']}.mod"
            if not self.channels.get(ch['name']):
                self.add_channel(ch['name'], recompile=False)
            for group in ch['groups']:
                segments = [self.cell.segments[seg_name] for seg_name in group['seg_names']]
                self.channels[ch['name']].add_group(segments,
                                                    group['param_name'])
                self.channels[ch['name']].groups[-1].distribution = Distribution.from_dict(group['distribution'])
                                                        
                    

    def to_hoc(self, path):
        pass
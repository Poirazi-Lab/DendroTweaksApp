from typing import List, Union, Callable
import os
import warnings
import json

from dendrotweaks.morphology.swc_trees import SWCTree
from dendrotweaks.morphology.sec_trees import Section, SectionTree
from dendrotweaks.morphology.seg_trees import Segment, SegmentTree
from dendrotweaks.simulators import NEURONSimulator
from dendrotweaks.membrane.groups import SectionGroup, SegmentGroup
from dendrotweaks.membrane.mechanisms import Mechanism, LeakChannel
from dendrotweaks.membrane.io import MechanismFactory
from dendrotweaks.membrane.io import MODFileLoader
from dendrotweaks.morphology.io import TreeFactory
from dendrotweaks.stimuli.iclamps import IClamp
from dendrotweaks.membrane.distributions import Distribution
from dendrotweaks.stimuli.populations import Population
from dendrotweaks.utils import calculate_lambda_f, dynamic_import

from collections import OrderedDict, defaultdict

# from .logger import logger

from dendrotweaks.path_manager import PathManager

from dataclasses import dataclass

import pandas as pd

INDEPENDENT_PARAMS = {
    'cm': 1, # uF/cm2
    'Ra': 100, # Ohm cm
    'ena': 50, # mV
    'ek': -77, # mV
    'eca': 140 # mV
}


class Model():
    """
    A model object that represents a neuron model.

    Parameters
    ----------
    name : str
        The name of the model.
    simulator_name : str
        The name of the simulator to use (either 'NEURON' or 'Jaxley').
    path_to_data : str
        The path to the data files where swc and mod files are stored.
    group_by : str
        The grouping method to use (either 'segments' or 'sections').
    """

    def __init__(self, name: str,
                 simulator_name='NEURON',
                 path_to_data='data',
                 group_by='sections') -> None:

        # Metadata
        self._name = name
        self.path_manager = PathManager(path_to_data, model_name=name)
        self.simulator_name = simulator_name

        # File managers
        self.tree_factory = TreeFactory()
        self.mechanism_factory = MechanismFactory()
        self.mod_loader = MODFileLoader()

        # Morphology
        self.swc_tree = None
        self.sec_tree = None

        # Mechanisms
        self.mechanisms = {}
        self.domains_to_mechanisms = {}

        # Parameters
        self.params = {
            'cm': {'all': Distribution('constant', value=1)}, # uF/cm2
            'Ra': {'all': Distribution('constant', value=35.4)}, # Ohm cm
        }

        # Groups
        self._groups = []

        # Distributions
        # self.distributed_params = {}

        # Segmentation
        self._d_lambda = None
        self.seg_tree = None

        # Stimuli
        self.iclamps = {}
        self.populations = {'AMPA': {}, 'NMDA': {}, 'AMPA_NMDA': {}, 'GABAa': {}}

        # Simulator
        if simulator_name == 'NEURON':
            self.simulator = NEURONSimulator()
        elif simulator_name == 'Jaxley':
            self.simulator = JaxleySimulator()
        else:
            raise ValueError(
                'Simulator name not recognized. Use NEURON or Jaxley.')

    # -----------------------------------------------------------------------
    # PROPERTIES
    # -----------------------------------------------------------------------

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        self.path_manager.update_paths(name)

    @property
    def domains(self):
        return list({sec.domain for sec in self.sec_tree.sections})

    @property
    def recordings(self):
        return self.simulator.recordings


    @recordings.setter
    def recordings(self, recordings):
        self.simulator.recordings = recordings


    @property
    def groups(self):
        return {group.name: group for group in self._groups}


    @property
    def groups_to_parameters(self):
        """
        Return a dictionary of groups to parameters.
        group : mechanism : parameter
        """
        groups_to_parameters = {}
        for group in self._groups:
            groups_to_parameters[group.name] = {}
            for mech_name, params in self.mechs_to_params.items():
                if mech_name not in group.mechanisms:
                    continue
                groups_to_parameters[group.name] = params
        return groups_to_parameters


    @property
    def parameters_to_groups(self):
        """
        Return a dictionary of parameters to groups.
        """
        parameters_to_groups = defaultdict(list)
        for group in self._groups:
            for mech_name, params in self.mechs_to_params.items():
                if mech_name not in group.mechanisms:
                    continue
                for param in params:
                    parameters_to_groups[param].append(group.name)
        return dict(parameters_to_groups)


    # @property
    # def params(self):
    #     # combine global and distributed parameters
    #     return {**self.distributed_params, **self.global_params}


    @property
    def params_to_mechs(self):
        params_to_mechs = {}
        # Sort mechanisms by length (longer first) to ensure specific matches
        sorted_mechs = sorted(self.mechanisms, key=len, reverse=True)
        for param in self.params:
            matched = False
            for mech in sorted_mechs:
                suffix = f"_{mech}"  # Define exact suffix
                if param.endswith(suffix):
                    params_to_mechs[param] = mech
                    matched = True
                    break
            if not matched:
                params_to_mechs[param] = "Independent"  # No match found
        return params_to_mechs


    @property
    def mechs_to_params(self):
        mechs_to_params = defaultdict(list)
        for param, mech_name in self.params_to_mechs.items():
            mechs_to_params[mech_name].append(param)
        return dict(mechs_to_params)


    # -----------------------------------------------------------------------
    # METADATA
    # -----------------------------------------------------------------------


    def info(self):
        """
        Print information about the model.
        """
        info_str = (
            f"Model: {self.name}\n"
            f"Path to data: {self.path_manager.path_to_data}\n"
            f"Simulator: {self.simulator_name}\n"
            f"Groups: {len(self.groups)}\n"
            f"Avaliable mechanisms: {len(self.mechanisms)}\n"
            f"Inserted mechanisms: {len(self.mechs_to_params) - 1}\n"
            # f"Parameters: {len(self.parameters)}\n"
            f"IClamps: {len(self.iclamps)}\n"
        )
        print(info_str)

    def params_to_dataframe(self):
        data = []
        for mech_name, params in self.mechs_to_params.items():
            for param in params:
                for group_name, distribution in self.params[param].items():
                    data.append({
                        'Mechanism': mech_name,
                        'Parameter': param,
                        'Group': group_name,
                        'Distribution': distribution
                    })
        df = pd.DataFrame(data)
        return df
    # ========================================================================
    # MORPHOLOGY
    # ========================================================================


    def from_swc(self, file_name):
        """
        Read an SWC file and build the SWC and section trees.

        Parameters
        ----------
        file_name : str
            The name of the SWC file to read.
        """
        self.name = file_name.split('.')[0]
        path_to_swc_file = self.path_manager.get_file_path('swc', file_name, extension='swc')
        swc_tree = self.tree_factory.create_swc_tree(path_to_swc_file)
        swc_tree.sort()
        swc_tree.shift_coordinates_to_soma_center()
        swc_tree.align_apical_dendrite()

        sec_tree = self.tree_factory.create_sec_tree(swc_tree)

        self.swc_tree = swc_tree
        self.sec_tree = sec_tree
        self.domains_to_mechanisms = {
            sec.domain: ['Independent'] 
            for sec in sec_tree.sections
        }

        self.create_and_reference_sections_in_simulator()
        self.set_segmentation(d_lambda=0.1)
        self.add_group('all', self.domains)



    def create_and_reference_sections_in_simulator(self):
        """
        Create and reference sections in the simulator.
        """
        print(f'Building sections in {self.simulator_name}...')
        for sec in self.sec_tree.sections:
            sec.create_and_reference(self.simulator_name)
        n_sec = len([sec._ref for sec in self.sec_tree.sections 
                    if sec._ref is not None])
        print(f'{n_sec} sections created.')

        self.seg_tree = self.tree_factory.create_seg_tree(self.sec_tree)


    def get_sections(self, filter_function):
        """Filter sections using a lambda function."""
        return [sec for sec in self.sec_tree.sections if filter_function(sec)]


    # ========================================================================
    # SEGMENTATION
    # ========================================================================


    def set_segmentation(self, d_lambda=0.1, f=100, use_neuron=False):
        """
        Set the number of segments in each section based on the geometry.

        Parameters
        ----------
        d_lambda : float
            The lambda value to use.
        f : float
            The frequency value to use.
        use_neuron : bool
            Whether to use NEURON's lambda_f function.
        """
        self._d_lambda = d_lambda
        for sec in self.sec_tree.sections:
            if use_neuron:
                from neuron import h
                lambda_f = h.lambda_f(f, sec=sec._ref)
            else:
                lambda_f = calculate_lambda_f(sec._ref.diam, sec._ref.Ra, sec._ref.cm, f)
            nseg = int((sec._ref.L / (d_lambda * lambda_f) + 0.9) / 2) * 2 + 1
            sec._ref.nseg = nseg

        self.seg_tree = self.tree_factory.create_seg_tree(self.sec_tree)


    # ========================================================================
    # MECHANISMS
    # ========================================================================

    def add_default_mechanisms(self, recompile=False):
        """
        Add default mechanisms to the model.
        """
        leak = LeakChannel()
        self.mechanisms[leak.name] = leak

        self.load_mechanisms('default_mod', recompile=False)


    def add_mechanisms(self, dir_name:str = 'mod', recompile=True) -> None:
        """
        Add a set of mechanisms from an archive to the model.

        Parameters
        ----------
        archive_name : str
            The name of the archive to add.
        """
        # Create Mechanism objects and add them to the model
        for mechanism_name in self.path_manager.list_files(dir_name, extension='mod'):
            self.add_mechanism(mechanism_name)
            self.load_mechanism(mechanism_name, dir_name, recompile)

    def add_mechanism(self, mechanism_name: str, 
                      python_template_name: str = 'default',
                      **kwargs) -> None:
        """
        Create a Mechanism object from the MOD file (or LeakChannel).

        Parameters
        ----------
        mechanism_name : str
            The name of the mechanism to add.
        archive_name : str, optional
            The name of the archive to add.
        """
        paths = self.path_manager.get_channel_paths(
            mechanism_name, 
            python_template_name=python_template_name
        )
        mech = self.mechanism_factory.create_channel(**paths)
        # Add the mechanism to the model
        self.mechanisms[mech.name] = mech
        # Update the global parameters

        
        print(f'Mechanism {mech.name} added to model.')

    def _update_equilibrium_potentials(self, ion: str) -> None:
        if ion == 'na' and not self.params.get('ena'):
            self.params['ena'] = {'all': Distribution('constant', value=50)}
        elif ion == 'k' and not self.params.get('ek'):
            self.params['ek'] = {'all': Distribution('constant', value=-77)}
        elif ion == 'ca' and not self.params.get('eca'):
            self.params['eca'] = {'all': Distribution('constant', value=140)}

    def load_mechanisms(self, dir_name: str = 'mod', recompile=True) -> None:
        """
        Load mechanisms from an archive.

        Parameters
        ----------
        dir_name : str, optional
            The name of the archive to load mechanisms from.
        recompile : bool, optional
            Whether to recompile the mechanisms.
        """
        mod_files = self.path_manager.list_files(dir_name, extension='mod')
        for mechanism_name in mod_files:
            self.load_mechanism(mechanism_name, dir_name, recompile)


    def load_mechanism(self, mechanism_name, dir_name='mod', recompile=False) -> None:
        """
        Load a mechanism from the specified archive.

        Parameters
        ----------
        mechanism_name : str
            The name of the mechanism to load.
        recompile : bool, optional
            Whether to recompile the mechanism.
        """
        path_to_mod_file = self.path_manager.get_file_path(
            dir_name, mechanism_name, extension='mod'
        )
        self.mod_loader.load_mechanism(
            path_to_mod_file=path_to_mod_file, recompile=recompile
        )
        print(f'Mechanism {mechanism_name} loaded to NEURON.\n')


    # ========================================================================
    # DOMAINS
    # ========================================================================

    def set_domain(self, domain_name, sections=None):
        """
        Create a domain from a filter function.

        Parameters
        ----------
        domain_name : str
            The name of the domain.
        filter_function : Callable
            The filter function to use.
        """
        if sections is None:
            sections = self.sec_tree.sections
        if isinstance(sections, Callable):
            sections = self.get_sections(sections)
        for sec in sections:
            sec.domain = domain_name
        self.domains_to_mechanisms[domain_name] = ['Independent']
            

    # -----------------------------------------------------------------------
    # INSERT / UNINSERT MECHANISMS
    # -----------------------------------------------------------------------


    def insert_mechanism(self, mechanism_name: str, 
                         domain_name: str):
        """
        Insert a mechanism into all sections in a domain.
        """
        mech = self.mechanisms[mechanism_name]

        self.params.update({
            param_name: {
                'all': Distribution('constant', value=value)
                }
            for param_name, value in mech.range_params_with_suffix.items()
            }
            )

        for sec in self.sec_tree.sections:
            if sec.domain == domain_name:
                sec.insert_mechanism(mech.name)
        self.domains_to_mechanisms[domain_name].append(mech.name)

        if getattr(mech, 'ion', None) is not None:
            self._update_equilibrium_potentials(mech.ion)


    def _find_nonoverlapping_nodes(self, mechanism_name, target_group):
        """
        Find the IDs of nodes in the target group where only the target group
        applies the given mechanism. Nodes shared with other groups that
        also apply the mechanism are excluded.

        Notes
        -----
        The ids are further used to uninsert the mechanism from the nodes, while
        keeping other groups that have the same mechanism inserted untouched.
        """
        nonoverlapping_nodes = set(target_group.nodes)
    
        for group in self.groups.values():
            if group is not target_group and mechanism_name in group.mechanisms:
                nonoverlapping_nodes.difference_update(group.nodes)
    
        return [node.idx for node in nonoverlapping_nodes]


    def uninsert_mechanism(self, mechanism_name: str, 
                            group_name: str):
        """
        """
        mechanism = self.mechanisms[mechanism_name]

        group = self.groups[group_name]
        group.mechanisms.remove(mechanism.name)

        # TODO: Remove params if no group uses the mechanism

        for section in group.sections:
            section.uninsert_mechanism(mechanism.name)


    # ========================================================================
    # SET PARAMETERS
    # ========================================================================

    # -----------------------------------------------------------------------
    # GROUPS
    # -----------------------------------------------------------------------


    def add_group(self, name, domains, min_dist=None, max_dist=None, min_diam=None, max_diam=None):
        """
        Add a group to the model.

        Parameters
        ----------
        group_name : str
            The name of the group.
        sections : list[Section]
            The sections to include in the group.
        """
        group = SegmentGroup(name, domains, min_dist, max_dist, min_diam, max_diam)
        self._groups.append(group)
        

    def remove_group(self, group_name):
        self._groups = [group for group in self._groups if group.name != group_name]
        for param_name in self.params:
            if self.params.get(param_name):
                self.params[param_name].pop(group_name, None)


    def move_group_down(self, name):
        idx = next(i for i, group in enumerate(self._groups) if group.name == name)
        if idx > 0:
            self._groups[idx-1], self._groups[idx] = self._groups[idx], self._groups[idx-1]
        for param_name in self.distributed_params:
            self.distribute(param_name)


    def move_group_up(self, name):
        idx = next(i for i, group in enumerate(self._groups) if group.name == name)
        if idx < len(self._groups) - 1:
            self._groups[idx+1], self._groups[idx] = self._groups[idx], self._groups[idx+1]
        for param_name in self.distributed_params:
            self.distribute(param_name)


    # -----------------------------------------------------------------------
    # DISTRIBUTIONS
    # -----------------------------------------------------------------------


    def set_param(self, param_name: str,
                        group_name: str = 'all',
                        distr_type: str = 'uniform',
                        **distr_params):

        self.set_distribution(param_name, group_name, distr_type, **distr_params)
        self.distribute(param_name)


    def set_distribution(self, param_name: str,
                         group_name: None,
                         distr_type: str = 'uniform',
                         **distr_params):
        
        distribution = Distribution(distr_type, **distr_params)
        self.params[param_name][group_name] = distribution


    def distribute(self, param_name: str):
        if param_name == 'Ra':
            self._distribute_Ra()
            return

        for group_name, distribution in self.params[param_name].items():
            group = self.groups[group_name]
            filtered_segments = [
                seg for seg in self.seg_tree.segments 
                if seg in group
            ]
            for seg in filtered_segments:
                value = distribution(seg.distance_to_root)
                seg.set_param_value(param_name, value)


    def _distribute_Ra(self):
        for group_name, distribution in self.params['Ra'].items():
            group = self.groups[group_name]
            filtered_segments = [
                seg for seg in self.seg_tree.segments
                if seg in group
            ]
            for seg in filtered_segments:
                value = distribution(seg._section(0.5).distance_to_root)
                seg._section._ref.Ra = value

    def set_section_param(self, param_name, value, domains=None):

        domains = domains or self.domains
        for sec in self.sec_tree.sections:
            if sec.domain in domains:
                setattr(sec._ref, param_name, value)

    # ========================================================================
    # STIMULI
    # ========================================================================

    # -----------------------------------------------------------------------
    # ICLAMPS
    # -----------------------------------------------------------------------

    def add_iclamp(self, sec, loc, amp=0, delay=100, dur=100):
        seg = sec(loc)
        if self.iclamps.get(seg):
            self.remove_iclamp(sec, loc)
        iclamp = IClamp(sec, loc, amp, delay, dur)
        print(f'IClamp added to sec {sec} at loc {loc}.')
        self.iclamps[seg] = iclamp


    def remove_iclamp(self, sec, loc):
        seg = sec(loc)
        if self.iclamps.get(seg):
            self.iclamps.pop(seg)


    def remove_all_iclamps(self):
        for seg in list(self.iclamps.keys()):
            sec, loc = seg._section, seg.x
            self.remove_iclamp(sec, loc)
        if self.iclamps:
            warnings.warn(f'Not all iclamps were removed: {self.iclamps}')
        self.iclamps = {}


    # -----------------------------------------------------------------------
    # SYNAPSES
    # -----------------------------------------------------------------------

    def _add_population(self, population):
        self.populations[population.syn_type][population.name] = population


    def add_population(self, segments, N, syn_type):
        idx = len(self.populations[syn_type])
        population = Population(idx, segments, N, syn_type)
        population.allocate_synapses()
        population.create_inputs()
        self._add_population(population)

    def remove_population(self, name):
        syn_type, idx = name.rsplit('_', 1)
        population = self.populations[syn_type].pop(name)
        population.clean()
        

    # ========================================================================
    # SIMULATION
    # ========================================================================


    def add_recording(self, sec, loc, var='v'):
        self.simulator.add_recording(sec, loc, var)

    def remove_recording(self, sec, loc):
        self.simulator.remove_recording(sec, loc, var)

    def remove_all_recordings(self):
        self.simulator.remove_all_recordings()

    def run(self, duration=300):
        self.simulator.run(duration)

    # MISC

    def reduce_morphology():
        ...

    def standardize_channel():
        ...


    # ========================================================================
    # FILE EXPORT
    # ========================================================================


    def to_dict(self):
        """
        Return a dictionary representation of the model.

        Returns
        -------
        dict
            The dictionary representation of the model.
        """
        return {
            'metadata': {
                'name': self.name,
                'archives': self._loaded_archives,
            },
            'simulation': {
                'd_lambda': self._d_lambda,
                **self.simulator.to_dict(),
            },
            'domains': {
                sec.idx: sec.domain for sec in self.sec_tree.sections
            },
            'groups': [
                group.to_dict() for group in self._groups
            ],
            'global_params': self.global_params,
            'distributed_params': {
                param_name: {
                    group_name: distribution.to_dict()
                    for group_name, distribution in distributions.items()
                }
                for param_name, distributions in self.distributed_params.items()
            },
            'stimuli': {
                'iclamps': [
                    {
                        'name': f'iclamp_{i}',
                        'amp': iclamp.amp,
                        'delay': iclamp.delay,
                        'dur': iclamp.dur
                    }
                    for i, (seg, iclamp) in enumerate(self.iclamps.items())
                ],
                'populations': {
                    syn_type: [pop.to_dict() for pop in pops.values()]
                    for syn_type, pops in self.populations.items()
                }
            },
        }
            
    def export_data(self):
        path_to_json = self.path_manager.get_file_path('json', self.name, extension='json')
        path_to_groups_csv = self.path_manager.get_file_path('csv', self.name + '_groups', extension='csv')
        path_to_stimuli_csv = self.path_manager.get_file_path('csv', self.name + '_stimuli', extension='csv')

        self.to_json(path_to_json, indent=4)
        self.groups_to_csv(path_to_groups_csv)
        self.stimuli_to_csv(path_to_stimuli_csv)


    def to_json(self, path_to_json, **kwargs):
        """
        Return a JSON representation of the model.

        Parameters
        ----------
        \**kwargs
            Additional keyword arguments to pass to json.dumps.

        Returns
        -------
        str
            The JSON representation of the model.
        """
        data = self.to_dict()

        with open(path_to_json, 'w') as f:
            json.dump(data, f, **kwargs)

    def stimuli_to_csv(self, path_to_csv=None):
        """
        Write the model to a CSV file.

        Parameters
        ----------
        path_to_csv : str
            The path to the CSV file to write.
        """
        
        rec_data = {
            'type': ['recording'] * len(self.recordings),
            'idx': [i for i in range(len(self.recordings))],
            'sec_idx': [seg._section.idx for seg in self.recordings],
            'loc': [seg.x for seg in self.recordings],
            'n_per_seg': [1] * len(self.recordings)
        }

        print(rec_data)

        iclamp_data = {
            'type': ['iclamp'] * len(self.iclamps),
            'idx': [i for i in range(len(self.iclamps))],
            'sec_idx': [seg._section.idx for seg in self.iclamps],
            'loc': [seg.x for seg in self.iclamps],
            'n_per_seg': [1] * len(self.iclamps)
        }
        
        synapses_data = {
            'type': [],
            'idx': [],
            'sec_idx': [],
            'loc': [],
            'n_per_seg': []
        }

        for syn_type, pops in self.populations.items():
            for pop_name, pop in pops.items():
                pop_data = pop.to_csv()
                synapses_data['type'] += pop_data['syn_type']
                synapses_data['idx'] += [int(name.rsplit('_', 1)[1]) for name in pop_data['name']]
                synapses_data['sec_idx'] += pop_data['sec_idx']
                synapses_data['loc'] += pop_data['loc']
                synapses_data['n_per_seg'] += pop_data['n_per_seg']

        df = pd.concat([
            pd.DataFrame(rec_data),
            pd.DataFrame(iclamp_data),
            pd.DataFrame(synapses_data)
        ], ignore_index=True)
        df['sec_idx'] = df['sec_idx'].astype(int)
        if path_to_csv: df.to_csv(path_to_csv, index=False)

        return df

    def groups_to_csv(self, path_to_csv=None):

        groups_data = {
            'sec_idx': [sec.idx for sec in self.sec_tree.sections]
        }

        for group_name, group in self.groups.items():
            groups_data[group_name] = [
            int(sec.idx in [s.idx for s in group.sections]) for sec in self.sec_tree.sections
            ]

        df = pd.DataFrame(groups_data)
        if path_to_csv:
            df.to_csv(path_to_csv, index=False)

        return df


    def to_swc(self, file_name):
        """
        Write the SWC tree to an SWC file.

        Parameters
        ----------
        file_name : str
            The name of the SWC file to write.
        """
        path_to_file = f'{self.path_to_data}/swc/{file_name}'.replace(
            '//', '/')
        self.swc_tree.to_swc(path_to_file)


    def to_mod(self):
        ...


    def load_data(self):
        """
        Load a model from a JSON file.

        Parameters
        ----------
        path_to_json : str
            The path to the JSON file to load.
        """

        path_to_json = self.path_manager.get_file_path('json', self.name, extension='json')
        path_to_groups_csv = self.path_manager.get_file_path('csv', self.name + '_groups', extension='csv')
        path_to_stimuli_csv = self.path_manager.get_file_path('csv', self.name + '_stimuli', extension='csv')

        with open(path_to_json, 'r') as f:
            data = json.load(f)

        df_groups = pd.read_csv(path_to_groups_csv)
        df_stimuli = pd.read_csv(path_to_stimuli_csv)

        self.name = data['metadata']['name']

        self.simulator.from_dict(data['simulation'])

        swc_file_name = data['metadata']['name']
        self.from_swc(swc_file_name)
        self.create_and_reference_sections_in_simulator()
        for sec_idx, domain in data['domains'].items():
            setattr(self.sec_tree.sections[int(sec_idx)], 'domain', domain)

        self.add_default_mechanisms()
        self.add_mechanisms('mod', recompile=True)

        for group_name in df_groups.columns[1:]:
            sections = [sec for sec in self.sec_tree.sections if df_groups[group_name][sec.idx]]
            self.add_group(group_name, sections)

        for group in data['groups']:
            for mech_name in group['mechanisms']:
                if mech_name == 'Independent':
                    continue
                self.insert_mechanism(mech_name, group['name'])
        
        self.distributed_params = {
            param_name: {
                group_name: Distribution.from_dict(distribution)
                for group_name, distribution in distributions.items()
            }
            for param_name, distributions in data['distributed_params'].items()
        }
        self.global_params = {k:v for k,v in data['global_params'].items()}

        for param_name in ['cm', 'Ra']:
            if param_name in self.distributed_params:
                self.distribute(param_name)
            else:
                self.set_global_param(param_name, self.global_params[param_name])

        self.set_segmentation(data['simulation']['d_lambda'])

        for param_name in self.distributed_params:
            self.distribute(param_name)
        for param_name, value in self.global_params.items():
            try:
                self.set_global_param(param_name, value)
            except:
                print(f'Could not set global parameter {param_name} to {value}.')

        df_recs = df_stimuli[df_stimuli['type'] == 'recording']
        for i, row in df_recs.iterrows():
            self.add_recording(
                self.sec_tree.sections[row['sec_idx']], row['loc']
            )

        df_iclamps = df_stimuli[df_stimuli['type'] == 'iclamp'].reset_index(drop=True, inplace=False)

        for i, row in df_iclamps.iterrows():
            self.add_iclamp(
            self.sec_tree.sections[row['sec_idx']], 
            row['loc'],
            data['stimuli']['iclamps'][i]['amp'],
            data['stimuli']['iclamps'][i]['delay'],
            data['stimuli']['iclamps'][i]['dur']
            )


        syn_types = ['AMPA', 'NMDA', 'AMPA_NMDA', 'GABAa']

        df_syn = df_stimuli[df_stimuli['type'] == 'AMPA']
    
        for i, pop_data in enumerate(data['stimuli']['populations']['AMPA']):
            segments = [self.sec_tree.sections[sec_idx](loc) 
                        for sec_idx, loc in zip(df_syn['sec_idx'], df_syn['loc'])]
            
            pop = Population(i, 
                             segments, 
                             pop_data['N'], 
                             'AMPA')
            n_per_seg = {seg: n for seg, n in zip(segments, df_syn['n_per_seg'])}
            pop.allocate_synapses(n_per_seg=n_per_seg)
            pop.update_kinetic_params(pop_data['kinetic_params'])
            pop.update_input_params(pop_data['input_params'])
            self._add_population(pop)

        

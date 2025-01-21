from typing import List, Union, Callable
import os
import json

from dendrotweaks.morphology.swc_trees import SWCTree
from dendrotweaks.morphology.sec_trees import Section, SectionTree, Domain
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



import pandas as pd

import warnings

def custom_warning_formatter(message, category, filename, lineno, file=None, line=None):
    return f"{category.__name__}: {message} ({os.path.basename(filename)}, line {lineno})\n"

warnings.formatwarning = custom_warning_formatter

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
        self.version = ''
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
        return self.sec_tree.domains if self.sec_tree else {}

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

    @property
    def df_params(self):
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
        sec_tree.sort()

        self.swc_tree = swc_tree
        self.sec_tree = sec_tree


        self.create_and_reference_sections_in_simulator()
        self.set_segmentation(d_lambda=0.1)


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
        self._add_default_segment_groups()


    def _add_default_segment_groups(self):
        DOMAIN_TO_GROUP = {
            'soma': 'somatic',
            'axon': 'axonal',
            'dend': 'dendritic',
            'apic': 'apical',
        }

        self.add_group('all', list(self.domains.keys()))
        for domain_name in self.domains:
            group_name = DOMAIN_TO_GROUP.get(domain_name, domain_name)
            self.add_group(group_name, [domain_name])

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
                      ) -> None:
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


    def define_domain(self, domain_name: str, sections):
        """
        Adds a new domain to the tree and ensures correct partitioning of
        the section tree graph.

        Parameters
        ----------
        domain_name : str
            The name of the domain.
        sections : list[Section] or Callable
            The sections to include in the domain. If a callable is provided,
            it should be a filter function applied to the list of all sections
            of the cell.
        """
        if isinstance(sections, Callable):
            sections = self.get_sections(sections)
            
        if domain_name not in self.domains:
            self._create_domain(domain_name, sections)
        else:
            self._extend_domain(domain_name, sections)

        self.remove_empty()
        

    def _create_domain(self, domain_name, sections):
        """
        Creates a new domain with the given sections.
        """
        print(f'Creating domain {domain_name}...')
        # 1 Create a new domain
        domain = Domain(domain_name)
        # 2 Remove sections from existing domains
        self.remove_selected_sections_from_existing_domains(sections)
        # 3 Add sections to new domain
        for sec in sections:
            domain.add_section(sec)
        # 4 Add domain groups
        self._add_domain_groups(domain.name)
        # 5 Add domain to the domain dictionary
        self.domains[domain_name] = domain


    def _extend_domain(self, domain_name, sections):
        """
        Extends an existing domain with new sections.
        """
        print(f'Extending domain {domain_name}...')
        # 1 Get the domain
        domain = self.domains.get(domain_name)
        # 2 Remove sections from existing domains, 
        # but only if they are not already in the target domain
        sections_not_in_domain = [sec for sec in sections if sec.domain != domain_name]
        if not sections_not_in_domain:
            warnings.warn(f'All sections are already in domain {domain_name}.')
            return
        self.remove_selected_sections_from_existing_domains(sections_not_in_domain)
        # 3 Add sections to domain
        for sec in sections_not_in_domain:
            domain.add_section(sec)


    def remove_selected_sections_from_existing_domains(self, sections):
        """
        """
        for domain in list(self.domains.values()):
           
            overlapping_sections = [sec for sec in sections 
                                    if sec in domain]

            for sec in overlapping_sections:
                domain.remove_section(sec)


    def remove_empty(self):
        self._remove_empty_domains()
        self._remove_uninserted_mechanisms()
        self._remove_empty_groups()


    def _remove_empty_domains(self):
        """
        """
        empty_domains = [domain for domain in self.domains.values() 
            if domain.is_empty()]
        for domain in empty_domains:
            for mech in domain.inserted_mechanisms.values():
                mech.domains.pop(domain.name)
            warnings.warn(f'Domain {domain.name} is empty and will be removed.')
            self.domains.pop(domain.name)
            self.groups['all'].domains.remove(domain.name)


    def _remove_uninserted_mechanisms(self):
        mech_names = list(self.mechs_to_params.keys())
        mechs = [self.mechanisms[mech_name] for mech_name in mech_names
             if mech_name != 'Independent']
        uninserted_mechs = [mech for mech in mechs
                            if not mech.is_inserted()]
        for mech in uninserted_mechs:
            for domain in mech.domains.values():
                domain.inserted_mechanisms.pop(mech.name)
            warnings.warn(f'Mechanism {mech.name} is not inserted in any domain and will be removed.')
            self._remove_mechanism_params(mech)


    def _remove_empty_groups(self):
        empty_groups = [group for group in self._groups 
                        if not any(sec in group 
                        for sec in self.sec_tree.sections)]
        for group in empty_groups:
            warnings.warn(f'Group {group.name} is empty and will be removed.')
            self.remove_group(group.name)


    def _add_domain_groups(self, domain_name):
        """
        Manage groups when a domain is added.
        """
        # Add new domain to `all` group
        if self.groups.get('all'):
            self.groups['all'].domains.append(domain_name)
        # Create a new group for the domain
        self.add_group(domain_name, [domain_name])


    # -----------------------------------------------------------------------
    # INSERT / UNINSERT MECHANISMS
    # -----------------------------------------------------------------------


    def insert_mechanism(self, mechanism_name: str, 
                         domain_name: str):
        """
        Insert a mechanism into all sections in a domain.
        """
        mech = self.mechanisms[mechanism_name]
        domain = self.domains[domain_name]

        domain.insert_mechanism(mech)
        self._add_mechanism_params(mech)

        # TODO: Redistribute parameters if any group contains this domain
        for param_name in self.params:
            self.distribute(param_name)
        

    def _add_mechanism_params(self, mech):
        """
        Update the parameters when a mechanism is inserted.
        By default each parameter is set to a constant value
        through the entire cell.
        """
        for param_name, value in mech.range_params_with_suffix.items():
            self.params[param_name] = {'all': Distribution('constant', value=value)}
        
        if hasattr(mech, 'ion') and mech.ion in ['na', 'k', 'ca']:
            self._add_equilibrium_potentials_on_mech_insert(mech.ion)


    def _add_equilibrium_potentials_on_mech_insert(self, ion: str) -> None:
        """
        """
        if ion == 'na' and not self.params.get('ena'):
            self.params['ena'] = {'all': Distribution('constant', value=50)}
        elif ion == 'k' and not self.params.get('ek'):
            self.params['ek'] = {'all': Distribution('constant', value=-77)}
        elif ion == 'ca' and not self.params.get('eca'):
            self.params['eca'] = {'all': Distribution('constant', value=140)}


    def uninsert_mechanism(self, mechanism_name: str, 
                            domain_name: str):
        """
        Uninsert a mechanism from all sections in a domain
        """
        mech = self.mechanisms[mechanism_name]
        domain = self.domains[domain_name]

        domain.uninsert_mechanism(mech)

        if not mech.is_inserted():
            self._remove_mechanism_params(mech)

    
    def _remove_mechanism_params(self, mech):
        for param_name in self.mechs_to_params.get(mech.name, []):
            self.params.pop(param_name)

        if hasattr(mech, 'ion') and mech.ion in ['na', 'k', 'ca']:
            self._remove_equilibrium_potentials_on_mech_uninsert(mech.ion)


    def _remove_equilibrium_potentials_on_mech_uninsert(self, ion: str) -> None:
        """
        """
        for mech_name, mech in self.mechanisms.items():
            if hasattr(mech, 'ion'):
                if mech.ion == mech.ion: return

        if ion == 'na':
            self.params.pop('ena', None)
        elif ion == 'k':
            self.params.pop('ek', None)
        elif ion == 'ca':
            self.params.pop('eca', None)

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
        # Remove group from the list of groups
        self._groups = [group for group in self._groups 
                        if group.name != group_name]
        # Remove distributions that refer to this group
        for param_name, groups_to_distrs in self.params.items():
            groups_to_distrs.pop(group_name, None)


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
                        distr_type: str = 'constant',
                        **distr_params):

        if param_name in ['temperature', 'v_init']:
            setattr(self.simulator, param_name, distr_params['value'])
            return

        self.set_distribution(param_name, group_name, distr_type, **distr_params)
        self.distribute(param_name)


    def set_distribution(self, param_name: str,
                         group_name: None,
                         distr_type: str = 'constant',
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

    def remove_distribution(self, param_name, group_name):
        self.params[param_name].pop(group_name, None)
        self.distribute(param_name)

    # def set_section_param(self, param_name, value, domains=None):

    #     domains = domains or self.domains
    #     for sec in self.sec_tree.sections:
    #         if sec.domain in domains:
    #             setattr(sec._ref, param_name, value)

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

    # ========================================================================
    # MORPHOLOGY
    # ========================================================================

    def remove_subtree(self, sec):
        self.sec_tree.remove_subtree(sec)
        self.sec_tree.sort()
        self.remove_empty()

    def merge_domains(self, domain_names: List[str]):
        """
        Merge two domains into one.
        """
        domains = [self.domains[domain_name] for domain_name in domain_names]
        for domain in domains[1:]:
            domains[0].merge(domain)
        self.remove_empty()


    def reduce_subtree(self, root):
        # Cannot remove domains
        # Can remove groups

        domain = self.get_domain(sec)
        parent = sec.parent
        domains_in_subtree = [self.domains[domain_name] 
            for domain_name in set([sec.domain for sec in root.subtree])]

        subtree_without_root = [sec for sec in root.subtree if sec is not root]

        # Map original segment names to their parameters
        ...

        # Temporarily remove active mechanisms
        for mech_name in self.mechanisms:
            for sec in root.subtree:
                sec.uninsert_mechanism(mech_name)

        # Disconnect
        root.disconnect_from_parent()

         # Calculate new properties of a reduced subtree
        ...

         # Map segment names to their new locations in the reduced cylinder
        ...

        # Set passive mechanisms for the reduced cylinder:
        ...

        # Reconnect
        root.connect_to_parent(parent)

        # Reinsert active mechanisms
        

        # Delete the original subtree
        children = sec.children[:]
        for child_sec in children:
            self.remove_subtree(child_sec)

        # Remove intermediate pts3d


        

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
            },
            'simulation': {
                'd_lambda': self._d_lambda,
                **self.simulator.to_dict(),
            },
            'domains': {
                domain_name: domain.to_dict()
                for domain_name, domain in self.domains.items()
            },
            'groups': [
                group.to_dict() for group in self._groups
            ],
            'params': {
                param_name: {
                    group_name: distribution.to_dict()
                    for group_name, distribution in distributions.items()
                }
                for param_name, distributions in self.params.items()
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
        name = self.name + '_' + self.version.replace(' ', ' ') if self.version else self.name
        path_to_json = self.path_manager.get_file_path('json', name, extension='json')
        # path_to_groups_csv = self.path_manager.get_file_path('csv', self.name + '_groups', extension='csv')
        path_to_stimuli_csv = self.path_manager.get_file_path('csv', name + '_stimuli', extension='csv')

        self.to_json(path_to_json, indent=4)
        # self.groups_to_csv(path_to_groups_csv)
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

    # def groups_to_csv(self, path_to_csv=None):

    #     groups_data = {
    #         'sec_idx': [sec.idx for sec in self.sec_tree.sections]
    #     }

    #     for group_name, group in self.groups.items():
    #         groups_data[group_name] = [
    #         int(sec.idx in [s.idx for s in group.sections]) for sec in self.sec_tree.sections
    #         ]

    #     df = pd.DataFrame(groups_data)
    #     if path_to_csv:
    #         df.to_csv(path_to_csv, index=False)

    #     return df


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


    def load_data(self, recompile=True):
        """
        Load a model from a JSON file.

        Parameters
        ----------
        path_to_json : str
            The path to the JSON file to load.
        """

        path_to_json = self.path_manager.get_file_path('json', self.name, extension='json')
        # path_to_groups_csv = self.path_manager.get_file_path('csv', self.name + '_groups', extension='csv')
        path_to_stimuli_csv = self.path_manager.get_file_path('csv', self.name + '_stimuli', extension='csv')

        with open(path_to_json, 'r') as f:
            data = json.load(f)

        # df_groups = pd.read_csv(path_to_groups_csv)
        df_stimuli = pd.read_csv(path_to_stimuli_csv)

        self.name = data['metadata']['name']

        self.simulator.from_dict(data['simulation'])

        swc_file_name = data['metadata']['name']
        self.from_swc(swc_file_name)
        self.create_and_reference_sections_in_simulator()
        
        print(f'DOMAINS: {self.domains}')
        self.add_default_mechanisms()
        self.add_group('all', list(self.domains.keys()))
        self.add_mechanisms('mod', recompile=recompile)
        print(f'GROUPS: {self.groups}')

        self.sec_tree.domains = {}
        for domain_name, domain_data in data['domains'].items():
            sections = [self.sec_tree.sections[sec_idx] for sec_idx in domain_data['sections']]
            domain = Domain(domain_name)
            for sec in sections:
                domain.add_section(sec)
            self.domains[domain_name] = domain
            for mech_name in domain_data['mechanisms']:
                if mech_name == "Independent":
                    continue
                self.insert_mechanism(mech_name, domain_name)
        self.remove_empty()

        for group_params in data['groups']:
            self.add_group(**group_params)
        
        self.params = {
            param_name: {
                group_name: Distribution.from_dict(distribution)
                for group_name, distribution in distributions.items()
            }
            for param_name, distributions in data['params'].items()
        }

        for param_name in ['cm', 'Ra']:
            self.distribute(param_name)

        self.set_segmentation(data['simulation']['d_lambda'])

        for param_name in self.params:
            self.distribute(param_name)

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

        

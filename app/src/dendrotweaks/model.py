from typing import List, Union, Callable
import os
import warnings

from dendrotweaks.morphology.swc_trees import SWCTree
from dendrotweaks.morphology.sec_trees import Section, SectionTree
from dendrotweaks.morphology.seg_trees import Segment, SegmentTree
from dendrotweaks.simulators import NEURONSimulator
# from dendrotweaks.membrane.groups import SectionGroup
from dendrotweaks.membrane.mechanisms import Mechanism, LeakChannel
from dendrotweaks.membrane.io import MechanismFactory
from dendrotweaks.membrane.io import MODFileLoader
from dendrotweaks.morphology.io import TreeFactory
from dendrotweaks.stimuli.iclamps import IClamp
from dendrotweaks.membrane.distributions import Distribution
from dendrotweaks.utils import calculate_lambda_f, dynamic_import

from collections import OrderedDict, defaultdict

# from .logger import logger

from dendrotweaks.path_manager import PathManager

from dataclasses import dataclass

INDEPENDENT_PARAMS = {
    'cm': 1, # uF/cm2
    'Ra': 100, # Ohm cm
    'ena': 50, # mV
    'ek': -77, # mV
    'eca': 140 # mV
}

class SectionGroup:

    def __init__(self, name, sections):
        self.name = name
        self._sections = sections
        self.mechanisms = ['Independent']

    @property
    def sections(self):
        return self._sections

    @sections.setter
    def sections(self, sections):
        raise AttributeError('Sections cannot be set directly.')

    


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
        self.name = name
        self.path_manager = PathManager(path_to_data)
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
        self.global_params = {
            'cm': 1, # uF/cm2
            'Ra': 100, # Ohm cm
            'ena': 50, # mV
            'ek': -77, # mV
            'eca': 140 # mV
        }

        # Groups
        self._groups = []

        # Distributions
        self.distributed_params = {}

        # Segmentation
        self._d_lambda = None
        self.seg_tree = None

        # Stimuli
        self.iclamps = {}
        self.populations = {}

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

    def make_distributed(self, param_name):
        value = self.global_params.get(param_name)
        mech_name = self.params_to_mechs[param_name]
        
        self.distributed_params[param_name] = {
            group.name: Distribution('uniform', value=value) for group in self._groups
            if mech_name in group.mechanisms
            }
        self.global_params.pop(param_name)

    # def make_global(self, param_name, mech_name='Independent'):
    #     groups = self.parameters[mech_name][param_name]
    #     values = [value for value in groups.values()]
    #     if len(set(values)) == 1:
    #         self.parameters[mech_name][param_name] = values[0]
    #     else:
    #         raise ValueError(f'Parameter {param_name} has different values in different groups.')
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


    @property
    def params(self):
        # combine global and distributed parameters
        return {**self.distributed_params, **self.global_params}

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
            f"Mechanisms: {len(self.mechanisms)}\n"
            # f"Parameters: {len(self.parameters)}\n"
            f"IClamps: {len(self.iclamps)}\n"
        )
        print(info_str)

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
    # MECHANISMS
    # ========================================================================

    # TODO: This should be done when user selects an archive. 
    # Then to each group, the mechanisms should be added from 
    # the model.mechanisms dictionary.I.e. the mechanism class is
    # instantiated only once and then only its parameters
    # are added to the groups. 
    # 1. Add mechanisms to the model.mechanisms dictionary
    # 2. From the model.mechanisms dictionary, add mechanisms to the groups
        # - their names will be inserted into the sections in the group
        # - their parameters will be distributed in the group sections
    # Base archive is added by default (Leak and Synapses)

    # -----------------------------------------------------------------------
    # ADDING MECHANISMS TO THE MODEL
    # -----------------------------------------------------------------------

    def add_archive(self, archive_name: str, recompile=True) -> None:
        """
        Add a set of mechanisms from an archive to the model.

        Parameters
        ----------
        archive_name : str
            The name of the archive to add.
        """
        # Create Mechanism objects and add them to the model
        for mechanism_name in self.path_manager.list_archives()[archive_name]:
            self.add_mechanism(mechanism_name, archive_name)
            self.load_mechanism(mechanism_name, archive_name, recompile)

    def add_mechanism(self, mechanism_name: str, 
                      archive_name: str = '', 
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
        if mechanism_name == 'Leak':
            path_to_mod_file = self.path_manager.get_file_path(
                'mod', 'Leak', 
                extension='mod', 
                archive=archive_name
            )
            mech = self.mechanism_factory.create_leak_channel(path_to_mod_file)
        else:
            paths = self.path_manager.get_channel_paths(
                mechanism_name, 
                archive_name,
                python_template_name=python_template_name
            )
            mech = self.mechanism_factory.create_channel(**paths)
        # Add the mechanism to the model
        self.mechanisms[mech.name] = mech
        
        print(f'Mechanism {mech.name} added to model.')

    def load_archive(self, archive_name: str = '', recompile=True) -> None:
        """
        Load mechanisms from an archive.

        Parameters
        ----------
        archive_name : str, optional
            The name of the archive to load mechanisms from.
        recompile : bool, optional
            Whether to recompile the mechanisms.
        """
        archive = self.path_manager.list_archives().get(archive_name, [])
        for mechanism_name in archive:
            self.load_mechanism(mechanism_name, archive_name, recompile)

    def load_mechanism(self, mechanism_name: str, archive_name: str = '', recompile=False) -> None:
        """
        Load a mechanism from the specified archive.

        Parameters
        ----------
        mechanism_name : str
            The name of the mechanism to load.
        archive_name : str, optional
            The name of the archive to load the mechanism from.
        recompile : bool, optional
            Whether to recompile the mechanism.
        """
        path_to_mod_file = self.path_manager.get_file_path(
            'mod', mechanism_name, extension='mod', archive=archive_name
        )
        self.mod_loader.load_mechanism(
            path_to_mod_file=path_to_mod_file, recompile=recompile
        )
        print(f'Mechanism {mechanism_name} loaded to NEURON.\n')



    # ========================================================================
    # GROUPS
    # ========================================================================

    def add_group(self, group_name, sections: Union[Callable, List[Section]] = None):
        """
        Add a group to the model.

        Parameters
        ----------
        group_name : str
            The name of the group.
        sections : list[Section]
            The sections to include in the group.
        """
        if group_name in self.groups:
            raise ValueError(f'Group {group_name} already exists')
        if sections is None:
            sections = self.sec_tree.sections
        if isinstance(sections, Callable):
            sections = self.get_sections(sections)
        group = SectionGroup(group_name, sections)
        self._groups.append(group)
        # Add the group to the parameters dictionary
        for param_name in self.distributed_params:
            self.distributed_params[param_name][group_name] = Distribution('uniform', value=0)
        

    # def update_distributions_on_adding_group(self, group_name):
    #     for param, value in INDEPENDENT_PARAMS.items():
    #         self.parameters[param][group_name] = value
    #     for mechanism in self.mechanisms.values():
    #         for param, value in mechanism.params.items():
    #             self.parameters[param][group_name] = value

    # def update_distributions_on_adding_mechanism(self, mechanism_name):
    #     for group in self.groups:
    #         for param, value in self.mechanisms[mechanism_name].params_with_suffix.items():
    #             self.parameters[param][group.name] = value

    def remove_group(self, group_name):
        self._groups = [group for group in self._groups if group.name != group_name]
        for param_name in self.distributed_params:
            self.distributed_params[param_name].pop(group_name)

    def move_group_down(self, name):
        idx = next(i for i, group in enumerate(self._groups) if group.name == name)
        if idx > 0:
            self._groups[idx-1], self._groups[idx] = self._groups[idx], self._groups[idx-1]

    def move_group_up(self, name):
        idx = next(i for i, group in enumerate(self._groups) if group.name == name)
        if idx < len(self._groups) - 1:
            self._groups[idx+1], self._groups[idx] = self._groups[idx], self._groups[idx+1]


    # -----------------------------------------------------------------------
    # ADDING MECHANISMS TO GROUPS / REMOVING MECHANISMS FROM GROUPS
    # -----------------------------------------------------------------------

    def insert_mechanism(self, mechanism_name: str, 
                         group_name: str):
        """
        """
        mechanism = self.mechanisms[mechanism_name]

        if all(mechanism.name not in group.mechanisms for group in self._groups):
            self.global_params.update(mechanism.params_with_suffix)

        group = self.groups[group_name]
        group.mechanisms.append(mechanism.name)

        for section in group.sections:
            section.insert_mechanism(mechanism.name)

        # self.parameters.setdefault(mechanism.name, {})
        
        # for param_name, value in mechanism.params.items():
        #     self.parameters[mechanism.name].setdefault(param_name, {})
        #     self.parameters[mechanism.name][param_name][group_name] = value


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

        for section in group.sections:
            section.uninsert_mechanism(mechanism.name)

    # -----------------------------------------------------------------------
    # ADDING PARAMETERS TO GROUPS / REMOVING PARAMETERS FROM GROUPS
    # -----------------------------------------------------------------------

    def set_distributed_param(self, param_name: str,
                              group_name: str,
                              distr_type: str = 'uniform',
                                **distr_params):

        self.set_distribution(param_name, group_name, distr_type, **distr_params)
        self.distribute(param_name)

    def set_distribution(self, param_name: str,
                         group_name: None,
                         distr_type: str = 'uniform',
                         **distr_params):
        if param_name not in self.distributed_params:
            raise ValueError(f'Parameter {param_name} is not a distributed parameter.')
        distribution = Distribution(distr_type, **distr_params)
        self.distributed_params[param_name][group_name] = distribution

    def distribute(self, param_name: str):
        # TODO: Eiter store distributed params within groups or
        # introduce somehow the order of groups in distributed_params[param_name]
        for group_name, distribution in self.distributed_params[param_name].items():
            group = self.groups[group_name]

            for section in group.sections:   
                # if isinstance(distribution, (int, float)):
                #     value = distribution
                #     const_distr = lambda x: value
                #     section.set_param_value(parameter_with_suffix, const_distr)
                if isinstance(distribution, Distribution):
                    section.set_param_value(param_name, distribution)
                else:
                    raise ValueError('Distribution has to be a Distribution object.')

    # def add_range_param(self, param_name: str, 
    #                     mechanism_name: str = "Independent", 
    #                     group_names: List[str] = None) -> None:
    #     """
    #     Add parameters to the sections in the specified groups.

    #     Parameters
    #     ----------
    #     param_name : str
    #         The name of the parameter to add.
    #     groups : List[str], optional
    #         The names of the groups to add the parameter to. If None, parameters will be added to all groups.
    #     """
    #     groups = [self.groups[name] for name in group_names]
    #     if not groups:
    #         groups = list(self.groups.values())
        
    #     for group in groups:
    #         group.add_parameter(param_name)

    #     if mechanism_name not in self._distributed_parameters:
    #         self._distributed_parameters[mechanism_name] = []
    #     if param_name not in self._distributed_parameters[mechanism_name]:
    #         self._distributed_parameters[mechanism_name].append(param_name)

    # def remove_range_param(self, param_name: str, 
    #                        mechanism_name: str = "Independent",
    #                        group_names: List[str] = None) -> None:
    #     """
    #     Remove parameters from the sections in the specified groups.

    #     Parameters
    #     ----------
    #     param_name : str
    #         The name of the parameter to remove.
    #     groups : List[str], optional
    #         The names of the groups to remove the parameter from. If None, parameters will be removed from
    #         all groups.
    #     """
    #     groups = [self.groups[name] for name in group_names]
    #     if not groups:
    #         groups = list(self.groups.values())
        
    #     for group in groups:
    #         group.remove_parameter(param_name)

    #     if param_name in self._distributed_parameters[mechanism_name]:
    #         self._distributed_parameters[mechanism_name].remove(param_name)
    #     if not self._distributed_parameters[mechanism_name]:
    #         self._distributed_parameters.pop(mechanism_name)

    def set_global_param(self, param_name: str, value: float) -> None:
        """
        Set a global parameter to a value.

        Parameters
        ----------
        param_name : str
            The name of the parameter to set.
        value : float
            The value to set the parameter to.
        """
        if param_name in self.distributed_params:
            raise ValueError(f'Parameter {param_name} is a distributed parameter.')

        if param_name in ['celsius', 'v_init']:
            setattr(self.simulator, param_name, value)
            return

        for sec in self.sec_tree.sections:
            sec.set_param_value(param_name, lambda x: value)
            self.global_params[param_name] = value


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
    # STIMULI
    # ========================================================================

    # ICAMPS

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
        for seg in self.iclamps.keys():
            sec, loc = seg._section, seg.x
            self.remove_iclamp(sec, loc)
        if self.iclamps:
            warnings.warn(f'Not all iclamps were removed: {self.iclamps}')
        self.iclamps = {}

    # SYNAPSES

    def _add_population(self, population):
        self.populations[population.name] = population

    def add_population(self, name, synapse_type, size, sections):
        population = Population(name, synapse_type, size, sections)
        self._add_population(population)

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
                },
                'simulation': {
                    'd_lambda': self._d_lambda,
                    **self.simulator.to_dict(),
                },
                'groups': {
                    group.name : [sec.idx for sec in group.sections]
                    for group in self._groups
                },
                'parameters': {
                    mechanism_name: {
                        param_name: {
                            group_name: distribution.to_dict() if isinstance(distribution, Distribution) else distribution
                            for group_name, distribution in group.items()
                        }
                        for param_name, group in mechanism.items()
                    }
                    for mechanism_name, mechanism in self.parameters.items()
                }
                    
                # 'stimuli': {
                #     {}
            }

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
        import json
        data = self.to_dict()
        if path_to_json:
            with open(path_to_json, 'w') as f:
                json.dump(data, f, **kwargs)
        return json.dumps(data, **kwargs)

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

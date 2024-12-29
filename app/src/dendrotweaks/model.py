from typing import List, Union, Callable
import os

from dendrotweaks.morphology.swc_trees import SWCTree
from dendrotweaks.morphology.sec_trees import Section, SectionTree
from dendrotweaks.morphology.seg_trees import Segment, SegmentTree
from dendrotweaks.simulators import NEURONSimulator
from dendrotweaks.membrane.groups import SectionGroup
from dendrotweaks.membrane.mechanisms import Mechanism, LeakChannel
from dendrotweaks.membrane.io import MechanismFactory
from dendrotweaks.membrane.io import MODFileLoader
from dendrotweaks.morphology.io import TreeFactory
from dendrotweaks.stimuli.iclamps import IClamp
from dendrotweaks.utils import calculate_lambda_f, dynamic_import

from collections import OrderedDict, defaultdict

# from .logger import logger

from dendrotweaks.path_manager import PathManager

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

        # Groups
        self.groups = OrderedDict()

        # Segmentation
        self._d_lambda = None
        self.seg_tree = None

        # Stimuli
        self._iclamps = defaultdict(dict)
        self.synapses = {}

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
    def groups_to_parameters(self):
        groups_to_parameters = defaultdict(list)
        for group in self.groups.values():
            for parameter in group.parameters:
                groups_to_parameters[group.name].append(parameter)
        return dict(groups_to_parameters)

    @property
    def parameters_to_groups(self):
        paramters_to_groups = defaultdict(list)
        for group in self.groups.values():
            for parameter_name in group.parameters:
                paramters_to_groups[parameter_name].append(group.name)
        return dict(paramters_to_groups)

    @property
    def iclamps(self):
        return [iclamp for sec in self._iclamps.values() for iclamp in sec.values()]

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
            f"Parameters: {len(self.parameters_to_groups)}\n"
            f"IClamps: {len(self.iclamps)}\n"
            f"Synapses: {len(self.synapses)}"
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

    def add_archive(self, archive_name: str, **kwargs) -> None:
        """
        Add a set of mechanisms from an archive to the model.

        Parameters
        ----------
        archive_name : str
            The name of the archive to add.
        **kwargs
            Additional keyword arguments to pass to the Mechanism constructor.
        """
        # Create Mechanism objects and add them to the model
        for mechanism_name in self.path_manager.list_archives()[archive_name]:
            mechanism = self.add_mechanism(mechanism_name, archive_name, **kwargs)

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
        **kwargs
            Additional keyword arguments to pass to the Mechanism constructor.
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

    def load_mechanism(self, mechanism_name: str, archive_name: str = '', recompile=True) -> None:
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
        self.groups[group.name] = group

    def remove_group(self, group_name):
        self.groups.pop(group_name)

    # -----------------------------------------------------------------------
    # ADDING MECHANISMS TO GROUPS / REMOVING MECHANISMS FROM GROUPS
    # -----------------------------------------------------------------------

    def insert_mechanism(self, mechanism_name: str, 
                         group_names: List[str] = None):
        """
        Add a mechanism to the groups specified in groups_names where
        - they will be inserted into the sections
        - they will be used to distribute parameters 
        specified in mechanism.parameters list.
        """
        if not group_names:
            group_names = list(self.groups.keys())
        groups = [self.groups[name] for name in group_names]
        
        mechanism = self.mechanisms[mechanism_name]

        for group in groups:
                group.insert_mechanism(mechanism)

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
                            group_names: List[str] = None):
        """
        """
        if not group_names:
            group_names = list(self.groups.keys())
        groups = [self.groups[name] for name in group_names]

        for group in groups:
            node_ids = self._find_nonoverlapping_nodes(group, mechanism_name)
            group.uninsert_mechanism(mechanism_name, node_ids)

    # -----------------------------------------------------------------------
    # ADDING PARAMETERS TO GROUPS / REMOVING PARAMETERS FROM GROUPS
    # -----------------------------------------------------------------------

    def add_range_param(self, param_name: str, group_names: List[str] = None) -> None:
        """
        Add parameters to the sections in the specified groups.

        Parameters
        ----------
        param_name : str
            The name of the parameter to add.
        groups : List[str], optional
            The names of the groups to add the parameter to. If None, parameters will be added to all groups.
        """
        groups = [self.groups[name] for name in group_names]
        if not groups:
            groups = list(self.groups.values())
        
        for group in groups:
            group.add_parameter(param_name)

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
        if param_name in self.parameters_to_groups:
            raise ValueError(f'Parameter {param_name} is a distributed parameter.')

        if param_name in ['celsius', 'v_init']:
            setattr(self.simulator, param_name, value)
            return

        for seg in self.seg_tree.segments:
            if not hasattr(seg._ref, param_name):
                raise AttributeError(f'{param_name} not found in segment.')
            setattr(seg._ref, param_name, value)


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

    # def load_synaptic_mechanisms(self):
    #     self.modm.load_mod_file('app/model/mechanisms/mod/Synapses/', 
    #                             recompile=not os.path.exists('app/model/mechanisms/mod/Synapses/x86_64/'))

    def _add_iclamp(self, iclamp):
        self._iclamps[iclamp.sec][iclamp.loc] = iclamp

    def add_iclamp(self, sec, loc, amp=0, delay=100, dur=100):
        if self._iclamps.get(sec):
            if self._iclamps[sec].get(loc):
                self.remove_iclamp(sec, loc)
        iclamp = IClamp(sec, loc, amp, delay, dur)
        print(f'IClamp added to sec {sec} at loc {loc}.')
        self._add_iclamp(iclamp)

    def remove_iclamp(self, sec, loc):
        if self._iclamps.get(sec):
            if self._iclamps[sec].get(loc):
                self._iclamps[sec].pop(loc)
            if not self._iclamps[sec]:
                self._iclamps.pop(sec)

    def remove_all_iclamps(self):
        for sec in list(self._iclamps.keys()):
            for loc in list(self._iclamps[sec].keys()):
                self.remove_iclamp(sec, loc)

    def _add_population(self, population):
        self.populations[population.name] = population

    def add_population(self, name, synapse_type, size, sections):
        population = Population(name, synapse_type, size, sections)
        self._add_population(population)

    # ========================================================================
    # SIMULATION
    # ========================================================================

    def add_recording(self, sec, loc=0.5):
        self.simulator.add_recording(sec, loc)

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
                    'simulator_name': self.modm._simulator_name,
                    'group_by': self._group_by,
                    'path_to_data': self.path_to_data,
                    'swc_data': self.swcm.to_dict(),
                    'mod_data': self.modm.to_dict(),
                },
                'simulation': {
                    'd_lambda': self._d_lambda,
                    **self.simulator.to_dict(),
                },
                'groups': {
                    group_name : group.to_dict()
                    for group_name, group in self.groups.items()
                },
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

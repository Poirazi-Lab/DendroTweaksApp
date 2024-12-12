from typing import List

from dendrotweaks.morphology.swc_trees import SWCTree
from dendrotweaks.morphology.seg_trees import Segment, SegmentTree
from dendrotweaks.simulators import NEURONSimulator
from dendrotweaks.membrane.groups import SectionGroup
from dendrotweaks.membrane.mechanisms import Mechanism, LeakChannel
from dendrotweaks.file_managers import SWCManager, MODManager
from dendrotweaks.stimuli.iclamps import IClamp
from dendrotweaks.utils import calculate_lambda_f, dynamic_import

from collections import OrderedDict, defaultdict

# from .logger import logger

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

    Attributes
    ----------
    name : str
        The name of the model.
    simulator_name : str
        The name of the simulator to use (either 'NEURON' or 'Jaxley').
    path_to_data : str
        The path to the data files where swc and mod files are stored.
    group_by : str
        The grouping method to use (either 'segments' or 'sections').
    swc_tree : SWCTree
        The SWC tree of the model.
    sec_tree : SWCTree
        The section tree of the model.
    seg_tree : SegmentTree
        The segment tree of the model.
    mechanisms : dict
        The mechanisms of the model.
    parameters : dict
        The parameters of the model.
    groups : dict
        The groups of the model.
    iclamps : dict
        The current clamps of the model.
    synapses : dict
        The synapses of the model.
    simulator : Simulator
        The simulator to use.
    """

    def __init__(self, name: str,
                 simulator_name='NEURON',
                 path_to_data='data',
                 group_by='sections') -> None:

        # Metadata
        self.name = name
        self.path_to_data = path_to_data
        self.simulator_name = simulator_name
        self._group_by = group_by

        # File managers
        self.swcm = SWCManager(path_to_data)
        self.modm = MODManager(simulator_name, path_to_data)

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
        self.iclamps = {}
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
    # PARAMETERS
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

    # -----------------------------------------------------------------------
    # METADATA
    # -----------------------------------------------------------------------

    @property
    def group_by(self):
        return self._group_by

    @group_by.setter
    def group_by(self, value):
        if value not in ['segments', 'sections']:
            raise ValueError(
                'group_by must be either "segments" or "sections"')
        if len(self.groups) > 0:
            raise ValueError(
                'Cannot change group_by after groups have been added')
        self._group_by = value

    def info(self):
        """
        Print information about the model.
        """
        info_str = (
            f"Model: {self.name}\n"
            f"Path to data: {self.path_to_data}\n"
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
        self.swcm.read(file_name)

        self.build_swc_tree()
        self.build_sec_tree()

    def build_swc_tree(self):
        self.swcm.build_swc_tree()
        self.swcm.postprocess_swc_tree(sort=True, 
                                       split=True, 
                                       shift=True, 
                                       extend=True)
        self.swc_tree = self.swcm.swc_tree

    def build_sec_tree(self):
        self.swcm.build_sec_tree()
        self.sec_tree = self.swcm.sec_tree

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

    def add_archive(self, archive_name: str, recompile=False):
        """
        Add a mechanism archive to the model.
        - Loads the mechanisms from the archive.
        - Creates Mechanism objects from the MOD files (or LeakChannel).
        - Adds the mechanisms to the model.mechnisms dictionary.
        - Adds the mechanisms to the groups specified in groups_names where
            - they will be inserted into the sections
            - they will be used to distribute parameters 
            specified in mechanism.parameters list.
        """
        if self.modm._path_to_data != self.path_to_data:
            self.modm._path_to_data = self.path_to_data

        # Load the archive of mod files
        self.modm.load_archive(archive_name, recompile=recompile)

        # Create Mechanism objects and add them to the model
        for mechanism_name in self.modm.list_archives()[archive_name]:
            mechanism = self._create_mechanism(mechanism_name, archive_name)
            self._add_mechanism_to_model(mechanism)

    def _create_mechanism(self, mechanism_name: str, archive_name=''):
        """
        Create a Mechanism object from the MOD file (or LeakChannel).
        """
        if mechanism_name == 'Leak':
            mech = LeakChannel()
        else:
            mech = self.from_mod(mechanism_name, archive_name)
        return mech

    def from_mod(self, mechanism_name, archive_name=''):
        """
        Read a MOD file, parse it to an AST, and write it to a Python file.

        Parameters
        ----------
        file_name : str
            The name of the MOD file to read. Also used to name the Python file.
        """
        path_to_mod_file = f'{self.path_to_data}/mod/{archive_name}/{mechanism_name}.mod'.replace(
            '//', '/')
        self.modm.read(path_to_mod_file)
        self.modm.parse()
        self.modm.ast_to_python()
        path_to_py_file = f'{self.path_to_data}/collection/{archive_name}/{mechanism_name}.py'.replace(
            '//', '/')
        self.modm.write(path_to_py_file)

        module_name = path_to_py_file.replace('.py', '').replace('/', '.')
        module_name = module_name.split('src.')[-1]
        print(f'Module name: {module_name}')
        class_name = self.modm.ast.suffix.capitalize()
        Mechanism = dynamic_import(module_name, class_name)
        return Mechanism()

    def _add_mechanism_to_model(self, mechanism: Mechanism):
        self.mechanisms[mechanism.name] = mechanism
        print(f'Mechanism {mechanism.name} added to model.')

    # -----------------------------------------------------------------------
    # ADDING MECHANISMS TO GROUPS / REMOVING MECHANISMS FROM GROUPS
    # -----------------------------------------------------------------------

    def insert_mechs(self, mech_names: List[str] = None, 
                          group_names: List[str] = None):
        """
        Add a mechanism to the groups specified in groups_names where
        - they will be inserted into the sections
        - they will be used to distribute parameters 
        specified in mechanism.parameters list.
        """
        group_names = group_names or list(self.groups.keys())
        mech_names = mech_names or list(self.mechanisms.keys())

        group_names = [group_names] if isinstance(group_names, str) else group_names
        mech_names = [mech_names] if isinstance(mech_names, str) else mech_names

        groups = [self.groups[name] for name in group_names]
        mechs = [self.mechanisms[name] for name in mech_names]

        for group in groups:
            for mech in mechs:
                group.insert_mechanism(mech)

    def _find_nonoverlapping_nodes(self, target_group, mechanism_name):
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

    def uninsert_mechs(self, mech_names: List[str] = None, 
                            group_names: List[str] = None):
        """
        """
        group_names = group_names or list(self.groups.keys())
        mech_names = mech_names or list(self.mechanisms.keys())

        group_names = [group_names] if isinstance(group_names, str) else group_names
        mech_names = [mech_names] if isinstance(mech_names, str) else mech_names

        groups = [self.groups[name] for name in group_names]

        for group in groups:
            for mech_name in mech_names:
                node_ids = self._find_nonoverlapping_nodes(group, mech_name)
                group.uninsert_mechanism(mech_name, node_ids)

    # def insert_mechanisms(self, mechanism_names: List[str] = None, groups_names: List[str] = None):
    #     """
    #     Insert mechanisms to the sections in the specified groups.

    #     Parameters
    #     ----------
    #     mechanism_names : List[str], optional
    #         The names of the mechanisms to insert. If None, all mechanisms in the group will be inserted.
    #     groups_names : List[str], optional
    #         The names of the groups to insert mechanisms to. If None, mechanisms will be inserted to all groups.
    #     """
    #     mechanism_names = mechanism_names or []
    #     groups_names = groups_names or list(self.groups.keys())
        
    #     print(f'Inserting within groups: {groups_names}')
        
    #     for group_name in groups_names:
    #         group = self.groups[group_name]
    #         mechanisms_to_insert = mechanism_names or group.mechanisms
            
    #         for mechanism_name in mechanisms_to_insert:
    #             if mechanism_name in group.mechanisms:
    #                 group.insert(mechanism_name)

    # -----------------------------------------------------------------------
    # ADDING PARAMETERS TO GROUPS / REMOVING PARAMETERS FROM GROUPS
    # -----------------------------------------------------------------------

    def add_parameters(self, parameter_names: List[str] = None, groups_names: List[str] = None):
        """
        Add parameters to the sections in the specified groups.

        Parameters
        ----------
        parameter_names : List[str], optional
            The names of the parameters to add. If None, all parameters in the group will be added.
        groups_names : List[str], optional
            The names of the groups to add parameters to. If None, parameters will be added to all groups.
        """
        parameter_names = parameter_names or []
        groups_names = groups_names or list(self.groups.keys())
        
        print(f'Adding within groups: {groups_names}')
        
        for group_name in groups_names:
            group = self.groups[group_name]
            parameters_to_add = parameter_names or group.parameters
            
            for parameter_name in parameters_to_add:
                if parameter_name in group.parameters:
                    group.add_parameter(parameter_name)
    
    def distribute_params(self, param_names: List[str] = None, groups_names: List[str] = None):
        """
        Distribute parameters to the sections in the specified groups.

        Parameters
        ----------
        parameter_names : List[str], optional
            The names of the parameters to distribute. If None, all parameters in the group will be distributed.
        groups_names : List[str], optional
            The names of the groups to distribute parameters to. If None, parameters will be distributed to all groups.
        """
        param_names = param_names or []
        groups_names = groups_names or list(self.groups.keys())
        
        for group_name in groups_names:
            # logger.debug(f'Distributing within group: {group_name}')
            group = self.groups[group_name]
            params_to_distribute = param_names or group.parameters
            # logger.debug(f'Parameters to distribute: {params_to_distribute}')
            for param_name in params_to_distribute:
                if param_name in group.parameters:
                    # logger.debug(f'Distributing parameter {param_name} in group {group_name}')
                    print(f'Distributing parameter {param_name} in group {group_name}')
                    group.distribute(param_name)



    # ========================================================================
    # GROUPS
    # ========================================================================

    def add_group(self, group_name, nodes):
        """
        Add a group to the model.

        Parameters
        ----------
        group_name : str
            The name of the group.
        nodes : list[Node]
            The nodes to include in the group.
        """
        if group_name in self.groups:
            raise ValueError(f'Group {group_name} already exists')
        group = SectionGroup(group_name, nodes)
        self.groups[group.name] = group

    def remove_group(self, group_name):
        self.groups.pop(group_name)


    # ========================================================================
    # SEGMENTATION
    # ========================================================================

    def set_geom_nseg(self, d_lambda=0.1, f=100, use_neuron=False):
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

    def build_seg_tree(self):
        """
        Build the segment tree using the section tree.
        """
        # self.set_geom_nseg(d_lambda, f)

        nodes = []  # To store Segment objects

        def add_segments(sec, parent_idx, idx_counter):
            segs = {seg: idx + idx_counter for idx, seg in enumerate(sec._ref)}

            # Add each segment of this section as a Segment object
            for seg, idx in segs.items():
                # Create a Segment object with the parent index
                segment = Segment(
                    idx=idx, parent_idx=parent_idx, neuron_seg=seg, section=sec)
                nodes.append(segment)
                sec.segments.append(segment)

                # Update the parent index for the next segment in this section
                parent_idx = idx

            # Update idx_counter for the next section
            idx_counter += len(segs)

            # Recursively add child sections
            for child in sec.children:
                # IMPORTANT: This is needed since 0 and 1 segments are not explicitly
                # defined in the section segments list
                if child._ref.parentseg().x == 1:
                    new_parent_idx = list(segs.values())[-1]
                elif child._ref.parentseg().x == 0:
                    new_parent_idx = list(segs.values())[0]
                else:
                    new_parent_idx = segs[child._ref.parentseg()]
                # Recurse for the child section
                idx_counter = add_segments(child, new_parent_idx, idx_counter)

            return idx_counter

        # Start with the root section of the sec_tree
        add_segments(self.sec_tree.root, parent_idx=-1, idx_counter=0)

        # Assign the built list of Segment nodes to seg_tree as a Tree instance
        print(f'Building SEG tree...')
        self.seg_tree = SegmentTree(nodes)
 
    # ========================================================================
    # STIMULI
    # ========================================================================

    def load_synaptic_mechanisms(self):
        self.modm.load_mod_file('app/model/mechanisms/mod/Synapses/', 
                                recompile=not os.path.exists('app/model/mechanisms/mod/Synapses/x86_64/'))

    def _add_iclamp(self, iclamp):
        self.iclamps[iclamp.seg] = iclamp

    def add_iclamp(self, seg, amp=0, delay=100, dur=100):
        if self.iclamps.get(seg):
            self.remove_iclamp(seg)
        iclamp = IClamp(seg, amp, delay, dur)
        print(f'IClamp added to segment {seg}')
        self._add_iclamp(iclamp)

    def remove_iclamp(self, seg):
        if self.iclamps.get(seg):
            self.iclamps[seg] = None
            self.iclamps.pop(seg)

    def remove_all_iclamps(self):
        for seg in list(self.iclamps.keys()):
            self.remove_iclamp(seg)

    def _add_population(self, population):
        self.populations[population.name] = population

    def add_population(self, name, synapse_type, size, sections):
        population = Population(name, synapse_type, size, sections)
        self._add_population(population)

    # SIMULATION

    def add_recording(self, seg):
        self.simulator.add_recording(seg)

    def run(self, duration=300):
        self.simulator.run(duration)

    # MISC

    def reduce_morphology():
        ...

    def standardize_channel():
        ...

    # FILE EXPORT

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

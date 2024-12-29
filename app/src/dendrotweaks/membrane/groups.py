from typing import List, Callable, Dict

from dendrotweaks.morphology.trees import Node
from dendrotweaks.morphology.sec_trees import Section
from dendrotweaks.morphology.seg_trees import Segment
from dendrotweaks.membrane.mechanisms import Mechanism
from dendrotweaks.membrane.distributions import Distribution
from dendrotweaks.utils import timeit

# TODO: Sec or seg? Layering or partitioning? Make the user choose.

# Group first approach:

# Pros:
# - Better UX logic, the user first defines the domain and then its parameters.
# - Better output JSON, no need to duplicate nodes. G x N instead of P x G x N.

# Cons:
# - Need to modify the UI.
# - No layering, each node belongs to one and only one group (not necessarily!).

# ex. Group or SectionGroup or Domain
class SectionGroup():
    """
    A group of nodes often representing a domain.

    Parameters
    ----------
    name : str
        The name of the group.
    nodes : List[Node]
        The list of nodes in the group.
    mechanisms : dict
        The list of mechanisms.

    Example
    -------
    >>> nodes = sec_tree.sections[1:]
    >>> somatic = SectionGroup('somatic', nodes)
    >>> somatic.add_parameter('cm')
    >>> somatic.update_distribution_function_parameters('cm', value=2)
    """

    def __init__(self, name: str,
                 sections: List[Section],
                 mechanisms: List[str] = [],
                 parameters: Dict[str, Distribution] = {}):
        self.name = name
        self.sections = sections
        self.parameters = {}
        # self._add_default_parameters()
        self.mechanisms = {}
        for mechanism in mechanisms:
            self.add_mechanism(mechanism)
        for parameter, function_dict in parameters.items():
            func = Distribution.from_dict(function_dict)
            self.add_parameter(parameter, func)

    # def _add_default_parameters(self):
    #     self.add_parameter('cm', Distribution('uniform', value=1))
    #     self.add_parameter('Ra', Distribution('uniform', value=100))

    def __repr__(self):
        """
        Returns a string representation of the group.

        Returns
        -------
        str
            A string representation of the group.
        """
        return f'Group({self.name}) with {len(self.sections)} nodes\nParameters: {list(self.parameters.keys())}'

    # ------------------------------------------------------------
    # MECHANISMS
    # ------------------------------------------------------------

    def insert_mechanism(self, mechanism):
        """
        Adds a mechanism to the group, updating parameters accordingly.

        Parameters
        ----------
        mechanism : Mechanism
            The mechanism to add to the group.
        """
        for node in self.sections:
            node.insert_mechanism(mechanism.name)
        self.mechanisms[mechanism.name] = mechanism

    def uninsert_mechanism(self, mechanism_name, node_ids=None):
        """
        Removes a mechanism from the group. If node_ids are provided,
        the mechanism is removed only from the specified nodes.
        """
        if node_ids is not None:
            nodes = [node for node in self.sections if node.idx in node_ids]
        else:
            nodes = self.sections

        for node in nodes:
            node.uninsert_mechanism(mechanism_name)
        del self.mechanisms[mechanism_name]

    # TODO: Should be done manually one by one since not all needed.
    # def add_parameters_from_mechanism(self, mechanism):
    #     """
    #     Adds a mechanism to the group, updating parameters accordingly.

    #     Parameters
    #     ----------
    #     mechanism : Mechanism
    #         The mechanism to add to the group.
    #     """
    #     for node in self.sections:
    #         node.insert_mechanism(mechanism.name)
    #     for parameter, value in mechanism.parameters.items():
    #         self.add_parameter(parameter, Distribution('uniform', value=value))

    # def add_parameter(self, parameter_name, default_value=None):
    #     """
    #     Adds a parameter to the group with an optional distribution function.

    #     Parameters
    #     ----------
    #     parameter_name : str
    #         The name of the parameter to add.
    #     distribution_function : Distribution
    #         The distribution function to use for the parameter. Defaults to None.
    #     """
    #     value = default_value or 0
    #     distribution_function = Distribution('uniform', value=value)
    #     self._add_parameter(parameter_name, distribution_function)

    def add_parameter(self, parameter_name, 
                      distribution_function=None,
                      mechanism_name=None,
                      distribute=False):
        """
        Adds a parameter to the group with an optional distribution function.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter to add.
        distribution_function : Distribution
            The distribution function to use for the parameter.
        """
        value = 0
        if mechanism_name is not None:
            mechanism = self.mechanisms[mechanism_name]
            value = mechanism.parameters[parameter_name]
        function = distribution_function or Distribution('uniform', value=value)
        self.parameters[parameter_name] = function

    def remove_parameter(self, parameter_name):
        """
        Removes a parameter from the group.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter to remove.
        """
        # self.parameters[parameter_name] = Distribution('uniform', value=0)
        del self.parameters[parameter_name]

    def revert_parameter(self, parameter_name):
        """
        Reverts the parameter to its default value.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter to revert.
        """
        # if parameter belongs to any mechanism, revert to that value
        # in mechanism['parameter_name']. Otherwise, revert to 0.
        for mechanism in self.mechanisms.values():
            if parameter_name in mechanism.parameters:
                value = mechanism.parameters[parameter_name]
                break

        

    # TODO: No need for this, just update the dict.
    def set_distribution(self, parameter_name, distribution_type, **distribution_parameters):
        """
        For a given parameter, assignes the distribution with
        default parameters.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter to replace the distribution function for.
        distribution_name : str
            The new distribution to use for the parameter. Avaliable distributions
            are: 'uniform', 'linear', 

        """
        self.parameters[parameter_name] = Distribution(distribution_type, **distribution_parameters)

    # def update_distribution_parameters(self, parameter_name, **new_parameters):
    #     """
    #     Updates the parameters of a distribution function for a given parameter.

    #     Parameters
    #     ----------
    #     parameter_name : str
    #         The name of the parameter to update the distribution function for.
    #     \**new_parameters
    #         The new parameters to update the distribution function with.
    #     """
    #     distribution_function = self.parameters[parameter_name]
    #     distribution_function.update_parameters(**new_parameters)
    #     self.distribute(parameter_name)

    # APPLY
    # @timeit
    # def distribute_all(self):
    #     """
    #     Distributes all parameters to the nodes based on the distribution function.
    #     """
    #     for parameter_name in self.parameters.keys():
    #         print(f'Distributing {parameter_name}')
    #         self.distribute(parameter_name)

    @timeit
    def distribute(self, parameter_name: str) -> None:
        """
        Distributes the parameter values to the nodes based on the distribution function.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter to distribute.
        """
        distribution_function = self.parameters[parameter_name]
        for node in self.sections:
            node.set_param_value(parameter_name, distribution_function)

    # EXPORT

    def to_dict(self):
        """
        Exports the group to a dictionary format.

        Returns
        -------
        dict
            The group in dictionary format.
        """
        return {
            'nodes': [node.idx for node in self.sections],
            'mechanisms': [mechanism_name for mechanism_name in self.mechanisms],
            'parameters': {
                parameter_name: distribution_function.to_dict()
                for parameter_name, distribution_function in self.parameters.items()
            }
        }

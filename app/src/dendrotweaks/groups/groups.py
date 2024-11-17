from typing import List, Callable, Dict

from dendrotweaks.trees import Node, Section, Segment
from dendrotweaks.mechanisms import Mechanism
from dendrotweaks.groups.distribution_functions import ParametrizedFunction
from dendrotweaks.utils import timeit

# TODO: Sec or seg? Layering or partitioning? Make the user choose.

# Group first approach:

# Pros:
# - Better UX logic, the user first defines the domain and then its parameters.
# - Better output JSON, no need to duplicate nodes. G x N instead of P x G x N.

# Cons:
# - Need to modify the UI.
# - No layering, each node belongs to one and only one group (not necessarily!).


class Group():
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
    >>> somatic = Group('somatic', nodes)
    >>> somatic.add_parameter('cm')
    >>> somatic.update_distribution_function_parameters('cm', value=2)
    """

    def __init__(self, name: str,
                 nodes: List[Node],
                 mechanisms: List[Mechanism] = []) -> None:
        self.name = name
        self._nodes = nodes
        self.parameters = {'cm': ParametrizedFunction('uniform', value=1),
                           'Ra': ParametrizedFunction('uniform', value=100)}
        self.mechanisms = {}
        for mechanism in mechanisms:
            self.add_mechanism(mechanism)
        for parameter_name in self.parameters:
            self.distribute(parameter_name)

    @property
    def nodes(self):
        """
        Returns the list of nodes in the group.

        Returns
        -------
        List[Node]
            The list of nodes in the group.
        """
        return self._nodes

    def __repr__(self):
        """
        Returns a string representation of the group.

        Returns
        -------
        str
            A string representation of the group.
        """
        return f'Group({self.name}) with {len(self._nodes)} nodes\nParameters: {list(self.parameters.keys())}'

    # ADD and SET UP

    def add_mechanism(self, mechanism):
        """
        Adds a mechanism to the group, updating parameters accordingly.

        Parameters
        ----------
        mechanism : Mechanism
            The mechanism to add to the group.
        """
        for node in self._nodes:
            node.insert_mechanism(mechanism.name)
        self.mechanisms[mechanism.name] = mechanism

    # TODO: Should be done manually one by one since not all needed.
    # def add_parameters_from_mechanism(self, mechanism):
    #     """
    #     Adds a mechanism to the group, updating parameters accordingly.

    #     Parameters
    #     ----------
    #     mechanism : Mechanism
    #         The mechanism to add to the group.
    #     """
    #     for node in self._nodes:
    #         node.insert_mechanism(mechanism.name)
    #     for parameter, value in mechanism.parameters.items():
    #         self.add_parameter(parameter, ParametrizedFunction('uniform', value=value))

    def remove_mechanism(self, mechanism_name):
        for node in self._nodes:
            node.uninsert_mechanism(mechanism_name)
        del self.mechanisms[mechanism_name]


    def add_parameter(self, parameter_name, distribution_function=None):
        """
        Adds a parameter to the group with an optional distribution function.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter to add.
        distribution_function : ParametrizedFunction
            The distribution function to use for the parameter. Defaults to None.
        """
        if distribution_function is None:
            distribution_function = ParametrizedFunction('uniform')
        self.parameters[parameter_name] = distribution_function
        # TODO: Instead of setting to 0 by default, extract value from the _ref (see add_mechanism)
        self.distribute(parameter_name)

    def set_distribution(self, parameter_name, distribution_name):
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
        self.parameters[parameter_name] = ParametrizedFunction(distribution_name)
        self.distribute(parameter_name)

    def update_distribution_parameters(self, parameter_name, **new_parameters):
        """
        Updates the parameters of a distribution function for a given parameter.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter to update the distribution function for.
        \**new_parameters
            The new parameters to update the distribution function with.
        """
        distribution_function = self.parameters[parameter_name]
        distribution_function.update_parameters(**new_parameters)
        self.distribute(parameter_name)

    # APPLY
    @timeit
    def distribute(self, parameter_name):
        """
        Distributes the parameter values to the nodes based on the distribution function.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter to distribute.
        """
        distribution_function = self.parameters[parameter_name]
        for node in self._nodes:
            node.update_parameter(parameter_name, distribution_function)

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
            'group': {
                'name': self.name,
                'nodes': [node.idx for node in self._nodes],
                'parameters': [
                    self._parameter_to_dict(parameter_name, distribution_function)
                    for parameter_name, distribution_function in self.parameters.items()
                ]
            }
        }

    def _parameter_to_dict(self, parameter_name, distribution_function):
        """
        Helper method to convert a parameter and its distribution function to a dictionary format.

        Parameters
        ----------
        parameter_name : str
            The name of the parameter.
        distribution_function : ParametrizedFunction
            The distribution function for the parameter.

        Returns
        --------
        dict: 
            The parameter and its distribution function in dictionary format.
        """
        return {
            'name': parameter_name,
            'distribution_function': distribution_function.to_dict()
        }
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

class SectionGroup:
    """
    A group of sections often representing a domain.

    Parameters
    ----------
    name : str
        The name of the group.
    sections : List[Section]
        The list of sections in the group.
    """

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

    def to_dict(self) -> Dict:
        """
        Exports the group to a dictionary format.

        Returns
        -------
        dict
            The group in dictionary format.
        """
        return {
            'name': self.name,
            'mechanisms': [mechanism_name for mechanism_name in self.mechanisms],
            # 'sections': [sec.idx for sec in self.sections],
        }

    def __repr__(self):
        return f'Group("{self.name}", {len(self.sections)})'

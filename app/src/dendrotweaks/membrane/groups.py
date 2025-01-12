from typing import List, Callable, Dict

from dendrotweaks.morphology.trees import Node
from dendrotweaks.morphology.sec_trees import Section
from dendrotweaks.morphology.seg_trees import Segment
from dendrotweaks.membrane.mechanisms import Mechanism
from dendrotweaks.membrane.distributions import Distribution
from dendrotweaks.utils import timeit
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict

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
        self.params = {
            'domain': None,
            'diam': None,
            'distance': None,
        }
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


@dataclass
class Distribution:
    name: str
    domains: List[str] = field(default_factory=lambda: ['all'])
    dist: Tuple[float, float] = None
    diam: Tuple[float, float] = None
    distr_type: str = 'constant'
    distr_params: Dict = field(default_factory=dict)

    def __post_init__(self):
        self.function = DistributionFunction(self.distr_type, **self.distr_params)
        self.max_dist = self.dist[1] if self.dist else None
        self.min_dist = self.dist[0] if self.dist else None
        self.max_diam = self.diam[1] if self.diam else None
        self.min_diam = self.diam[0] if self.diam else None

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'function': self.function.to_dict(),
            'domains': self.domains,
            'max_dist': self.max_dist,
            'min_dist': self.min_dist,
            'max_diam': self.max_diam,
            'min_diam': self.min_diam,
        }

@dataclass
class SegmentGroup:
    name: str
    domains: List[str]
    min_dist: float = None
    max_dist: float = None
    min_diam: float = None
    max_diam: float = None

    def __contains__(self, segment: Segment) -> bool:
        return (
            segment.domain in self.domains and
            (self.min_dist is None or segment.distance_to_root > self.min_dist) and
            (self.max_dist is None or segment.distance_to_root < self.max_dist) and
            (self.min_diam is None or segment.diam > self.min_diam) and
            (self.max_diam is None or segment.diam < self.max_diam)
        )

    def __repr__(self):
        filters = [
            f"dist({self.min_dist}, {self.max_dist})" if self.min_dist is not None or self.max_dist is not None else "",
            f"diam({self.min_diam}, {self.max_diam})" if self.min_diam is not None or self.max_diam is not None else ""
        ]
        filters_str = ", ".join(filter(None, filters))
        return f'SegmentGroup("{self.name}", domains={self.domains}' + (f", {filters_str}" if filters_str else "") + ')'

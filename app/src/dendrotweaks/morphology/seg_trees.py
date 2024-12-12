from dendrotweaks.morphology.trees import Node, Tree


class Segment(Node):

    def __init__(self, idx, parent_idx, neuron_seg, section) -> None:
        """
        Create a wrapper for a NEURON segment.

        Args:
            idx (int): The index of the segment.
            parent_idx (int): The index of the parent segment.
            _seg (h.Segment): The NEURON segment object.
            sec (h.Section): The Section wrapper object.
        """
        super().__init__(idx, parent_idx)
        self._section = section
        self._ref = neuron_seg

    @property
    def domain(self):
        return self._section.domain

    @property
    def x(self):
        return self._ref.x

    @property
    def area(self):
        return self._ref.area()

    @property
    def diam(self):
        return self._ref.diam

    @property
    def subtree_size(self):
        return self._section.subtree_size

    @property
    def distance_to_root(self):
        return self._section.distance_to_root(self.x)

    def set_param_value(self, param_name, distribution_function):
        setattr(self._ref, param_name,
                distribution_function(self.distance_to_root))

    def get_param_value(self, param_name):
        return getattr(self, param_name, 
                        getattr(self._ref, param_name, 0))

class SegmentTree(Tree):

    def __init__(self, segments: list[Segment]) -> None:
        super().__init__(segments)
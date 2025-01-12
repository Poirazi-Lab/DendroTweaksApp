import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from typing import Callable
from neuron import h

from dendrotweaks.morphology.trees import Node, Tree

from bisect import bisect_left

class Section(Node):
    """
    A set of nodes with a relation on the set. A path.
    """

    def __init__(self, idx: str, parent_idx: str, pts3d: list[Node]) -> None:
        super().__init__(idx, parent_idx)
        self.pts3d = pts3d
        self.segments = []
        self._ref = None
        self.domain = self.pts3d[0].domain

    # MAGIC METHODS

    def __repr__(self):
        return f'••{self.idx}'

    def __call__(self, x: float):
        """
        Return the segment at a given position.
        """
        if self._ref is None:
            raise ValueError('Section is not referenced in NEURON.')
        if x < 0 or x > 1:
            raise ValueError('Location x must be in the range [0, 1].')
        elif x == 0: 
            # TODO: Decide how to handle sec(0) and sec(1)
            # as they are not shown in the seg_graph
            return self.segments[0]
        elif x == 1:
            return self.segments[-1]
        matching_segs = [self._ref(x) == seg._ref for seg in self.segments]
        if any(matching_segs):
            return self.segments[matching_segs.index(True)]
        raise ValueError('No segment found at location x.')
        
        

    # def __call__(self, x: float):
    #     """
    #     Return the Segment at a given position `x` in [0, 1].

    #     Parameters
    #     ----------
    #     x : float
    #         The position along the section's normalized length [0, 1].

    #     Returns
    #     -------
    #     Segment
    #         The custom Segment object corresponding to the location `x`.
    #     """
    #     if self._ref is None:
    #         raise ValueError('Section is not referenced in NEURON.')
    #     if not (0.0 <= x <= 1.0):
    #         raise ValueError('Location x must be in the range [0, 1].')
        
    #     idx = bisect_left(self.seg_borders, x) - 1
    #     return self.segments[max(0, idx)]


    def __iter__(self):
        """
        Iterate over the segments in the section.
        """
        for seg in self.segments:
            yield seg

    # PROPERTIES

    @property
    def df_pts3d(self):
        """
        Return the nodes in the section as a pandas DataFrame.
        """
        # concatenate the dataframes of the nodes
        return pd.concat([pt.df for pt in self.pts3d])

    @property
    def df(self):
        return pd.DataFrame({'idx': [self.idx],
                            'parent_idx': [self.parent_idx]})

    @property
    def diam(self):
        return self._ref.diam

    @property
    def L(self):
        return self._ref.L

    @property
    def Ra(self):
        return self._ref.Ra

    @property
    def nseg(self):
        return self._ref.nseg

    @property
    def radii(self):
        return [pt.r for pt in self.pts3d]

    @property
    def xs (self):
        return [pt.x for pt in self.pts3d]

    @property
    def ys(self):
        return [pt.y for pt in self.pts3d]

    @property
    def zs(self):
        return [pt.z for pt in self.pts3d]

    @property
    def seg_centers(self):
        if self._ref is None:
            raise ValueError('Section is not referenced in NEURON.')
        return (np.array([(2*i - 1) / (2 * self._ref.nseg)
                for i in range(1, self._ref.nseg + 1)]) * self._ref.L).tolist()

    @property
    def seg_borders(self):
        if self._ref is None:
            raise ValueError('Section is not referenced in NEURON.')
        nseg = int(self._ref.nseg)
        return [i / nseg for i in range(nseg + 1)]

    @property
    def distances(self):
        dx = np.diff(self.xs)
        dy = np.diff(self.ys)
        dz = np.diff(self.zs)

        distances = np.sqrt(dx**2 + dy**2 + dz**2)
        # distances = [np.sqrt((pt.x - pt.parent.x)**2 +
        #                      (pt.y - pt.parent.y)**2 +
        #                      (pt.z - pt.parent.z)**2)
        #              for pt in self.pts3d if pt.parent]
        distances = np.cumsum(distances)

        distances = np.insert(distances, 0, 0)
        return distances
        # return distances - distances[0]

    @property
    def center(self):
        return np.mean(self.xs), np.mean(self.ys), np.mean(self.zs)

    @property
    def length(self):
        return self.distances[-1]

    # REFERENCING METHODS

    def create_and_reference(self, simulator_name='NEURON'):
        """
        Add a reference to the section in the simulator.
        """
        if simulator_name == 'NEURON':
            self.create_NEURON_section()
        elif simulator_name == 'JAXLEY':
            self.create_JAXLEY_section()

    def create_NEURON_section(self):
        """
        Create a NEURON section.
        """
        self._ref = h.Section(name=f'Sec_{self.idx}')
        if self.parent is not None:
            # TODO: Attaching basal to soma 0
            if self.parent.parent is None: # if parent is soma
                self._ref.connect(self.parent._ref(0.5))
            else:
                self._ref.connect(self.parent._ref(1))
        # Add 3D points to the section
        for pt in self.pts3d:
            diam = 2*pt.r
            diam = round(diam, 16)
            self._ref.pt3dadd(pt.x, pt.y, pt.z, diam)

    def create_JAXLEY_section(self):
        """
        Create a JAXLEY section.
        """
        raise NotImplementedError

    # MECHANISM METHODS

    def insert_mechanism(self, name: str):
        """
        Insert a mechanism in the section.
        """
        # if already inserted, return
        if self._ref.has_membrane(name):
            return
        self._ref.insert(name)

    def uninsert_mechanism(self, name: str):
        """
        Uninsert a mechanism in the section.
        """
        # if already inserted, return
        if not self._ref.has_membrane(name):
            return
        self._ref.uninsert(name)

    # PARAMETER METHODS

    def get_param_value(self, param_name):
        """
        Get the average parameter of the section's segments.
        """
        # if param_name in ['Ra', 'diam', 'L', 'nseg', 'domain', 'subtree_size']:
        #     return getattr(self, param_name)
        # if param_name in ['dist']:
        #     return self.distance_to_root(0.5)
        seg_values = [seg.get_param_value(param_name) for seg in self.segments]
        return round(np.mean(seg_values), 16)


    # def set_param_value(self, parameter_name, distribution_function):
    #     """
    #     Update the parameter of the section.
    #     """
    #     if not isinstance(distribution_function, Callable):
    #         raise ValueError('Distribution function must be callable.')
    #     if self.segments and all([hasattr(seg._ref, parameter_name) for seg in self.segments]):
    #         # print(f'Setting {parameter_name} in segments')
    #         for seg in self.segments:
    #             seg.set_param_value(parameter_name, distribution_function)
    #     elif hasattr(self._ref, parameter_name):
    #         # print(f'Setting {parameter_name} in section')
    #         setattr(self._ref, parameter_name,
    #                 distribution_function(self.distance_to_root(0.5)))
    #     else:
    #         raise ValueError(f'Parameter {parameter_name} not found in section.')

    # GEOMETRIC METHODS

    def distance_to_root(self, relative_position: float = 0):
        if relative_position < 0 or relative_position > 1:
            raise ValueError('Relative position must be between 0 and 1.')
        return self.pts3d[0].distance_to_root + relative_position * self.length

    # PLOTTING METHODS

    def plot(self, ax=None, plot_parent=True, color='C0', 
             set_aspect=True, remove_ticks=False):
        """
        Plot the nodes in the section.
        """
        if ax is None:
            fig, ax = plt.subplots(2, 2)

        marker_style = 'o-' if plot_parent else 'o-'
        titles = ['XZ', 'YZ', 'XY']
        coords = [(self.xs, self.zs), (self.ys, self.zs), (self.xs, self.ys)]
        labels = [('X', 'Z'), ('Y', 'Z'), ('X', 'Y')]

        for i, (coord, title, label) in enumerate(zip(coords, titles, labels)):
            row, col = divmod(i, 2)
            ax[row][col].plot(*coord, marker_style, color=color, fillstyle='full' if plot_parent else 'none')
            ax[row][col].set_title(title)
            ax[row][col].set_xlabel(label[0])
            ax[row][col].set_ylabel(label[1])
            if set_aspect:
                ax[row][col].set_aspect('equal')
            if remove_ticks:
                ax[row][col].set_xticks([])
                ax[row][col].set_yticks([])


        self.plot_radii(ax[1][1], plot_parent=plot_parent)


        if plot_parent:
            plt.suptitle(f'{self.idx} - {self.domain}')
            if self.parent:
                self.parent.plot(ax=ax, plot_parent=False, color='C1')

        plt.tight_layout()

    def plot_radii(self, ax=None, plot_parent=True):
        """
        Plot the radii in the section.
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 5))

        if plot_parent and self.parent:
            child_to_parent_distance = np.sqrt(
                (self.pts3d[0].x - self.parent.pts3d[-1].x)**2 +
                (self.pts3d[0].y - self.parent.pts3d[-1].y)**2 +
                (self.pts3d[0].z - self.parent.pts3d[-1].z)**2
            )
            distances = self.distances + child_to_parent_distance
        else: 
            distances = self.distances - self.distances[-1]

        ax.plot(distances, self.radii, 'o-', label='SWC radii', fillstyle='full' if plot_parent else 'none')

        if self._ref:
            avg_rs = [seg.diam / 2 for seg in self._ref]
            bar_width = [self._ref.L / self._ref.nseg] * self._ref.nseg
            if plot_parent and self.parent:
                seg_centers = np.array(self.seg_centers) + child_to_parent_distance
            else: 
                seg_centers = np.array(self.seg_centers) - self.distances[-1]

            ax.bar(seg_centers, avg_rs, width=bar_width, edgecolor='white', color='C1', label='Segment radii')

        ax.set_title('Radius')
        ax.set_ylim(0, max(self.radii) + 0.1 * max(self.radii))


# @dataclass
# class Domain():
#     name: str
#     sections: List[Section]
#     mechanisms: List[str] = field(default_factory=lambda: ['Independent'])


class SectionTree(Tree):
    def __init__(self, sections: list[Section]) -> None:
        super().__init__(sections)
        
    @property
    def domains_to_sections(self):
        domains_to_sections = {}
        for sec in self.sections:
            domains_to_sections.setdefault(sec.domain, []).append(sec)
        return domains_to_sections

    # def _create_domains(self):
    # """
    # Create the domains in the tree.
    # """
    # for sec in self.sections:
    #     if sec.domain not in self.domains:
    #         self.domains[sec.domain] = Domain(sec.domain)
    #     self.domains[sec.domain].sections.append(sec)

    @property
    def sections(self):
        return self._nodes

    @property
    def soma(self):
        return self.root

    def sort(self):
        """
        
        """
        print('Sorting sections...')
        count_sections = 0
        count_pts3d = 0
        count_segments = 0

        for sec in self.traverse():
            sec.idx = count_sections
            sec.parent_idx = sec.parent.idx if sec.parent else -1
            count_sections += 1

            for pt in sec.pts3d:
                pt.idx = count_pts3d
                pt.parent_idx = pt.parent.idx if pt.parent else -1
                count_pts3d += 1

            for seg in sec:
                seg.idx = count_segments
                seg.parent_idx = seg.parent.idx if seg.parent else -1
                count_segments += 1

    def plot_sections_as_matrix(self, ax=None):
        """
        Plot the sections as a connectivity matrix.
        """
        if ax is None:
            fig, ax = plt.subplots()

        n = len(self.sections)
        matrix = np.zeros((n, n))
        for section in self.sections:
            if section.parent:
                matrix[section.idx, section.parent.idx] = section.idx
        matrix[matrix == 0] = np.nan

        ax.imshow(matrix.T, cmap='jet_r')
        ax.set_xlabel('Section ID')
        ax.set_ylabel('Parent ID')

    def plot(self, ax=None, show_points=False, show_lines=True, 
                      annotate=False, projection='XY'):
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))

        x_attr, y_attr = projection[0], projection[1]

        for sec in self.sections:
            coords = {'X': [pt.x for pt in sec.pts3d],
                  'Y': [pt.y for pt in sec.pts3d],
                  'Z': [pt.z for pt in sec.pts3d]}
            xs = coords[x_attr]
            ys = coords[y_attr]
            if show_points:
                ax.plot(xs, ys, '.', color=plt.cm.jet(
                    1-sec.idx/len(self.sections)), markersize=5)
            if show_lines:
                ax.plot(xs, ys, color=plt.cm.jet(
                    1-sec.idx/len(self.sections)))

            # annotate the section index
            if annotate:
                ax.annotate(f'{sec.idx}', (np.mean(
                    xs), np.mean(ys)), fontsize=8)
                ax.annotate(f'{sec.idx}', (np.mean(xs), np.mean(ys)), fontsize=8,
                        bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.3'))

        ax.set_xlabel(projection[0])
        ax.set_ylabel(projection[1])
        ax.set_aspect('equal')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from typing import Callable, List
from neuron import h

from dendrotweaks.morphology.trees import Node, Tree
from dendrotweaks.morphology.domains import Domain
from dataclasses import dataclass, field
from bisect import bisect_left

import warnings

def custom_warning_formatter(message, category, filename, lineno, file=None, line=None):
    return f"{category.__name__}: {message} ({os.path.basename(filename)}, line {lineno})\n"

warnings.formatwarning = custom_warning_formatter

DOMAINS_TO_COLORS = {
    'soma': '#E69F00',       
    'apic': '#0072B2',       
    'dend': '#019E73',       
    'basal': '#31A354',      
    'axon': '#F0E442',       
    'trunk': '#56B4E9',
    'tuft': '#A55194', #'#9467BD',
    'oblique': '#8C564B',
    'perisomatic': '#D55E00',
    # 'custom': '#BDBD22',
    'custom': '#D62728',
    'custom2': '#E377C2',
    'undefined': '#7F7F7F',
}

class Section(Node):
    """
    A set of nodes with a relation on the set. A path.
    """

    def __init__(self, idx: str, parent_idx: str, pts3d: List[Node]) -> None:
        super().__init__(idx, parent_idx)
        self.pts3d = pts3d
        self.segments = []
        self._ref = None
        self._domain = self.pts3d[0].domain

        if not all(pt.domain == self._domain for pt in pts3d):
            raise ValueError('All points in a section must belong to the same domain.')

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
        

    def __iter__(self):
        """
        Iterate over the segments in the section.
        """
        for seg in self.segments:
            yield seg

    # PROPERTIES

    @property
    def domain(self):
        return self._domain

    @domain.setter
    def domain(self, domain):
        self._domain = domain
        for pt in self.pts3d:
            pt.domain = domain

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
        coords = np.array([[pt.x, pt.y, pt.z] for pt in self.pts3d])
        deltas = np.diff(coords, axis=0)
        frusta_distances = np.sqrt(np.sum(deltas**2, axis=1))
        cumulative_frusta_distances = np.insert(np.cumsum(frusta_distances), 0, 0)
        return cumulative_frusta_distances

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
        self._ref = h.Section() # name=f'Sec_{self.idx}'
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
        Inserts a mechanism in the section if 
        it is not already inserted.
        """
        # if already inserted, return
        if self._ref.has_membrane(name):
            return
        self._ref.insert(name)

    def uninsert_mechanism(self, name: str):
        """
        Uninserts a mechanism in the section if
        it was inserted.
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


    def path_distance(self, relative_position: float = 0, 
                        stop_at_domain_change: bool = False) -> float:
        """
        Calculate the distance from the section to the root at a given relative position.

        Parameters
        ----------
        relative_position : float
            The position along the section's normalized length [0, 1].

        Returns
        -------
        float
            The distance from the section to the root.

        Important
        ---------
        Assumes that we always attach the 0 end of the child.
        """
        if not (0 <= relative_position <= 1):
            raise ValueError('Relative position must be between 0 and 1.')

        distance = 0
        factor = relative_position
        node = self

        while node.parent:

            distance += factor * node.length

            if stop_at_domain_change and node.parent.domain != node.domain:
                break

            node = node.parent
            factor = 1
            
        return distance
        

    
    def disconnect_from_parent(self):
        """
        Detach the section from the parent.
        """
        # In SectionTree
        super().disconnect_from_parent()
        # In NEURON
        if self._ref:
            h.disconnect(sec=self._ref) #from parent
        # In SWCTree
        self.pts3d[0].disconnect_from_parent()
        # In SegmentTree
        if self.segments:
            self.segments[0].disconnect_from_parent()

    def connect_to_parent(self, parent):
        """
        Attaches the section to a parent section.
        """
        # In SectionTree
        super().connect_to_parent(parent)
        # In NEURON
        if self._ref:
            if self.parent is not None:
                if self.parent.parent is None: # if parent is soma
                    self._ref.connect(self.parent._ref(0.5))
                else:
                    self._ref.connect(self.parent._ref(1))
                
        # In SWCTree
        if self.parent is not None:
            if self.parent.parent is None: # if parent is soma
                self.pts3d[0].connect_to_parent(self.parent.pts3d[1]) # attach to the middle of the parent
            else:
                self.pts3d[0].connect_to_parent(parent.pts3d[-1]) # attach to the end of the parent
        # In SegmentTree
        if self.segments:
            self.segments[0].connect_to_parent(parent.segments[-1])


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


class SectionTree(Tree):

    def __init__(self, sections: list[Section]) -> None:
        super().__init__(sections)
        self._create_domains()
        self._swc_tree = None
        self._seg_tree = None


    def _create_domains(self):
        """
        Create the domains in the tree.
        """

        unique_domain_names = set([sec.domain for sec in self.sections])
        self.domains = {name: Domain(name) for name in unique_domain_names}

        for sec in self.sections:
            self.domains[sec.domain].add_section(sec)
            

    @property
    def sections(self):
        return self._nodes

    @property
    def soma(self):
        return self.root

    @property
    def sections_by_depth(self):
        """
        Return the sections grouped by depth.
        """
        sections_by_depth = {}
        for sec in self.sections:
            if sec.depth not in sections_by_depth:
                sections_by_depth[sec.depth] = []
            sections_by_depth[sec.depth].append(sec)
        return sections_by_depth

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

            if sec.parent is None:
                sec.pts3d[1].idx = count_pts3d
                sec.pts3d[1].parent_idx = -1
                count_pts3d += 1
                sec.pts3d[0].idx = count_pts3d
                sec.pts3d[0].parent_idx = sec.pts3d[0].parent.idx
                count_pts3d += 1
                sec.pts3d[2].idx = count_pts3d
                sec.pts3d[2].parent_idx = sec.pts3d[2].parent.idx
                count_pts3d += 1
            else:
                for pt in sec.pts3d:
                    pt.idx = count_pts3d
                    pt.parent_idx = pt.parent.idx
                    count_pts3d += 1

            for seg in sec:
                seg.idx = count_segments
                seg.parent_idx = seg.parent.idx if seg.parent else -1
                count_segments += 1

    def sort(self):
        super().sort()
        self._swc_tree.sort()
        if self._seg_tree:
            self._seg_tree.sort()

    def remove_subtree(self, section):
        super().remove_subtree(section)
        # Domains
        for domain in self.domains.values():
            for sec in section.subtree:
                if sec in domain.sections:
                    domain.remove_section(sec)
        # Points
        self._swc_tree.remove_subtree(section.pts3d[0])
        # Segments
        if self._seg_tree:
            self._seg_tree.remove_subtree(section.segments[0])
        # NEURON
        if section._ref:
            h.disconnect(sec=section._ref)
            for sec in section.subtree:
                h.delete_section(sec=sec._ref)


    def downsample(self, factor: float):
        """
        Downsample the SWC tree by reducing the number of points in each section 
        based on the given factor, while preserving the first and last points.
        
        :param factor: The proportion of points to keep (e.g., 0.5 keeps 50% of points)
        """
        for sec in self.sections:
            if sec is self.soma:
                continue

            if len(sec.pts3d) < 3:  # Keep sections with only start & end points
                continue

            num_points = len(sec.pts3d)
            num_to_keep = max(2, int(num_points * factor))  # Ensure at least start & end remain

            # Select indices to keep (first, last, and spaced indices in between)
            keep_indices = np.linspace(0, num_points - 1, num_to_keep, dtype=int)
            keep_set = set(keep_indices)

            points_to_remove = [pt for i, pt in enumerate(sec.pts3d) if i not in keep_set]

            print(f'Removing {len(points_to_remove)} points from section {sec.idx}')
            
            for pt in points_to_remove:
                self._swc_tree.remove_node(pt)
            
        self._swc_tree.sort()

            

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
                      annotate=False, projection='XY', domains=False):
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))

        x_attr, y_attr = projection[0], projection[1]

        for sec in self.sections:
            coords = {'X': [pt.x for pt in sec.pts3d],
                      'Y': [pt.y for pt in sec.pts3d],
                      'Z': [pt.z for pt in sec.pts3d]}
            xs = coords[x_attr]
            ys = coords[y_attr]
            
            color = plt.cm.jet(1-sec.idx/len(self.sections))
            if domains:
                color = DOMAINS_TO_COLORS.get(sec.domain, color)
            
            if show_points:
                ax.plot(xs, ys, '.', color=color, markersize=5)
            if show_lines:
                ax.plot(xs, ys, color=color)

            # annotate the section index
            if annotate:
                ax.annotate(f'{sec.idx}', (np.mean(xs), np.mean(ys)), fontsize=8)
                ax.annotate(f'{sec.idx}', (np.mean(xs), np.mean(ys)), fontsize=8,
                            bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.3'))

        ax.set_xlabel(projection[0])
        ax.set_ylabel(projection[1])
        ax.set_aspect('equal')

    def plot_radii_distribution(self, ax=None, highlight=None, 
    domains=True, show_soma=False):
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 3))

        for sec in self.sections:
            if not show_soma and sec.parent is None:
                continue
            color = 'gray'
            if domains:
                color = DOMAINS_TO_COLORS.get(sec.domain, color)
            if highlight and sec.idx in highlight:
                ax.plot(
                    [pt.path_distance() for pt in sec.pts3d], 
                    sec.radii, 
                    marker='.', 
                    color='red', 
                    zorder=2
                )
            else:
                ax.plot(
                    [pt.path_distance() for pt in sec.pts3d], 
                    sec.radii, 
                    marker='.', 
                    color=color, 
                    zorder=1
                )
        ax.set_xlabel('Distance from root')
        ax.set_ylabel('Radius')

    def to_swc(self, path_to_file: str):
        """
        Save the SectionTree as an SWC file.
        """
        if not self.is_sorted or not self._swc_tree.is_sorted:
            raise ValueError('The tree must be sorted before saving.')

        data = {
            'idx': [],
            'type_idx': [],
            'x': [],
            'y': [],
            'z': [],
            'r': [],
            'parent_idx': []
        }

        for sec in self.sections:
            pts3d = sec.pts3d if sec.parent is None or sec.parent.parent is None else sec.pts3d[1:]
            for pt in pts3d:
                data['idx'].append(pt.idx)
                data['type_idx'].append(pt.type_idx)
                data['x'].append(pt.x)
                data['y'].append(pt.y)
                data['z'].append(pt.z)
                data['r'].append(pt.r)
                data['parent_idx'].append(pt.parent_idx)

        df = pd.DataFrame(data)
        df.to_csv(path_to_file, sep=' ', index=False, header=False)

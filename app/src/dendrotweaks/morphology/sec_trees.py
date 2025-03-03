import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.colors as mcolors

from typing import Callable, List
from neuron import h

from dendrotweaks.morphology.trees import Node, Tree
from dendrotweaks.morphology.domains import Domain
from dataclasses import dataclass, field
from bisect import bisect_left

import warnings

from dendrotweaks.utils import DOMAINS_TO_COLORS

def custom_warning_formatter(message, category, filename, lineno, file=None, line=None):
    return f"{category.__name__}: {message} ({os.path.basename(filename)}, line {lineno})\n"

warnings.formatwarning = custom_warning_formatter



class Section(Node):
    """
    A set of nodes with a relation on the set. A path.
    """

    def __init__(self, idx: str, parent_idx: str, points: List[Node]) -> None:
        super().__init__(idx, parent_idx)
        self.points = points
        self.segments = []
        self._ref = None
        self._domain = self.points[0].domain

        if not all(pt.domain == self._domain for pt in points):
            raise ValueError('All points in a section must belong to the same domain.')

    # MAGIC METHODS


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
        for pt in self.points:
            pt.domain = domain

    @property
    def df_points(self):
        """
        Return the nodes in the section as a pandas DataFrame.
        """
        # concatenate the dataframes of the nodes
        return pd.concat([pt.df for pt in self.points])

    @property
    def df(self):
        return pd.DataFrame({'idx': [self.idx],
                            'parent_idx': [self.parent_idx]})

    # TODO: Figure out why this is different from NEURON's diam
    # @property
    # def diam(self):
    #     """
    #     Average diameter of the section calculated from
    #     the radii and distances of the points.
    #     """
    #     distances = self.distances  # Cumulative distances
    #     radii = self.radii  # Corresponding radii
    #     total_length = distances[-1]  # Total section length
        
    #     if total_length == 0:
    #         return 0  # Avoid division by zero for zero-length sections

    #     segment_lengths = np.diff(distances)  # Lengths of frusta segments
    #     segment_diameters = 2 * (np.array(radii[:-1]) + np.array(radii[1:])) / 2  # Mean diameter per segment

    #     # Length-weighted average
    #     avg_diameter = np.sum(segment_diameters * segment_lengths) / total_length

    #     return avg_diameter

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
        return [pt.r for pt in self.points]

    @property
    def xs (self):
        return [pt.x for pt in self.points]

    @property
    def ys(self):
        return [pt.y for pt in self.points]

    @property
    def zs(self):
        return [pt.z for pt in self.points]

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
        coords = np.array([[pt.x, pt.y, pt.z] for pt in self.points])
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

    @property
    def area(self):
        """
        Calculate the area of the section using the formula for a frustum.
        """
        areas = [np.pi * (r1 + r2) * np.sqrt((r1 - r2)**2 + h**2) for r1, r2, h in zip(self.radii[:-1], self.radii[1:], np.diff(self.distances))]
        return sum(areas)

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
        for pt in self.points:
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
                        within_domain: bool = False) -> float:
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

            if within_domain and node.parent.domain != node.domain:
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
        # In PointTree
        self.points[0].disconnect_from_parent()
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
                
        # In PointTree
        if self.parent is not None:
            if self.parent.parent is None: # if parent is soma
                parent_sec = self.parent
                parent_pt = parent_sec.points[1] if len(parent_sec.points) > 1 else parent_sec.points[0]
                self.points[0].connect_to_parent(parent_pt) # attach to the middle of the parent
            else:
                self.points[0].connect_to_parent(parent.points[-1]) # attach to the end of the parent
        # In SegmentTree
        if self.segments:
            self.segments[0].connect_to_parent(parent.segments[-1])


    # PLOTTING METHODS
   
    def plot(self, ax=None, plot_parent=True, section_color=None, parent_color='gray', 
             show_labels=True, aspect_equal=True):
        """
        Plot section morphology in 3D projections (XZ, YZ, XY) and radii distribution.
        
        Parameters
        ----------
        ax : list or array of matplotlib.axes.Axes, optional
            Four axes for plotting (XZ, YZ, XY, radii). If None, creates a new figure with axes.
        plot_parent : bool, optional
            Whether to include parent section in the visualization.
        section_color : str or None, optional
            Color for the current section. If None, assigns based on section domain.
        parent_color : str, optional
            Color for the parent section.
        show_labels : bool, optional
            Whether to show axis labels and titles.
        aspect_equal : bool, optional
            Whether to set aspect ratio to 'equal' for the projections.
            
        Returns
        -------
        ax : list of matplotlib.axes.Axes
            The axes containing the plots.
        """
        # Create figure and axes if not provided
        if ax is None:
            fig = plt.figure(figsize=(10, 8))
            gs = GridSpec(2, 3, width_ratios=[1, 1, 1.2], figure=fig)
            
            # Create the three projection axes and one radius axis
            ax_xz = fig.add_subplot(gs[0, 0])
            ax_yz = fig.add_subplot(gs[0, 1])
            ax_xy = fig.add_subplot(gs[1, 0])
            ax_radii = fig.add_subplot(gs[1, 1:])
            ax = [ax_xz, ax_yz, ax_xy, ax_radii]
        else:
            # Use provided axes
            if len(ax) != 4:
                # flatten 
                ax = [ai for a in ax for ai in a]
            ax_xz, ax_yz, ax_xy, ax_radii = ax
        
        # Determine section color based on domain if not provided
        if section_color is None:
            section_color = DOMAINS_TO_COLORS.get(self.domain, 'gray')
        
        # Extract coordinates
        xs = np.array([p.x for p in self.points])
        ys = np.array([p.y for p in self.points])
        zs = np.array([p.z for p in self.points])
        
        # Plot section projections
        self._plot_projection(ax_xz, xs, zs, 'X', 'Z', 'XZ Projection', 
                              section_color, show_labels, aspect_equal)
        self._plot_projection(ax_yz, ys, zs, 'Y', 'Z', 'YZ Projection', 
                              section_color, show_labels, aspect_equal)
        self._plot_projection(ax_xy, xs, ys, 'X', 'Y', 'XY Projection', 
                              section_color, show_labels, aspect_equal)
        
        # Plot radius distribution
        self._plot_radii_distribution(ax_radii, plot_parent, section_color, parent_color)
        
        # Plot parent section if requested
        if plot_parent and self.parent:
            # Only plot parent projections, radii are handled in _plot_radii_distribution
            parent_xs = np.array([p.x for p in self.parent.points])
            parent_ys = np.array([p.y for p in self.parent.points])
            parent_zs = np.array([p.z for p in self.parent.points])
            
            self.parent._plot_projection(ax_xz, parent_xs, parent_zs, None, None, None, 
                                         parent_color, False, aspect_equal)
            self.parent._plot_projection(ax_yz, parent_ys, parent_zs, None, None, None, 
                                         parent_color, False, aspect_equal)
            self.parent._plot_projection(ax_xy, parent_xs, parent_ys, None, None, None, 
                                         parent_color, False, aspect_equal)
        
        # Add overall title if we created the figure
        if ax is not None and show_labels:
            fig = ax_xz.get_figure()
            fig.suptitle(f"Section {self.idx} ({self.domain})", fontsize=14)
            fig.tight_layout()
        
        return ax
    
    def _plot_projection(self, ax, x_coords, y_coords, x_label, y_label, title, 
                         color, show_labels, aspect_equal):
        """Helper method to plot a 2D projection of the section."""
        ax.plot(x_coords, y_coords, 'o-', color=color, markerfacecolor=color, 
                markeredgecolor='black', markersize=4, linewidth=1.5)
        
        if show_labels:
            if x_label:
                ax.set_xlabel(x_label)
            if y_label:
                ax.set_ylabel(y_label)
            if title:
                ax.set_title(title)
        
        if aspect_equal:
            ax.set_aspect('equal')
    
    def _plot_radii_distribution(self, ax, plot_parent, section_color, parent_color):
        """Helper method to plot radius distribution along the section."""
        # Get section length for normalization
        section_length = self.distances[-1] - self.distances[0]
        
        # Normalize distances to start at 0 and end at section_length
        normalized_distances = self.distances - self.distances[0]
        
        # Plot section radii
        ax.plot(normalized_distances, self.radii, 'o-', color=section_color, 
                label=f"{self.domain} ({self.idx})", linewidth=2)
        
        # Plot reference NEURON segments if available
        if hasattr(self, '_ref') and self._ref:
            # Calculate normalized segment centers
            normalized_seg_centers = np.array(self.seg_centers) - self.distances[0]
            
            # Extract radii from segments
            seg_radii = np.array([seg.diam / 2 for seg in self._ref])
            
            # Use the specified bar width calculation from original code
            bar_width = [self._ref.L / self._ref.nseg] * self._ref.nseg
            
            # Plot segment radii as bars
            ax.bar(normalized_seg_centers, seg_radii, width=bar_width, 
                   alpha=0.5, color=section_color, edgecolor='white',
                   label=f"{self.domain} segments")
        
        # Plot parent section if requested
        if plot_parent and self.parent:
            parent_length = self.parent.distances[-1] - self.parent.distances[0]
            
            # Normalize parent distances to end at 0 (connecting to child)
            # Parent section goes from -parent_length to 0
            normalized_parent_distances = self.parent.distances - self.parent.distances[-1]
            
            # Plot parent radii
            ax.plot(normalized_parent_distances, self.parent.radii, 'o-', 
                    color=parent_color, linewidth=2,
                    label=f"Parent {self.parent.domain} ({self.parent.idx})")
            
            # Plot parent reference segments if available
            if hasattr(self.parent, '_ref') and self.parent._ref:
                # Normalize parent segment centers to the same scale
                normalized_parent_seg_centers = (np.array(self.parent.seg_centers) - 
                                                self.parent.distances[-1])
                
                # Extract parent segment radii
                parent_seg_radii = np.array([seg.diam / 2 for seg in self.parent._ref])
                
                # Use the specified bar width calculation for parent
                parent_bar_width = [self.parent._ref.L / self.parent._ref.nseg] * self.parent._ref.nseg
                
                # Plot parent segment radii as bars
                ax.bar(normalized_parent_seg_centers, parent_seg_radii, 
                       width=parent_bar_width, alpha=0.5, color=parent_color, 
                       edgecolor='white', label=f"Parent segments")
        
        # Set plot labels and legend
        ax.set_xlabel('Distance (µm)')
        ax.set_ylabel('Radius (µm)')
        ax.set_title('Radius Distribution')
        
        # Ensure y-axis starts at 0
        ax.set_ylim(bottom=0)
        
        # Adjust x-axis to show the full section(s)
        if plot_parent and self.parent:
            parent_length = self.parent.distances[-1] - self.parent.distances[0]
            ax.set_xlim(-parent_length * 1.05, section_length * 1.05)
        else:
            ax.set_xlim(-section_length * 0.05, section_length * 1.05)
        
        # Add legend if we have multiple data series
        if ((hasattr(self, '_ref') and self._ref) or 
            (plot_parent and self.parent)):
            ax.legend(loc='best', frameon=True, framealpha=0.8)

    def plot_radii(self, ax=None, include_parent=False, section_color=None, parent_color='gray'):
        """
        Plot just the radius distribution for the section.
        
        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes to plot on. If None, creates a new figure and axes.
        include_parent : bool, optional
            Whether to include parent section in the plot.
        section_color : str or None, optional
            Color for current section. If None, assigns based on section domain.
        parent_color : str, optional
            Color for parent section if included.
            
        Returns
        -------
        ax : matplotlib.axes.Axes
            The axes containing the plot.
        """
        # Create new figure and axes if not provided
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 5))
        
        # Determine section color based on domain if not provided
        if section_color is None:
            domain_colors = {
                'soma': 'black',
                'axon': 'red',
                'dend': 'blue',
                'apic': 'green'
            }
            section_color = domain_colors.get(self.domain, 'purple')
        
        # Plot radius distribution
        self._plot_radii_distribution(ax, include_parent, section_color, parent_color)
        
        # Add title if creating a standalone plot
        if ax.get_figure().get_axes()[0] == ax:  # If this is the only axes in the figure
            ax.set_title(f"Radius Distribution - Section {self.idx} ({self.domain})")
            plt.tight_layout()
        
        return ax


class SectionTree(Tree):

    def __init__(self, sections: list[Section]) -> None:
        super().__init__(sections)
        self._create_domains()
        self._point_tree = None
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
        count_points = 0
        count_segments = 0

        for sec in self.traverse():
            sec.idx = count_sections
            sec.parent_idx = sec.parent.idx if sec.parent else -1
            count_sections += 1

            if sec.parent is None:
                sec.points[1].idx = count_points
                sec.points[1].parent_idx = -1
                count_points += 1
                sec.points[0].idx = count_points
                sec.points[0].parent_idx = sec.points[0].parent.idx
                count_points += 1
                sec.points[2].idx = count_points
                sec.points[2].parent_idx = sec.points[2].parent.idx
                count_points += 1
            else:
                for pt in sec.points:
                    pt.idx = count_points
                    pt.parent_idx = pt.parent.idx
                    count_points += 1

            for seg in sec:
                seg.idx = count_segments
                seg.parent_idx = seg.parent.idx if seg.parent else -1
                count_segments += 1

    def sort(self):
        super().sort()
        self._point_tree.sort()
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
        self._point_tree.remove_subtree(section.points[0])
        # Segments
        if self._seg_tree:
            self._seg_tree.remove_subtree(section.segments[0])
        # NEURON
        if section._ref:
            h.disconnect(sec=section._ref)
            for sec in section.subtree:
                h.delete_section(sec=sec._ref)

    def remove_zero_length_sections(self):
        """
        Remove sections with zero length.
        """
        for sec in self.sections:
            if sec.length == 0:
                for pt in sec.points:
                    self._point_tree.remove_node(pt)
                for seg in sec.segments:
                    self._seg_tree.remove_node(seg)
                self.remove_node(sec)



    def downsample(self, factor: float):
        """
        Downsample the SWC tree by reducing the number of points in each section 
        based on the given factor, while preserving the first and last points.
        
        :param factor: The proportion of points to keep (e.g., 0.5 keeps 50% of points)
                       If factor is 0, keep only the first and last points.
        """
        for sec in self.sections:
            if sec is self.soma:
                continue

            if len(sec.points) < 3:  # Keep sections with only start & end points
                continue

            num_points = len(sec.points)
            if factor == 0:
                num_to_keep = 2
            else:
                num_to_keep = max(2, int(num_points * factor))  # Ensure at least start & end remain

            # Select indices to keep (first, last, and spaced indices in between)
            keep_indices = np.linspace(0, num_points - 1, num_to_keep, dtype=int)
            keep_set = set(keep_indices)

            points_to_remove = [pt for i, pt in enumerate(sec.points) if i not in keep_set]

            print(f'Removing {len(points_to_remove)} points from section {sec.idx}')
            
            for pt in points_to_remove:
                self._point_tree.remove_node(pt)
                sec.points.remove(pt)
            
        self._point_tree.sort()

            

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
            show_domains=True, annotate=False, 
            projection='XY', highlight_sections=None, focus_sections=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))

        highlight_sections = set(highlight_sections) if highlight_sections else None
        focus_sections = set(focus_sections) if focus_sections else None
        x_attr, y_attr = projection[0].lower(), projection[1].lower()

        section_count = len(self.sections)  # Avoid recalculating

        for sec in self.sections:
            # Skip sections that are not in the focus set (if focus is specified)
            if focus_sections and sec not in focus_sections:
                continue

            xs = [getattr(pt, x_attr) for pt in sec.points]
            ys = [getattr(pt, y_attr) for pt in sec.points]

            # Assign colors based on domains or section index
            color = plt.cm.jet(1 - sec.idx / section_count)
            if show_domains:
                color = DOMAINS_TO_COLORS.get(sec.domain, color)
            if highlight_sections and sec in highlight_sections:
                color = 'red'

            # Plot section points and lines
            if show_points:
                ax.plot(xs, ys, '.', color=color, markersize=7, markeredgecolor='black')
            if show_lines:
                ax.plot(xs, ys, color=color, zorder=0)

            # Annotate section index if needed
            if annotate:
                mean_x, mean_y = np.mean(xs), np.mean(ys)
                ax.annotate(
                    f'{sec.idx}', (mean_x, mean_y), fontsize=8,
                    color='white',
                    bbox=dict(facecolor='black', edgecolor='white', 
                    boxstyle='round,pad=0.3')
                )

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
                    [pt.path_distance() for pt in sec.points], 
                    sec.radii, 
                    marker='.', 
                    color='red', 
                    zorder=2
                )
            else:
                ax.plot(
                    [pt.path_distance() for pt in sec.points], 
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
        if not self.is_sorted or not self._point_tree.is_sorted:
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
            points = sec.points if sec.parent is None or sec.parent.parent is None else sec.points[1:]
            for pt in points:
                data['idx'].append(pt.idx)
                data['type_idx'].append(pt.type_idx)
                data['x'].append(pt.x)
                data['y'].append(pt.y)
                data['z'].append(pt.z)
                data['r'].append(pt.r)
                data['parent_idx'].append(pt.parent_idx)

        df = pd.DataFrame(data)
        df.to_csv(path_to_file, sep=' ', index=False, header=False)

    @property
    def df(self):
        data = {
            'idx': [],
            'domain': [],
            'x': [],
            'y': [],
            'z': [],
            'r': [],
            'parent_idx': [],
            'section_idx': [],
            'parent_section_idx': [],
        }

        for sec in self.sections:
            points = sec.points if sec.parent is None or sec.parent.parent is None else sec.points[1:]
            for pt in points:
                data['idx'].append(pt.idx)
                data['domain'].append(pt.domain)
                data['x'].append(pt.x)
                data['y'].append(pt.y)
                data['z'].append(pt.z)
                data['r'].append(pt.r)
                data['parent_idx'].append(pt.parent_idx)
                data['section_idx'].append(sec.idx)
                data['parent_section_idx'].append(sec.parent_idx)

        return pd.DataFrame(data)
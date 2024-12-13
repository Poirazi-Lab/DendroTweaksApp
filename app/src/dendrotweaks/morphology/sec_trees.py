import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from neuron import h

from dendrotweaks.morphology.trees import Node, Tree

class Section(Node):
    """
    A set of nodes with a relation on the set. A path.
    """

    def __init__(self, idx: str, parent_idx: str, pts3d: list[Node]) -> None:
        super().__init__(idx, parent_idx)
        self.pts3d = pts3d
        self.segments = []
        self._ref = None

    # MAGIC METHODS

    def __repr__(self):
        return f'••{self.idx}'

    def __call__(self, x: float):
        """
        Return the segment at a given position.
        """
        if self._ref is None:
            raise ValueError('Section is not referenced in NEURON.')
        return self._ref(x)

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
    def domain(self):
        return self.pts3d[0].domain

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
        return distances.tolist()
        # return distances - distances[0]

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
            diam = round(2*pt.r, 2)
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

    def set_param_value(self, parameter_name, distribution_function):
        """
        Update the parameter of the section.
        """
        if self.segments and all([hasattr(seg._ref, parameter_name) for seg in self.segments]):
            # print(f'Setting {parameter_name} in segments')
            for seg in self.segments:
                seg.set_param_value(parameter_name, distribution_function)
        elif hasattr(self._ref, parameter_name):
            # print(f'Setting {parameter_name} in section')
            setattr(self._ref, parameter_name,
                    distribution_function(self.distance_to_root(0.5)))
        else:
            raise ValueError(f'Parameter {parameter_name} not found in section.')

    # GEOMETRIC METHODS

    def distance_to_root(self, relative_position: float = 0):
        if relative_position < 0 or relative_position > 1:
            raise ValueError('Relative position must be between 0 and 1.')
        return self.pts3d[0].distance_to_root + relative_position * self.length

    # PLOTTING METHODS

    def plot_pts3d(self, ax=None, plot_radii=True, plot_parent=True, color='C0'):
        """
        Plot the nodes in the section.
        """
        if ax is None:
            fig, ax = plt.subplots(2, 2)

        marker_style = 'o-' if plot_parent else 'o-'
        ax[0][0].plot(self.xs, self.zs, marker_style, color=color, fillstyle='full' if plot_parent else 'none')
        ax[0][1].plot(self.ys, self.zs, marker_style, color=color, fillstyle='full' if plot_parent else 'none')
        ax[1][0].plot(self.xs, self.ys, marker_style, color=color, fillstyle='full' if plot_parent else 'none')
        ax[0][0].set_title('XZ')
        ax[0][1].set_title('YZ')
        ax[1][0].set_title('XY')
        for a in ax:
            for b in a:
                b.set_aspect('equal')
        if plot_radii:
            self.plot_radii(ax[1][1])
        else:
            ax[1][1].axis('off')
        plt.suptitle(f'{self.idx} - {self.domain}')

        if plot_parent and self.parent:
            self.parent.plot_pts3d(ax=ax, plot_radii=plot_radii, plot_parent=False, color='C1')

        return ax

    def plot_radii(self, ax=None):
        """
        Plot the radii in the section.
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(self.distances, self.radii, 'o-', label='SWC radii')

        avg_rs = [seg.diam/2 for seg in self._ref]

        bar_width = [self._ref.L / self._ref.nseg] * self._ref.nseg

        ax.bar(self.seg_centers, avg_rs, width=bar_width,
               edgecolor='white', color='C1', label='Segment radii')

        ax.set_title('Radius')
        ax.set_aspect('auto')
        ax.set_ylim(0, max(self.radii) + 1/10 * max(self.radii))
        ax.legend()

        return ax


class SectionTree(Tree):

    def __init__(self, sections: list[Section]) -> None:
        super().__init__(sections)

    @property
    def sections(self):
        return self._nodes

    @property
    def soma(self):
        return self.root

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

    def plot_sections(self, ax=None, show_points=False, show_lines=True, 
                      annotate=False):

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))

        for sec in self.sections:
                
            xs = [pt.x for pt in sec.pts3d]
            ys = [pt.y for pt in sec.pts3d]
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

        ax.set_aspect('equal')
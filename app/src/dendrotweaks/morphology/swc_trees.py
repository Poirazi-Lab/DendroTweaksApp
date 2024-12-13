import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.spatial.transform import Rotation

from dendrotweaks.utils import timeit

from dendrotweaks.morphology.trees import Node, Tree

SWC_TYPES = {
    1: 'soma',
    2: 'axon',
    3: 'dend',
    4: 'apic'
}


class SWCNode(Node):

    def __init__(self, idx: str, type_idx: int, 
                 x: float, y: float, z: float, r: float, 
                 parent_idx: str) -> None:
        super().__init__(idx, parent_idx)
        self.type_idx = type_idx
        self.x = x
        self.y = y
        self.z = z
        self.r = r
        self._section = None

    def info(self):
        info = (
            f"Node {self.idx}:\n"
            f"  Type: {SWC_TYPES.get(self.type_idx, 'unknown')}\n"
            f"  Coordinates: ({self.x}, {self.y}, {self.z})\n"
            f"  Radius: {self.r}\n"
            f"  Parent: {self.parent_idx}\n"
            f"  Section: {self._section.idx if self._section else 'None'}"
        )
        print(info)
    
    @property
    def domain(self):
        return SWC_TYPES.get(self.type_idx, 'unknown')

    @property
    def distance_to_parent(self):
        if not self.parent:
            return 0
        return np.sqrt((self.x - self.parent.x)**2 + (self.y - self.parent.y)**2 + (self.z - self.parent.z)**2)

    @property
    def distance_to_root(self):
        if not self.parent:
            return 0
        return self.parent.distance_to_root + self.distance_to_parent

    @property
    def df(self):
        # put the required data in a pandas dataframe
        return pd.DataFrame({'idx': [self.idx],
                             'type_idx': [self.type_idx],
                             'x': [self.x],
                             'y': [self.y],
                             'z': [self.z],
                             'r': [self.r],
                             'parent_idx': [self.parent_idx]})

    def copy(self):
        new_node = SWCNode(self.idx, self.type_idx, self.x,
                            self.y, self.z, self.r, self.parent_idx)
        return new_node


class SWCTree(Tree):

    def __init__(self, nodes: list[SWCNode]) -> None:
        super().__init__(nodes)
        self._sections = []
        self._is_extended = False

    # PROPERTIES

    @property
    def pts3d(self):
        return self._nodes

    @property
    def is_sectioned(self):
        return len(self._sections) > 0

    @property
    def soma_pts3d(self):
        return [pt for pt in self.pts3d if pt.type_idx == 1]

    @property
    def soma_center(self):
        return np.mean([[pt.x, pt.y, pt.z] 
                        for pt in self.soma_pts3d], axis=0)

    @property
    def apical_center(self):
        apical_pts3d = [pt for pt in self.pts3d 
                        if pt.type_idx == 4]
        if len(apical_pts3d) == 0:
            return None
        return np.mean([[pt.x, pt.y, pt.z] 
                       for pt in apical_pts3d], axis=0)

    @property
    def soma_notation(self):
        if len(self.soma_pts3d) == 1:
            return '1PS'
        elif len(self.soma_pts3d) == 2:
            return '2PS'
        elif len(self.soma_pts3d) == 3:
            return '3PS'
        else:
            return 'contour'

    # SORTING METHODS

    def _sort_root_children(self):
        """
        Sort the children of the root node based on the distance to the root.
        """
        self.root.children = sorted(self.root.children, key=lambda x: (x.type_idx, x.idx), reverse=True)

    # SECTIONING METHODS

    @timeit
    def split_to_sections(self):
        """
        Build the sections using bifurcation points.
        """
        from dendrotweaks.morphology.sec_trees import Section

        self._sections = []

        bifurcation_children = [
            child for b in self.bifurcations for child in b.children]
        bifurcation_children = [self.root] + bifurcation_children
        bifurcation_children = sorted(bifurcation_children,
                                      key=lambda x: x.idx)

        # Assign a section to each bifurcation child
        for i, child in enumerate(bifurcation_children):
            section = Section(idx=i, parent_idx=-1, pts3d=[child])
            self._sections.append(section)
            child._section = section
            # Propagate the section to the children until the next 
            # bifurcation or termination point is reached
            while child.children:
                next_child = child.children[0]
                if next_child in bifurcation_children:
                    break
                next_child._section = section
                section.pts3d.append(next_child)
                child = next_child

            section.parent = section.pts3d[0].parent._section if section.pts3d[0].parent else None
            section.parent_idx = section.parent.idx if section.parent else -1
            # section.parent_idx = section.pts3d[0].parent._section.idx if section.pts3d[0].parent else -1

    # SOMA METHODS

    def merge_soma(self):
        """
        If soma has 3PS notation, merge it into one section.
        """
        
        soma_pts3d = self.soma_pts3d
        soma_pts3d.remove(self.root)
        soma_pts3d.insert(1, self.root)


        # Create a new section for the soma
        true_soma = self.root._section
        true_soma.pts3d = soma_pts3d
        for node in soma_pts3d:
            node._section = true_soma

        # Replace the soma sections with the new one
        soma_sections = [sec for sec in self._sections
                        if any([pt.type_idx == 1 for pt in sec.pts3d])]
        for sec in soma_sections:
            self._sections.remove(sec)
        self._sections = [true_soma] + self._sections

        # Update the indices
        for sec in self._sections:
            sec.idx = sec.idx - 2 if sec.idx > 1 else sec.idx
            sec.parent_idx = sec.parent_idx - 2 if sec.parent_idx > 1 else sec.parent_idx

    # EXTENSION METHODS

    def extend_sections(self):
        """
        Extends the section by adding a copy of the last node from the parent section
        to the beginning of the section. This is done to ensure continuity between sections.
        The method checks if the sections have already been extended to avoid duplication.

        Attributes:
            _is_extended (bool): A flag indicating whether the sections have 
                        already been extended.
            _sections (list): A list of sections in the tree structure.
            soma (object): The root section.
            soma_notation (str): The notation used for the soma.

        Notes:
            - The method is implemented similarly to the NEURON's approach to section extension.
            - If the section's parent is the soma, it extends the section only if it has
            a single point. 
            - Given the above, for '3PS' notation, instead of the last point it copies 
            the second point of the parent section (the root point).
        """
        if self._is_extended:
            print('Sections are already extended.')
            return
        for sec in self._sections:
            if not sec.parent:
                continue
            first_node = sec.pts3d[0]
            if sec.parent is self.soma:
                if len(sec.pts3d) > 1:
                    continue # do not extend the soma children in general
                if self.soma_notation == '3PS':
                    node_to_copy = sec.parent.pts3d[1]
                else:
                    node_to_copy = sec.parent.pts3d[-1]
            node_to_copy = sec.parent.pts3d[-1]
            new_node = node_to_copy.copy()
            # Copy SWC-specific attributes
            new_node.type_idx = first_node.type_idx
            new_node._section = first_node._section
            # Insert the new node at the beginning of the section
            self.insert_node(first_node.idx, new_node)
            sec.pts3d.insert(0, new_node)
        self._is_extended = True

    # COORDINATE TRANSFORMATION METHODS

    def shift_coordinates_to_soma_center(self):
        """
        Shift all coordinates so that the soma center is at the origin (0, 0, 0).
        """
        soma_x, soma_y, soma_z = self.soma_center
        for pt in self.pts3d:
            pt.x = round(pt.x - soma_x, 8)
            pt.y = round(pt.y - soma_y, 8)
            pt.z = round(pt.z - soma_z, 8)

    def rotate(self, angle_deg, axis='Y'):
        """Rotate the point cloud around the specified axis at the soma center using scipy."""
        # Convert angle to radians and create a rotation object
        
        angle_rad = np.radians(angle_deg)

        rotation_vector = {
            'X': np.array([1, 0, 0]),
            'Y': np.array([0, 1, 0]),
            'Z': np.array([0, 0, 1])
        }.get(axis.upper(), None)

        if rotation_vector is None:
            raise ValueError("Axis must be 'X', 'Y', or 'Z'")

        rotation = Rotation.from_rotvec(angle_rad * rotation_vector)

        # Translate points to origin, rotate, and translate back
        for pt in self.pts3d:
            coords = np.array([pt.x, pt.y, pt.z]) - self.soma_center
            rotated_coords = rotation.apply(coords) + self.soma_center
            pt.x, pt.y, pt.z = rotated_coords

    def align_apical_dendrite(self, axis='Y', facing='up'):
        

        soma_center = self.soma_center
        apical_center = self.apical_center

        if apical_center is None:
            raise ValueError("No apical dendrite found.")

        # Define the target vector based on the axis and facing
        target_vector = {
            'X': np.array([1, 0, 0]),
            'Y': np.array([0, 1, 0]),
            'Z': np.array([0, 0, 1])
        }.get(axis.upper(), None)

        if target_vector is None:
            raise ValueError("Axis must be 'X', 'Y', or 'Z'")

        if facing == 'down':
            target_vector = -target_vector

        # Calculate the rotation vector and angle
        current_vector = apical_center - soma_center
        rotation_vector = np.cross(current_vector, target_vector)
        rotation_angle = np.arccos(np.dot(current_vector, target_vector) / np.linalg.norm(current_vector))

        # Create the rotation matrix
        rotation_matrix = Rotation.from_rotvec(rotation_angle * rotation_vector / np.linalg.norm(rotation_vector)).as_matrix()

        # Apply the rotation to each point
        for pt in self.pts3d:
            coords = np.array([pt.x, pt.y, pt.z]) - soma_center
            rotated_coords = np.dot(rotation_matrix, coords) + soma_center
            pt.x, pt.y, pt.z = rotated_coords



    # PLOTTING METHODS

    def plot_points(self, ax=None, edges=True, 
                    annotate=False, projection='XY'):

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))

        # Create a dictionary for coordinates
        coords = {'X': [pt.x for pt in self.pts3d],
                  'Y': [pt.y for pt in self.pts3d],
                  'Z': [pt.z for pt in self.pts3d]}

        if edges:
            for edge in self.edges:
                edge_coords = {'X': [edge[0].x, edge[1].x],
                               'Y': [edge[0].y, edge[1].y],
                               'Z': [edge[0].z, edge[1].z]}
                ax.plot(edge_coords[projection[0]], edge_coords[projection[1]], color='red')

        ax.plot(coords[projection[0]], coords[projection[1]], '.', color='k', markersize=5)

        # Annotate the node index
        if annotate and len(self.pts3d) < 50:
            for pt in self.pts3d:
                ax.annotate(f'{pt.idx}', (coords[projection[0]][pt.idx], coords[projection[1]][pt.idx]), fontsize=8)

        ax.set_xlabel(projection[0])
        ax.set_ylabel(projection[1])
        ax.set_aspect('equal')

    def plot_sections(self, ax=None, show_points=False, show_lines=True, 
                      annotate=False):

        if not self.is_sectioned:
            raise ValueError('Tree is not sectioned. Use split_to_sections() method.')

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))

        for sec in self._sections:
            xs = [pt.x for pt in sec.pts3d]
            ys = [pt.y for pt in sec.pts3d]
            if show_points:
                ax.plot(xs, ys, '.', color=plt.cm.jet(
                    1-sec.idx/len(self._sections)), markersize=5)
            if show_lines:
                ax.plot(xs, ys, color=plt.cm.jet(
                    1-sec.idx/len(self._sections)))

            # annotate the section index
            if annotate:
                ax.annotate(f'{sec.idx}', (np.mean(
                    xs), np.mean(ys)), fontsize=8)
                ax.annotate(f'{sec.idx}', (np.mean(xs), np.mean(ys)), fontsize=8,
                            bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.3'))

        ax.set_aspect('equal')
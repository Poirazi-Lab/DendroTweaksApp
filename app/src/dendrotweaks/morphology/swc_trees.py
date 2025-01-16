import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.spatial.transform import Rotation

from dendrotweaks.utils import timeit

from dendrotweaks.morphology.trees import Node, Tree

from dendrotweaks.utils import timeit

SWC_TYPES = {
    0: 'undefined',
    1: 'soma',
    2: 'axon',
    3: 'dend',
    4: 'apic',
    5: 'custom',
    6: 'neurite',
    7: 'glia',
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
    
    @property
    def domain(self):
        return SWC_TYPES.get(self.type_idx, 'unknown')

    @property
    def distance_to_parent(self):
        if self.parent:
            return np.sqrt((self.x - self.parent.x)**2 + (self.y - self.parent.y)**2 + (self.z - self.parent.z)**2)
        return 0

    @property
    def distance_to_root(self):
        if self.parent:
            return self.parent.distance_to_root + self.distance_to_parent
        return 0

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

    def info(self):
        info = (
            f"Node {self.idx}:\n"
            f"  Type: {SWC_TYPES.get(self.type_idx, 'unknown')}\n"
            f"  Coordinates: ({self.x}, {self.y}, {self.z})\n"
            f"  Radius: {self.r}\n"
            f"  Parent: {self.parent_idx}\n"
            f"  Children: {[child.idx for child in self.children]}\n"
            f"  Siblings: {[sibling.idx for sibling in self.siblings]}\n"
            f"  Section: {self._section.idx if self._section else 'None'}"
        )
        print(info)

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

    @property
    def df(self):
        data = {
            'idx': [node.idx for node in self._nodes],
            'type_idx': [node.type_idx for node in self._nodes],
            'x': [node.x for node in self._nodes],
            'y': [node.y for node in self._nodes],
            'z': [node.z for node in self._nodes],
            'r': [node.r for node in self._nodes],
            'parent_idx': [node.parent_idx for node in self._nodes],
        }
        return pd.DataFrame(data)



    # SORTING METHODS

    def _sort_children(self):
        """
        Iterate through all nodes in the tree and sort their children based on
        the number of bifurcations (nodes with more than one child) in each child's
        subtree. Nodes with fewer bifurcations in their subtrees are placed earlier in the list
        of the node's children, ensuring that the shortest paths are traversed first.

        Returns
        -------
            None
        """
        for node in self._nodes:
            node.children = sorted(
                node.children, 
                key=lambda x: (x.type_idx, sum(1 for n in x.subtree if len(n.children) > 1)),
                reverse=False
            )



    # COORDINATE TRANSFORMATION METHODS

    def soma_to_3PS_notation(self):
        """
        Convert the soma to 3PS notation.
        """
        if self.soma_notation == '3PS':
            print('Soma is already in 3PS notation.')
            return

        if self.soma_notation == '1PS':
            # if soma has 1PS notation, create two new nodes
            # using the first node of the soma, its radius
            pt = self.soma_pts3d[0]
            self._nodes.remove(pt)

            r = pt.r
            x = [pt.x] * 3
            y = [pt.y, pt.y - r, pt.y + r]
            z = [pt.z] * 3
            r = [r] * 3
            parent_idx = [-1, 1, 1]

            new_nodes = [SWCNode(idx=i, 
                                 type_idx=1, 
                                 x=x[i], y=y[i], z=z[i], r=r[i], 
                                 parent_idx=parent_idx[i]) for i in range(3)]

            self._nodes = new_nodes + self._nodes

            for node in new_nodes:
                node._section = self.root._section

            # Update the parent index of the root node
            soma = Section(idx=0, parent_idx=-1, pts3d=new_nodes)
            
        elif self.soma_notation =='contour':
            # if soma has contour notation, take the average
            # distance of the nodes from the center of the soma
            # and use it as radius, create 3 new nodes
            ...

    def shift_coordinates_to_soma_center(self):
        """
        Shift all coordinates so that the soma center is at the origin (0, 0, 0).
        """
        soma_x, soma_y, soma_z = self.soma_center
        for pt in self.pts3d:
            pt.x = round(pt.x - soma_x, 8)
            pt.y = round(pt.y - soma_y, 8)
            pt.z = round(pt.z - soma_z, 8)

    @timeit
    def rotate(self, angle_deg, axis='Y'):
        """Rotate the point cloud around the specified axis at the soma center using numpy."""

        # Get the rotation center point
        rotation_point = self.soma_center

        # Define rotation matrix based on the specified axis
        angle = np.radians(angle_deg)
        if axis == 'X':
            rotation_matrix = np.array([
                [1, 0, 0],
                [0, np.cos(angle), -np.sin(angle)],
                [0, np.sin(angle), np.cos(angle)]
            ])
        elif axis == 'Y':
            rotation_matrix = np.array([
                [np.cos(angle), 0, np.sin(angle)],
                [0, 1, 0],
                [-np.sin(angle), 0, np.cos(angle)]
            ])
        elif axis == 'Z':
            rotation_matrix = np.array([
                [np.cos(angle), -np.sin(angle), 0],
                [np.sin(angle), np.cos(angle), 0],
                [0, 0, 1]
            ])
        else:
            raise ValueError("Axis must be 'X', 'Y', or 'Z'")

        # Subtract rotation point to translate the cloud to the origin
        coords = np.array([[pt.x, pt.y, pt.z] for pt in self.pts3d])
        coords -= rotation_point

        # Apply rotation
        rotated_coords = np.dot(coords, rotation_matrix.T)

        # Translate back to the original position
        rotated_coords += rotation_point

        # Update the coordinates of the points
        for pt, (x, y, z) in zip(self._nodes, rotated_coords):
            pt.x, pt.y, pt.z = x, y, z

    def align_apical_dendrite(self, axis='Y', facing='up'):
        soma_center = self.soma_center
        apical_center = self.apical_center

        if apical_center is None:
            return

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

        # Calculate the current vector
        current_vector = apical_center - soma_center

        # Check if the apical dendrite is already aligned
        if np.allclose(current_vector / np.linalg.norm(current_vector), target_vector):
            print('Apical dendrite is already aligned.')
            return

        # Calculate the rotation vector and angle
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

    def plot(self, ax=None, edges=True, 
             annotate=False, projection='XY', 
             highlight=None):

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
                ax.plot(edge_coords[projection[0]], edge_coords[projection[1]], color='C1')

        ax.plot(coords[projection[0]], coords[projection[1]], '.', color='C0', markersize=5)

        # Annotate the node index
        if annotate and len(self.pts3d) < 50:
            for pt in self.pts3d:
                ax.annotate(f'{pt.idx}', (coords[projection[0]][pt.idx], coords[projection[1]][pt.idx]), fontsize=8)

        # Highlight the specified node
        if highlight:
            for pt in highlight:
                ax.plot(coords[projection[0]][pt.idx], coords[projection[1]][pt.idx], 'o', color='C3', markersize=5)

        ax.set_xlabel(projection[0])
        ax.set_ylabel(projection[1])
        ax.set_aspect('equal')

    # def plot_sections(self, ax=None, show_points=False, show_lines=True, 
    #                   annotate=False):

    #     if not self.is_sectioned:
    #         raise ValueError('Tree is not sectioned. Use split_to_sections() method.')

    #     if ax is None:
    #         fig, ax = plt.subplots(figsize=(10, 10))

    #     for sec in self._sections:
    #         xs = [pt.x for pt in sec.pts3d]
    #         ys = [pt.y for pt in sec.pts3d]
    #         if show_points:
    #             ax.plot(xs, ys, '.', color=plt.cm.jet(
    #                 1-sec.idx/len(self._sections)), markersize=5)
    #         if show_lines:
    #             ax.plot(xs, ys, color=plt.cm.jet(
    #                 1-sec.idx/len(self._sections)))

    #         # annotate the section index
    #         if annotate:
    #             ax.annotate(f'{sec.idx}', (np.mean(
    #                 xs), np.mean(ys)), fontsize=8)
    #             ax.annotate(f'{sec.idx}', (np.mean(xs), np.mean(ys)), fontsize=8,
    #                         bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.3'))

    #     ax.set_aspect('equal')
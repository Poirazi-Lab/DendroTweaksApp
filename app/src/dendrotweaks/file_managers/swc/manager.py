from dendrotweaks.morphology.swc_trees import SWCNode, SWCTree
from dendrotweaks.morphology.sec_trees import Section, SectionTree
from dendrotweaks.file_managers.utils import list_folders, list_files
import pandas as pd
from io import StringIO
import os
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.animation import PillowWriter

# TODO: Think of the use cases.
# - Change soma notation (1PS, 3PS, contour)
# + Insert / remove sections / nodes
# - Update section diameter
# + Rotate the tree
# Do we really need to implement all of these?
# Given there is HBP Morphology Viewer.


class SWCManager():

    def __init__(self, path_to_data='data'):
        self._df = None
        self.swc_tree = None
        self.sec_tree = None
        self.path_to_data = path_to_data
        self._file_name = None

    def to_dict(self):
        return {
            'swc_file_name': self._file_name,
        }

    # FILE MANAGEMENT

    def list_files(self):
        path_to_swc = os.path.join(self.path_to_data, 'swc')
        return list_files(path_to_swc, extension='.swc')

    # READ

    def read(self, file_name=None):

        if file_name:
            self._file_name = file_name
            path_to_file = f'{self.path_to_data}/swc/{file_name}'.replace('//', '/')
            self.df = pd.read_csv(path_to_file,
                                  sep=' ',
                                  header=None,
                                  comment='#',
                                  names=['id', 'type', 'x', 'y', 'z', 'r', 'parent_id'])

        if self.df['id'].duplicated().any():
            raise ValueError("The SWC file contains duplicate node ids.")

    # BUILD TREES

    def build_swc_tree(self):
        """
        Build SWC tree from the DataFrame.
        """
        print("Building SWC tree...")
        nodes = [SWCNode(row['id'],
                         row['type'],
                         row['x'],
                         row['y'],
                         row['z'],
                         row['r'],
                         row['parent_id'])
                 for _, row in self.df.iterrows()]

        self.swc_tree = SWCTree(nodes)

    def postprocess_swc_tree(self, sort=False, split=False, shift=False, extend=False):

        print("Postprocessing SWC tree...")
        # 1. Sort the tree
        if sort:
            print("  Sorting tree...")
            if self.swc_tree.is_sorted:
                print("  Tree is already sorted.")
            else:
                self.swc_tree.sort()

        # 2. Split the tree to sections
        if split:
            print("Splitting tree to sections...")
            if self.swc_tree.is_sectioned:
                print('  Sections already exist.')
            else:
                self.swc_tree.split_to_sections()

            # 3. Merge soma in case of 3PS notation
            print("Merging soma into a single section...")
            if len(self.swc_tree._soma_sections) == 3:
                self.swc_tree.merge_soma()

        # 4. Shift coordinates to soma center
        if shift:
            print("Shifting coordinates to soma center...")
            self.swc_tree.shift_coordinates_to_soma_center()

        # 5. Extend the tree
        if extend:
            print("Extending tree...")
            self.swc_tree.extend_sections()

        self.validate_swc_tree()

    def build_sec_tree(self):
        """
        Build SEC tree from the SWC tree and validate it.
        """
        print("Building SEC tree...")
        sections = self.swc_tree._sections
        self.sec_tree = SectionTree(sections)
        self.validate_sec_tree()

    # VALIDATE TREES

    def validate_swc_tree(self):
        check_nodes_match_root_subtree(self.swc_tree)
        check_unique_ids(self.swc_tree)
        check_connections(self.swc_tree)
        validate_parents(self.swc_tree)

        print("SWC tree validation passed successfully")
        print(f"    is connected:{self.swc_tree.is_connected:2}")
        print(f"    is sorted:   {self.swc_tree.is_sorted:2}")
        print(f"    is sectioned:{self.swc_tree.is_sectioned:2}")
        print(f"    is extended: {self.swc_tree._is_extended:2}")

    def validate_sec_tree(self):
        check_nodes_match_root_subtree(self.sec_tree)
        check_unique_ids(self.sec_tree)
        check_connections(self.sec_tree)
        validate_parents(self.sec_tree)
        validate_node_reference_to_section(self.sec_tree)

        print("SEC tree validation passed successfully.")
        print(f"    is connected:{self.sec_tree.is_connected:2}")
        print(f"    is sorted:   {self.sec_tree.is_sorted:2}")

    def validate_trees_match(self):
        validate_points_match(self.swc_tree, self.sec_tree)
        validate_sections_match(self.swc_tree, self.sec_tree)

    # PLOTTING METHODS

    def plot_raw_data(self, ax):
        types_to_colors = {1: 'C1', 2: 'C3', 3: 'C2', 4: 'C0'}
        for t in self.df['type'].unique():
            color = types_to_colors.get(t, 'k')
            mask = self.df['type'] == t
            ax.scatter(self.df[mask]['x'], self.df[mask]['y'], self.df[mask]['z'], 
                       c=color, s=1, label=f'Type {t}')
        ax.legend()


    





    def plot_3d(self, ax=None, show_points=True, show_lines=True, annotate=False, animate=True, 
                frames=360, interval=25, save_as_gif=True, gif_filename="animation.gif"):
        """
        Plot the 3D morphology of the SWC tree, with an option to save as a GIF.
        Removes the frame to show only the black background.
        """
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.animation import FuncAnimation
        from matplotlib.animation import PillowWriter

        if ax is None:
            fig = plt.figure(figsize=(5, 5), facecolor='black')  # Set the figure background to black
            ax = fig.add_subplot(111, projection='3d')
        else:
            fig = ax.get_figure()  # Get the figure if ax is provided

        # Remove figure frame
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)  # Remove margins around the plot area

        # Set up the 3D plot aesthetics
        ax.set_facecolor('black')
        ax.w_xaxis.pane.set_edgecolor('black')
        ax.w_yaxis.pane.set_edgecolor('black')
        ax.w_zaxis.pane.set_edgecolor('black')
        ax.w_xaxis.line.set_color((0.0, 0.0, 0.0, 0.0))
        ax.w_yaxis.line.set_color((0.0, 0.0, 0.0, 0.0))
        ax.w_zaxis.line.set_color((0.0, 0.0, 0.0, 0.0))
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.xaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)
        ax.yaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)
        ax.zaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)

        for sec in self.sec_tree.sections:
            xs = [pt.x for pt in sec.pts3d]
            ys = [pt.y for pt in sec.pts3d]
            zs = [pt.z for pt in sec.pts3d]

            if show_points:
                ax.scatter(xs, ys, zs, color=plt.cm.jet(1 - sec.idx / len(self.sec_tree.sections)), s=5)
            if show_lines:
                ax.plot(xs, ys, zs, color=plt.cm.jet(1 - sec.idx / len(self.sec_tree.sections)))

            if annotate:
                ax.text(np.mean(xs), np.mean(ys), np.mean(zs), f'{sec.idx}', fontsize=8,
                        bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.3'))

        # Animation logic
        if animate:
            def update(frame):
                ax.view_init(elev=10., azim=frame * (360 / frames))  # Rotate over the total number of frames
                return ax,

            ani = FuncAnimation(fig, update, frames=frames, interval=interval, blit=False)

            if save_as_gif:
                print(f"Saving animation to {gif_filename}...")
                writer = PillowWriter(fps=1000 // interval, metadata=dict(artist="SWC Tree Visualization"))
                ani.save(gif_filename, writer=writer)
                plt.close(fig)  # Close the figure after saving
            else:
                plt.show()
        else:
            plt.show()







# VALIDATION FUNCTIONS

# Any tree

def check_nodes_match_root_subtree(tree):
    """
    Check if the root node is the parent of all other nodes.
    """
    tree._nodes == tree.root.subtree

def check_unique_ids(tree):
    node_ids = {node.idx for node in tree._nodes}
    if len(node_ids) != len(tree._nodes):
        raise ValueError("Tree contains duplicate node ids.")


def check_connections(tree):
    if not tree.is_connected:
        raise ValueError("Tree is not connected.")


def validate_parents(tree):
    """
    Validate the parent-child relationships in the tree.

    1. Check if all children are in the children list of their parent.
    2. Check if the parent of every child of a node is the node itself.
    """

    # 1. Check if all children are in the children list of their parent.
    for node in tree._nodes:
        parent = node.parent
        if (not parent is None) and (not node in parent.children):
            raise ValueError(
                f"Node {node} is missing in the children list of its parent {parent}."
            )

    # 2. Check if the parent of every child of a node is the node itself.
    for node in tree._nodes:
        for child in node.children:
            if child.parent is not node:
                raise ValueError(
                    f"Child node {child_node} has an incorrect parent. "
                    f"The parent is expected to be {node}, but found a different instance {child_node.parent}."
                )

# SEC tree

def validate_node_reference_to_section(tree):
    """
    Validate that each node references the section it belongs to (_section attribute).
    """
    for section in tree.sections:
        for pt in section.pts3d:
            if pt._section is not section:
                raise ValueError(
                    f"Node {pt} of section {section} has a different _section attribute than the section itself."
                )

# Trees match

def validate_sections_match(swc_tree, sec_tree):
    """
    Validate that the sections (partition) of the SWC tree match the sections (nodes) of the SEC tree.
    """
    if swc_tree._sections is not sec_tree.sections:
        raise ValueError(
            "The sections of the SWC tree do not match the sections of the SEC tree.")


def validate_points_match(swc_tree, sec_tree):
    """
    Ensure that the points (nodes) in the SWC tree correspond exactly to the 
    combined points within all sections of the SEC tree.
    """
    sec_tree_pts3d = [
        pt for sec in sec_tree.sections for pt in sec.pts3d]
    if not all(sec_pt is pt for sec_pt, pt in zip(sec_tree_pts3d, swc_tree.pts3d)):
        raise ValueError(
            "The pts3d of the SEC tree do not match the pts3d of the SWC tree.")

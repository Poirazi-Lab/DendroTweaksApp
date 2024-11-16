from ...trees import SWCNode, SWCTree, Section, SectionTree

import pandas as pd
from io import StringIO

# TODO: Think of the use cases.
# - Change soma notation (1PS, 3PS, contour)
# + Insert / remove sections / nodes
# - Update section diameter
# + Rotate the tree
# Do we really need to implement all of these?
# Given there is HBP Morphology Viewer.


class SWCManager():

    def __init__(self):
        self._df = None
        self.swc_tree = None
        self.sec_tree = None

    # READ

    def read(self, path_to_file=None, file_content=None):

        if path_to_file:
            self._path_to_file = path_to_file
            self.df = pd.read_csv(path_to_file,
                                  sep=' ',
                                  header=None,
                                  comment='#',
                                  names=['id', 'type', 'x', 'y', 'z', 'r', 'parent_id'])

        elif file_content:
            self._original_content = file_content
            self.df = pd.read_csv(StringIO(file_content),
                                  sep=' ',
                                  header=None,
                                  comment='#',
                                  names=['id', 'type', 'x', 'y', 'z', 'r', 'parent_id'])

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


# VALIDATION FUNCTIONS

# Any tree

def check_nodes_match_root_subtree(tree):
    """
    Check if the root node is the parent of all other nodes.
    """
    tree._nodes == tree.root._subtree

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

from collections import defaultdict
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from dendrotweaks.utils import timeit
from typing import Union

class Node():
    """
    Represents a node in a tree.

    A node can be a 3D point in a neuron morphology,
    a segment, a section, or even a tree.

    Parameters:
        idx (Union[int, str]): The index of the node.
        parent_idx (Union[int, str]): The index of the parent node.

    Examples:
        >>> node = Node(0, -1)
        >>> node
        •0
    """

    def __init__(self, idx: Union[int, str], parent_idx: Union[int, str]) -> None:
        """
        Creates a node in a tree.

        Args:
            idx (Union[int, str]): The index of the node.
            parent_idx (Union[int, str]): The index of the parent node.
        """
        self.idx = int(idx)
        self.parent_idx = int(parent_idx)
        self.parent = None
        self.children = []

    def __repr__(self):
        return f'•{self.idx}'

    @property
    def topological_type(self) -> str:
        """The topological type of the node based on the number of children.

        Returns:
            str: The topological type of the node: 'continuation', 'bifurcation', or 'termination'.
        """
        types = {0: 'termination', 1: 'continuation'}
        return types.get(len(self.children), 'bifurcation')

    @property
    def subtree(self) -> list:
        """
        Gets the subtree of the node (including the node itself).

        Returns:
            list: A list of nodes in the subtree.
        """
        subtree = [self]
        for child in self.children:
            subtree += child.subtree
        return subtree

    @property
    def subtree_size(self):
        """
        Gets the size of the subtree of the node.

        Returns:
            int: The size of the subtree of the node.
        """
        return len(self.subtree)

    @property
    def depth(self):
        """
        The depth of the node in the tree.

        Returns:
            int: The depth of the node in the tree.
        """
        if self.parent is None:
            return 0
        else:
            return self.parent.depth + 1

    @property
    def siblings(self):
        """
        Gets the siblings of the node.

        Returns:
            list: A list of nodes that share the same parent as the node.
        """
        if self.parent is None:
            return []
        return [child for child in self.parent.children if child is not self]


class Tree:
    """
    A class to represent a tree data structure.

    Args:
        nodes (List[Node]): A list of nodes in the tree.
    """

    def __init__(self, nodes: list) -> None:

        self._nodes = nodes
        self.root = self._find_root()

        if not self.is_connected:
            self._connect_nodes()

    # MAGIC METHODS

    def __repr__(self):
        return f'Tree {self._nodes}'

    def __getitem__(self, idx):
        return self._nodes[idx]

    def __len__(self):
        return len(self._nodes)

    def __iter__(self):
        for node in self._nodes:
            yield node

    def __contains__(self, node):
        return node in self._nodes

    # PROPERTIES

    @property
    def is_connected(self):
        """
        Checks if all nodes are connected to the root.

        Returns:
            bool: True if all nodes are reachable from the root, False otherwise.
        """
        return len(self._nodes) == len(self.root.subtree)

    @property
    def is_sorted(self):
        return all([node.idx == i for i, node in enumerate(self._nodes)])

    @property
    def bifurcations(self):
        return [node for node in self._nodes if len(node.children) > 1]

    @property
    def terminations(self):
        return [node for node in self._nodes if len(node.children) == 0]

    @property
    def edges(self) -> list:
        """
        Returns a list of edges in the tree.

        Returns:
            list[tuple[Node, Node]]: A list of edges in the tree.
        """
        edges = []
        for node in self._nodes:
            if node.parent is not None:
                edges.append((node.parent, node))
        return edges

    # TREE CONSTRUCTION METHODS

    def _find_root(self):
        """
        Finds the root node.

        Returns:
            Node: The root node of the tree.
        """
        ROOT_PARENT = {None, -1, '-1'}
        root_nodes = [node for node in self._nodes if node.parent_idx in ROOT_PARENT]

        if len(root_nodes) != 1:
            print('Root nodes:', root_nodes)
            raise ValueError('Tree must have exactly one root node.')

        return root_nodes[0]

    def _connect_nodes(self):
        """
        Builds the hierarchical tree structure for the nodes.

        For each node in `self._nodes`, find its parent node.
        Append the given node as a child to the parent node.
        Assign the parent node as the parent to the given node.
        """
        print('Connecting tree.')
        if self.is_connected:
            print('  Tree already connected.')
            return
        for node in self._nodes:
            if node is not self.root:
                for parent_node in self._nodes:
                    if node.parent_idx == parent_node.idx:
                        node.parent = parent_node
                        parent_node.children.append(node)
                        break
        
        if not self.is_connected:
            raise ValueError('Tree is not connected.')

    # TRAVERSAL METHODS

    def traverse(self):
        """
        Iterate over the nodes in the tree using a stack-based 
        depth-first traversal.
        """
        stack = [self.root]
        visited = set()

        while stack:
            node = stack.pop()
            if node in visited:
                continue

            yield node
            visited.add(node)
            for child in reversed(node.children):
                stack.append(child)

    # SORTIONG METHODS

    def _sort_children(self):
        """
        Iterate through all nodes in the tree and sort their children based on
        the number of bifurcations (nodes with more than one child) in each child's
        subtree. Nodes with fewer bifurcations in their subtrees are placed earlier in the list
        of the node's children, ensuring that the shortest paths are traversed first.

        Returns:
            None
        """
        for node in self._nodes:
            node.children = sorted(
                node.children, 
                key=lambda x: sum(1 for n in x.subtree if len(n.children) > 1),
                reverse=False
            )

    @timeit
    def sort(self, sort_children=True):
        """
        Sorts the nodes in the tree using a stack-based depth-first traversal.

        Args:
            sort_children (bool, optional): Whether to sort the children of each node 
            based on the number of bifurcations in their subtrees. Defaults to True.
        """
        if sort_children:
            self._sort_children()

        if self.is_sorted:
            print('Tree already sorted.')
            return

        count = 0
        for node in self.traverse():
            node.idx = count
            node.parent_idx = node.parent.idx if node.parent else -1
            count += 1

        self._nodes = sorted(self._nodes, key=lambda x: x.idx)

        if not self.is_sorted:
            raise ValueError('Tree is not sorted.')

    # INSERTION AND REMOVAL METHODS

    def _detach_node_from_parent(self, idx):
        """
        Detach a node from the tree.

        Parameters:
            idx (int): The index of the node to detach.
        """
        if not self.is_sorted:
            raise ValueError('Tree must be sorted to detach a node.')

        node = self._nodes[idx]
        if node.parent:
            node.parent.children.remove(node)
            node.parent = None
            node.parent_idx = -1

    def _attach_node_to_parent(self, node, parent_idx):
        """
        Attach a node to a parent in the tree.

        Args:
            node (Node): The node to attach.
            parent_idx (int): The index of the node to attach the new node to.

        Raises:
            ValueError: If the node is already in the parent's subtree.
        """
        parent = self._nodes[parent_idx]

        if node in parent.subtree:
            raise ValueError('Cannot attach a node to its own subtree.')

        if node.parent:
            node.parent.children.remove(node)

        node.parent = parent
        node.parent_idx = parent.idx
        parent.children = sorted(parent.children + [node], key=lambda x: x.idx)

    def insert_node(self, idx, new_node):
        """
        Insert a node at a given index in the tree.

        Args:
            idx (int): The index to insert the new node.
            new_node (Node): The node to insert.

        Raises:
            ValueError: If the node already exists in the tree.
            ValueError: If the tree is not sorted.
        """
        if new_node in self._nodes:
            raise ValueError('Node already exists in the tree.')
        if not self.is_sorted:
            raise ValueError('Tree must be sorted to insert a node.')

        new_node.idx = idx
        current_node = self._nodes[idx]
        parent = current_node.parent
        # Detach the current node from its parent
        self._detach_node_from_parent(idx)
        # Shift the indices of the following nodes by 1
        for i, node in enumerate(self._nodes[idx:], start=idx+1):
            node.idx = i
            node.parent_idx = node.parent.idx if node.parent else -1
        # Attach the new node to the parent of the current node
        self._attach_node_to_parent(new_node, parent.idx)
        # Insert the new node at the given index in the list of nodes
        self._nodes.insert(idx, new_node)
        # Attach the current node to the new node
        self._attach_node_to_parent(current_node, new_node.idx)

    def remove_subtree(self, idx):
        """
        Remove a node and its subtree from the tree.

        Args:
            idx (int): The index of the node to remove.

        Raises:
            ValueError: If the tree is not sorted.
        """
        if not self.is_sorted:
            raise ValueError('Tree must be sorted to remove a subtree.')

        subtree_root = self._nodes[idx]
        # Remove the node from its parent's children list
        if subtree_root.parent:
            subtree_root.parent.children.remove(subtree_root)
        # Remove the node and its subtree from the tree
        for node in subtree_root.subtree:
            self._nodes.remove(node)
        # Update the indices for the following nodes
        for i, node in enumerate(self._nodes[idx:], start=idx):
            node.idx = i
            node.parent_idx = node.parent.idx if node.parent else -1
        
    # VISUALIZATION METHODS

    def topology(self):
        """
        Print the topology of the tree with a visual tree structure.
        """
        def print_node(node, prefix="", is_last=True):
            """Recursive function to print the node with branches."""
            # Print the current
            root_str = f"{node.parent_idx:6} |   "
            prefix = root_str + prefix
            print(prefix + '•' + str(node.idx))

            # Handle the children nodes
            num_children = len(node.children)
            for i, child in enumerate(node.children):
                is_last_child = (i == num_children - 1)
                branch = "└─" if is_last_child else "├─"
                prefix = prefix.replace("└─", "  ").replace("├─", "│ ")
                prefix = prefix.replace(root_str, "")
                print_node(child, prefix + branch, is_last_child)

        # Assume the root node is the first in self._nodes
        print('parent |   idx')
        print('-'*15)
        print_node(self.root)

from collections import defaultdict
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from dendrotweaks.utils import timeit

# If you are using this approach leverage the use of the node class
# to attach relations to it. E.g. self._section


class Node():
    """
    A class to represent a node in a tree.
    A node can be a 3D point in a neuron morphology,
    a segment, a section or even a tree.

    Parameters:
    ----------
    idx : str
        The index of the node.
    parent_idx : str
        The index of the parent node.
    """

    def __init__(self, idx: str, parent_idx: str) -> None:
        self.idx = int(idx)
        self.parent_idx = int(parent_idx)
        self.parent = None
        self.children = []

    @property
    def topological_type(self):
        """
        Returns the topological type of the node.
        """
        if len(self.children) == 1:
            return 'continuation'
        elif len(self.children) > 1:
            return 'bifurcation'
        elif len(self.children) == 0:
            return 'termination'

    @property
    def _subtree(self) -> list:
        """
        Returns the subtree rooted at the node.

        Returns:
        --------
        List[Node]
            A list of nodes in the subtree.
        """
        subtree = [self]
        for child in self.children:
            subtree += child._subtree
        return subtree

    @property
    def _depth(self):
        """
        Returns the depth of the node in the tree.

        Returns:
        --------
        int
            The depth of the node in the tree.
        """
        if self.parent is None:
            return 0
        else:
            return self.parent._depth + 1

    # @property
    # def subtree(self):
    #     nodes = self._subtree
    #     nodes[0].parent = None
    #     return Tree(nodes)

    def __repr__(self):
        return f'•{self.idx}'

    # def __eq__(self, other):
    #     return self.idx == other.idx


class Tree:
    """
    A class to represent a tree data structure.

    Parameters:
    ----------
    nodes : List[Node]
        A list of nodes in the tree.
    """

    ROOT_PARENT = {None, -1, '-1'}

    def __init__(self, nodes: list) -> None:
        self._nodes = nodes
        self._count = 0

        # Validate and set the root node
        self.root = self._validate_nodes_and_find_root()

        # Ensure all nodes are connected
        if not self.is_connected:
            self._connect_nodes()

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

    def _validate_nodes_and_find_root(self):
        """
        Validates nodes, checks for duplicate IDs, and finds the root node.

        Returns:
        --------
        Node
            The root node of the tree.
        """
        unique_ids = set()
        root_nodes = []

        for node in self._nodes:
            # Check for IDs type (int or str)
            if not isinstance(node.idx, (int, str)):
                raise ValueError('Node ids must be integers or strings.')

            # Check for unique node IDs
            if node.idx in unique_ids:
                raise ValueError('Duplicate node ids found.')
            unique_ids.add(node.idx)

            # Check for node self-parenting
            if node.idx == node.parent_idx:
                raise ValueError(f'Node {node.idx} is its own parent.')

            # Identify root nodes
            if node.parent_idx in self.ROOT_PARENT:
                root_nodes.append(node)

        # Root node validation
        if len(root_nodes) > 1:
            raise ValueError('More than one root node found.')
        elif len(root_nodes) == 0:
            raise ValueError('No root node found.')

        return root_nodes[0]

    # @property
    # def nodes(self):
    #     return self._nodes

    @property
    def bifurcations(self):
        return [node for node in self._nodes if len(node.children) > 1]

    @property
    def terminations(self):
        return [node for node in self._nodes if len(node.children) == 0]

    @property
    def is_sorted(self):
        return all([node.idx == i for i, node in enumerate(self._nodes)])

    @property
    def is_connected(self):
        """
        Check if all nodes are connected to the root.

        Returns:
        --------
        bool
            True if a path exists from the root to all nodes, False otherwise. 
        """
        visited = set()

        def visit(node):
            if node.idx in visited:
                return
            visited.add(node.idx)
            for child in node.children:
                visit(child)

        visit(self.root)
        return len(visited) == len(self._nodes)

    @property
    @timeit
    def df(self):
        """
        Return the nodes in the tree as a pandas DataFrame.

        Returns:
        --------
        pd.DataFrame
            A DataFrame of the nodes in the tree.
        """
        # concatenate the dataframes of the nodes
        return pd.concat([node.df for node in self._nodes]).reset_index(drop=True)

    @property
    def edges(self) -> list:
        """
        Returns a list of edges in the tree.

        Returns:
        --------
        List[Tuple[Node, Node]]
            A list of edges in the tree.
        """
        edges = []
        for node in self._nodes:
            if node.parent is not None:
                edges.append((node.parent, node))
        return edges

    def _connect_nodes(self):
        """
        Builds the hierarchical tree structure for the nodes.

        For each node in `self._nodes`, find its parent node.
        To the parent node, append the given node as a child. 
        To the given node, assign the parent node as the parent.

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

    # TRAVERSAL METHODS

    def _traverse(self, node, pre_visit=None, post_visit=None):
        """
        Traverse the tree recursively in a depth-first manner.

        Parameters:
        ----------
        node : Node
            The node to start the traversal from.
        pre_visit : function
            A function to be executed before visiting the children of the node.
        post_visit : function
            A function to be executed after visiting the children of the node.
        """
        # TODO: Consider replacing with visitor pattern from is_connected

        if pre_visit:
            pre_visit(node)

        # On start
        ...

        children = node.children

        # On continuation
        if len(children) == 1:
            for child in children:
                self._traverse(child, pre_visit, post_visit)

        # On bifurcation
        if len(children) > 1:
            # for child in children:
            for i, child in enumerate(children):
                self._traverse(child, pre_visit, post_visit)

        # On termination
        if len(children) == 0:
            ...

        if post_visit:
            post_visit(node)

    # SORTING METHODS

    @timeit
    def sort(self, verbose=False):
        """
        Traverse the tree recursively in a depth-first manner.

        Parameters:
        ----------
        verbose : bool
            If True, print the traversal path.
        """
        self._count = 0

        def pre_visit(node, verbose=verbose):
            if verbose:
                print('  ' * node._depth + str(node) + '→' + str(self._count))
            node.idx = self._count
            node.parent_idx = node.parent.idx if node.parent else -1
            self._count += 1

        self._traverse(self.root, pre_visit=pre_visit)

    @timeit
    def sort2(self):
        """
        Sort the nodes in the tree using a stack-based depth-first traversal.
        """

        root = self.root
        stack = [root]
        visited = set()
        count = 0

        while stack:
            node = stack.pop()
            if node in visited:
                continue

            node.idx = count
            node.parent_idx = node.parent.idx if node.parent else -1
            count += 1

            visited.add(node)
            for child in sorted(node.children, key=lambda x: x.idx, reverse=True):
                stack.append(child)

    # INSERTION AND REMOVAL METHODS

    def remove_node(self, idx):
        """
        Remove a node from the tree.

        Parameters:
        ----------
        idx : int
            The index of the node to remove.
        """
        if not self.is_sorted:
            raise ValueError('Tree must be sorted to remove a node.')
        node = self._nodes[idx]
        subtree = node._subtree
        subtree_size = len(subtree)
        if node.parent:
            node.parent.children.remove(node)
        for node in subtree:
            self._nodes.remove(node)
            print(self._nodes)
        # Update the indices for the following nodes
        for i, node in enumerate(self._nodes[idx:], start=idx):
            node.idx = i
            node.parent_idx = node.parent.idx if node.parent else -1

    def detach_node(self, idx):
        """
        Detach a node from the tree.

        Parameters:
        ----------
        idx : int
            The index of the node to detach.
        """
        if not self.is_sorted:
            raise ValueError('Tree must be sorted to detach a node.')
        node = self._nodes[idx]
        if node.parent:
            node.parent.children.remove(node)
            node.parent = None
            node.parent_idx = -1

    def attach_node(self, node, parent_idx):
        """
        Attach a node to a parent in the tree.

        Parameters:
        ----------
        node : Node
            The node to attach.
        parent_idx : int
            The index of the node to attach the new node to.
        """
        parent = self._nodes[parent_idx]
        if node in parent._subtree:
            raise ValueError('Cannot attach a node to its own subtree.')
        if node.parent:
            node.parent.children.remove(node)
        node.parent = parent
        node.parent_idx = parent.idx
        parent.children = sorted(parent.children + [node], key=lambda x: x.idx)

    def insert_node(self, idx, new_node):
        """
        Insert a node at a given index in the tree.

        Parameters:
        ----------
        idx : int
            The index to insert the new node.
        new_node : Node
            The node to insert.
        """
        if new_node in self._nodes:
            raise ValueError('Node already exists in the tree.')
        if not self.is_sorted:
            raise ValueError('Tree must be sorted to insert a node.')

        new_node.idx = idx
        current_node = self._nodes[idx]
        parent = current_node.parent
        # Update the indices for the following nodes
        self.detach_node(idx)
        for i, node in enumerate(self._nodes[idx:], start=idx+1):
            node.idx = i
            node.parent_idx = node.parent.idx if node.parent else -1
        self.attach_node(new_node, parent.idx)
        self._nodes.insert(idx, new_node)
        self.attach_node(current_node, new_node.idx)
        
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

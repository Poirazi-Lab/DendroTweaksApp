from dendrotweaks.morphology.trees import Tree
from dendrotweaks.morphology.swc_trees import SWCTree
from dendrotweaks.morphology.sec_trees import SectionTree

import numpy as np


def validate_tree(tree):

    # Check for unique node ids
    check_unique_ids(tree)
    check_unique_root(tree)
    check_unique_children(tree)
    print(f"Tree has a unique root node {tree.root}")

    # Check for connectivity
    check_connections(tree)
    print("Tree is well connected")
    check_loops(tree)
    print("Tree has no loops")
    check_bifurcations(tree)
    print("Tree is binary (not considering the root node)")
    # validate_order(self.tree)


    if isinstance(tree, SWCTree):
        validate_swc_tree(tree)

    # Check if the tree is sorted
    if not tree.is_sorted:
        raise ValueError("Tree is not sorted")
    print("Tree is sorted")
    
    print("\nTree validation passed successfully")


# -----------------------------------------------------------------------------
# Indicies
# -----------------------------------------------------------------------------


def check_unique_ids(tree):
    node_ids = {node.idx for node in tree._nodes}
    if len(node_ids) != len(tree._nodes):
        raise ValueError(f"Tree contains {len(tree._nodes) - len(node_ids)} duplicate node ids.")


def check_unique_children(tree):
    for node in tree._nodes:
        children = node.children
        if len(children) != len(set(children)):
            raise ValueError(f"Node {node} contains duplicate children.")


def check_unique_root(tree):
    root_nodes = {node for node in tree._nodes
        if node.parent is None or node.parent_idx in {None, -1, '-1'}
    }
    if len(root_nodes) > 1:
        raise ValueError(f"Found {len(root_nodes)} root nodes.")
    if len(root_nodes) == 0:
        raise ValueError("Tree does not contain a root node.")


# -----------------------------------------------------------------------------
# Connectivity
# -----------------------------------------------------------------------------


def check_connections(tree):
    """
    Validate the parent-child relationships in the tree.

    1. Ensure that every node is listed as a child of its parent.
    2. Ensure that the parent of each child matches the node.
    """

    if not tree.is_connected:
        not_connected = set(tree._nodes) - set(tree.root.subtree)
        raise ValueError(f"The following nodes are not connected to the root node: {not_connected}")

    for node in tree._nodes:
        parent = node.parent
        
        # Validate that the node is in its parent's children list.
        if parent is not None:
            if node not in parent.children:
                raise ValueError(
                    f"Validation Error: Node {node} is not listed in the children of its parent {parent}. "
                    f"Expected parent.children to include {node}, but it does not."
                )

        # Validate that the parent of each child is the current node.
        for child in node.children:
            if child.parent is not node:
                raise ValueError(
                    f"Validation Error: Node {child} has an incorrect parent. "
                    f"Expected parent {node}, but found {child.parent}."
                )


def check_loops(tree):
    # Check for loops
    for node in tree._nodes:
        for descendant in node.subtree:
            if node in descendant.children:
                raise ValueError(f"Node {node} is a descendant of itself. Loop detected at node {descendant}.")


def check_bifurcations(tree):
    bifurcation_issues = {node: len(node.children) for node in tree.bifurcations if len(node.children) > 2 and node is not tree.root}
    if bifurcation_issues:
        issues_str = "\n".join([f"Node {node.idx:<6} has {count} children" for node, count in bifurcation_issues.items()])
        raise ValueError(f"Tree contains bifurcations with more than 2 children:\n{issues_str}")


# =============================================================================
# SWC-specific validation
# =============================================================================


def validate_swc_tree(swc_tree):

    # Check for NaN values in the DataFrame
    nan_counts = swc_tree.df.isnull().sum()
    if nan_counts.sum() > 0:
        raise ValueError(f"Found {nan_counts} NaN values in the DataFrame")

    # Check for bifurcations in the soma
    bifurcations_without_root = [pt for pt in swc_tree.bifurcations 
        if pt is not swc_tree.root]
    bifurcations_within_soma = [pt for pt in bifurcations_without_root
        if pt.type_idx == 1]
    if bifurcations_within_soma:
        raise ValueError(f"Soma must be non-branching. Found bifurcations: {bifurcations_within_soma}")

    if swc_tree._is_extended:
        non_overlapping_children = [
            (pt, child) for pt in bifurcations_without_root for child in pt.children
            if not child.overlaps_with(pt)
        ]
        if non_overlapping_children:
            issues_str = "\n".join([f"Child {child} does not overlap with parent {pt}" for pt, child in non_overlapping_children])
            raise ValueError(f"Found non-overlapping children:\n{issues_str} for bifurcations")
        


# =============================================================================
# Validation utilities
# =============================================================================


def shuffle_indices_for_testing(df):
    idx_range = int(df['Index'].max() - df['Index'].min()) + 1
    random_mapping = {k:v for k, v in zip(df['Index'], np.random.permutation(idx_range))}
    df['Index'] = df['Index'].map(random_mapping)
    df.loc[df['Parent'] != -1, 'Parent'] = df['Parent'].map(random_mapping)
    return df
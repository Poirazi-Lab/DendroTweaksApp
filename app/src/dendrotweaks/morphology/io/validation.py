from dendrotweaks.morphology.trees import Tree
from dendrotweaks.morphology.swc_trees import SWCTree
from dendrotweaks.morphology.sec_trees import SectionTree

import numpy as np


def validate_tree(tree):

    check_unique_ids(tree)
    check_unique_root(tree)
    check_connections(tree)
    # validate_parents(self.tree)
    # validate_order(self.tree)


    if isinstance(tree, SWCTree):
        validate_swc_tree(tree)
    
    print("Tree validation passed successfully")

def check_unique_ids(tree):
    node_ids = {node.idx for node in tree._nodes}
    if len(node_ids) != len(tree._nodes):
        raise ValueError("Tree contains duplicate node ids.")

def check_unique_root(tree):
    root_nodes = {node for node in tree._nodes
        if node.parent is None or node.parent_idx in {None, -1, '-1'}
    }
    if len(root_nodes) > 1:
        raise ValueError(f"Found {len(root_nodes)} root nodes.")
    if len(root_nodes) == 0:
        raise ValueError("Tree does not contain a root node.")

def check_connections(tree):
    # Check if the tree is connected
    if not tree.is_connected:
        not_connected = set(tree._nodes) - set(tree.root.subtree)
        raise ValueError(f"The following nodes are not connected to the root node: {not_connected}")
    # Check for loops
    for node in tree._nodes:
        for descendant in node.subtree:
            if node in descendant.children:
                raise ValueError(f"Node {node} is a descendant of itself. Loop detected at node {descendant}.")
    # Check for bifurcations with more than 2 children
    bifurcation_issues = {node: len(node.children) for node in tree.bifurcations if len(node.children) > 2 and node is not tree.root}
    if bifurcation_issues:
        issues_str = "\n".join([f"Node {node.idx:<6} has {count} children" for node, count in bifurcation_issues.items()])
        raise ValueError(f"Tree contains bifurcations with more than 2 children:\n{issues_str}")
            


def validate_swc_tree(swc_tree):

    # Check for NaN values in the DataFrame
    nan_counts = swc_tree.df.isnull().sum()
    if nan_counts.sum() > 0:
        raise ValueError(f"Found {nan_counts} NaN values in the DataFrame")









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


def shuffle_indices_for_testing(df):
    idx_range = int(df['Index'].max() - df['Index'].min()) + 1
    random_mapping = {k:v for k, v in zip(df['Index'], np.random.permutation(idx_range))}
    df['Index'] = df['Index'].map(random_mapping)
    df.loc[df['Parent'] != -1, 'Parent'] = df['Parent'].map(random_mapping)
    return df
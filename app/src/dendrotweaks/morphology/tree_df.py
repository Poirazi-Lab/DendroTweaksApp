import pandas as pd
import numpy as np


import pandas as pd
import numpy as np

import time

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print(f"{method.__name__} took: {round(te - ts, 3)} sec")
        return result
    return timed

class Tree:
    def __init__(self):
        self._df = None

    def from_swc(self, path_to_file):
        """
        Load tree structure from an SWC file.
        SWC format includes columns: idx, type, x, y, z, r, parent_idx.
        """
        self._df = pd.read_csv(
            path_to_file, sep=' ', header=None, comment='#',
            names=['idx', 'type', 'x', 'y', 'z', 'r', 'parent_idx']
        )
        # shuffle the rows
        self._df = self._df.sample(frac=1).reset_index(drop=True)

    @property
    def root(self):
        """
        Find the root node of the tree. Assumes that the parent index of -1 indicates the root.
        """
        root_nodes = self._df[self._df['parent_idx'] == -1]
        if root_nodes.empty:
            raise ValueError("No root node found. Ensure the tree is valid.")
        return root_nodes.iloc[0]  # Return the first root node
    
    @timeit
    def count_children(self):
        """
        Count the number of children for each node in the tree.
        """
        self._df['n_children'] = 0
        self._df['is_bifurcation'] = False
        self._df['is_bifurcation_child'] = False

        for idx, row in self._df.iterrows():
            parent_idx = row['parent_idx']
            if parent_idx == -1:
                continue

            self._df.loc[self._df['idx'] == parent_idx, 'n_children'] += 1
        
        self._df['is_bifurcation'] = self._df['n_children'] > 1
        self._df['is_bifurcation_child'] = self._df['parent_idx'].isin(self._df[self._df['is_bifurcation']]['idx'])

    @timeit
    def sort(self):
        """
        Perform a depth-first traversal of the tree, starting from the root.
        """
        if self._df is None:
            raise ValueError("Tree is empty. Load a tree using from_swc().")
        
        root_idx = int(self.root['idx'])
        print(f'Root: {root_idx}')

        stack = [root_idx]  # Initialize the stack with the root node
        visited = set()  # To keep track of visited nodes

        count = 0
        self._df['order'] = 0
        while stack:
            current_idx = stack.pop()
            if current_idx in visited:
                continue
            visited.add(current_idx)

            # Print the current node
            # print(f"Visiting node: {current_idx}")
            count += 1
            self._df.loc[self._df['idx'] == current_idx, 'order'] = count

            # Find and process children
            children = self._df[self._df['parent_idx'] == current_idx]
            for _, child in children.sort_values(by='idx', ascending=False).iterrows():
                stack.append(int(child['idx']))

        self._df = self._df.sort_values('order')
        self._df = self._df.drop(columns=['order'])
        self._df = self._df.reset_index(drop=True)

    @timeit
    def assign_sections(self):
        """
        Perform a depth-first traversal of the tree, starting from the root.
        """
        if self._df is None:
            raise ValueError("Tree is empty. Load a tree using from_swc().")
        
        root_idx = int(self.root['idx'])
        print(f'Root: {root_idx}')

        stack = [root_idx]  # Initialize the stack with the root node
        visited = set()  # To keep track of visited nodes

        section_idx = 0
        self._df['section_idx'] = 0
        while stack:
            current_idx = stack.pop()
            if current_idx in visited:
                continue
            visited.add(current_idx)

            # Print the current node
            # print(f"Visiting node: {current_idx}")
            self._df.loc[self._df['idx'] == current_idx, 'section_idx'] = section_idx

            # Find and process children
            children = self._df[self._df['parent_idx'] == current_idx]

            if children.empty:
                section_idx += 1
            elif len(children) > 1:
                section_idx += 1

            for _, child in children.sort_values(by='idx', ascending=False).iterrows():
                stack.append(int(child['idx']))

        self._assign_parents_to_sections()

    @timeit
    def _assign_parents_to_sections(self):
        """
        Assign parent section indices to each section.
        """
        # the idea is that the bifurcation child is the beginning of a section
        # we should take parent node of the bifurcation child, its section_idx will be the
        # parent_section_idx of each node in the given section
        self._df['parent_section_idx'] = -1

        for idx, row in self._df.iterrows():
            if row['is_bifurcation_child']:
                parent_idx = row['parent_idx']
                parent_section_idx = self._df[self._df['idx'] == parent_idx]['section_idx'].values[0]
                self._df.loc[self._df['section_idx'] == row['section_idx'], 'parent_section_idx'] = parent_section_idx
        
class Group():
    
    def __init__(self, df, node_ids):
        self._df = df
        self._node_ids = node_ids



        




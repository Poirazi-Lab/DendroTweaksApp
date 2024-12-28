from dendrotweaks.morphology.trees import Node, Tree
from dendrotweaks.morphology.swc_trees import SWCNode, SWCTree
from dendrotweaks.morphology.sec_trees import Section, SectionTree
from dendrotweaks.morphology.seg_trees import Segment, SegmentTree

from dendrotweaks.morphology.io.reader import SWCReader

from typing import List, Union
import numpy as np
from pandas import DataFrame

class TreeFactory():

    def __init__(self):
        
        self.reader = SWCReader()

    def create_swc_tree(self, source: Union[str, DataFrame]) -> SWCTree:
        """
        Creates an SWC tree from either a file path or a DataFrame.
        
        Parameters:
            source (str | pd.DataFrame): File path to the SWC file or a preprocessed DataFrame.
        """
        if isinstance(source, str):
            df = self.reader.read_file(source)
        elif isinstance(source, DataFrame):
            df = source
        else:
            raise ValueError("Source must be a file path (str) or a DataFrame.")

        nodes = [
            SWCNode(row['Index'], row['Type'], row['X'], row['Y'], row['Z'], row['R'], row['Parent'])
            for _, row in df.iterrows()
        ]
        return SWCTree(nodes)


    def create_sec_tree(self, swc_tree: SWCTree, extend: bool = True):
        """
        Creates a section tree from an SWC tree.

        Parameters
        ----------
        swc_tree : SWCTree
            The SWC tree to be partitioned into a section tree.
        extend : bool, optional
            Whether to extend the sections by adding a copy of the last node from the parent
            section to the beginning of the section. This ensures continuity between sections.
            Default is True.

        Returns
        -------
        SectionTree
            The section tree created from the SWC tree.
        """

        sections = self._create_sections(swc_tree, extend)

        sec_tree = SectionTree(sections)

        return sec_tree

    def _create_sections(self, swc_tree: SWCTree, extend: bool = True) -> List[Section]:

        sections = self._split_to_sections(swc_tree)

        if extend and not swc_tree._is_extended:
            nodes_before = len(swc_tree.pts3d)
            self._extend_sections(swc_tree=swc_tree, sections=sections)
            swc_tree._is_extended = True
            nodes_after = len(swc_tree.pts3d)
            print(f'Extended {nodes_after - nodes_before} nodes.')
        elif extend:
            print('Sections are already extended.')

        return sections

    def _split_to_sections(self, swc_tree: SWCTree) -> List[Section]:

        sections = []

        bifurcation_children = [
            child for b in swc_tree.bifurcations for child in b.children]
        bifurcation_children = [swc_tree.root] + bifurcation_children
        # bifurcation_children = sorted(bifurcation_children,
        #                               key=lambda x: x.idx)
        # Filter out the bifurcation children to enforce the original order
        bifurcation_children = [node for node in swc_tree._nodes 
                                if node in bifurcation_children]

        # Assign a section to each bifurcation child
        for i, child in enumerate(bifurcation_children):
            section = Section(idx=i, parent_idx=-1, pts3d=[child])
            sections.append(section)
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

        # Merge the soma into one section if it has 3PS notation
        if swc_tree.soma_notation == '3PS':
            sections = self._merge_soma(sections, swc_tree.soma_pts3d)

        return sections

    def _merge_soma(self, sections: List[Section], soma_pts3d: List[SWCNode]) -> List[Section]:
        """
        If soma has 3PS notation, merge it into one section.
        """
        
        root_pt = [pt for pt in soma_pts3d if not pt.parent][0]
        soma_pts3d.remove(root_pt)
        soma_pts3d.insert(1, root_pt)

        # Create a new section for the soma
        true_soma = root_pt._section
        true_soma.pts3d = soma_pts3d
        for node in soma_pts3d:
            node._section = true_soma

        # Identify soma sections and their indices
        soma_sections = [sec for sec in sections if any(pt.type_idx == 1 for pt in sec.pts3d)]
        soma_sections_ids = sorted(sec.idx for sec in soma_sections if sec != true_soma)

        # Remove the soma sections from the list
        for sec in soma_sections:
                sections.remove(sec)

        # Add the merged soma section at the beginning
        sections = [true_soma] + sections

        # Update the indices
        for sec in sections:
            # Shift index based on the number of soma sections removed before it
            shift = sum(1 for sid in soma_sections_ids if sid < sec.idx)
            sec.idx -= shift

            # Similarly adjust parent_idx
            if sec.parent_idx in soma_sections_ids:
                sec.parent_idx = 0  # Assign merged soma section as the parent
            else:
                shift = sum(1 for sid in soma_sections_ids if sid < sec.parent_idx)
                sec.parent_idx -= shift

        return sections

    def _extend_sections(self, sections: List[Section], 
                         swc_tree: SWCTree) -> List[Section]:
        """
        Extends the sections by adding a copy of the last node from the parent section
        to the beginning of the section. This ensures continuity between sections.

        Warning
        -------
        Mutates the input sections and the SWC tree.

        Notes
        -----
        - The method is implemented similarly to NEURON's approach to section extension.
        - For '3PS' notation, instead of the last point, it copies the second point of 
          the parent section (the root point).
        """

        soma = swc_tree.soma_pts3d[0]._section

        for sec in sections:
            if not sec.parent:
                continue
            first_node = sec.pts3d[0]
            if sec.parent is soma:
                if len(sec.pts3d) > 1:
                    continue # do not extend the soma children in general
                if swc_tree.soma_notation == '3PS':
                    node_to_copy = sec.parent.pts3d[1]
                else:
                    node_to_copy = sec.parent.pts3d[-1]
            node_to_copy = sec.parent.pts3d[-1]
            # Compare coordinates to avoid duplication
            if np.allclose([first_node.x, first_node.y, first_node.z], 
                           [node_to_copy.x, node_to_copy.y, node_to_copy.z], 
                           atol=1e-8):
                continue
            new_node = node_to_copy.copy()
            # Copy SWC-specific attributes
            new_node.type_idx = first_node.type_idx
            new_node._section = first_node._section
            # Insert the new node at the beginning of the section
            swc_tree.insert_node(first_node.idx, new_node)
            sec.pts3d.insert(0, new_node)

        return sections
        

    def create_seg_tree(self, sec_tree):

        segments = self._create_segments(sec_tree)

        seg_tree = SegmentTree(segments)

        return seg_tree
        
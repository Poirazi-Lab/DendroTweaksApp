from dendrotweaks.morphology.trees import Node, Tree
from dendrotweaks.morphology.swc_trees import SWCNode, SWCTree
from dendrotweaks.morphology.sec_trees import Section, SectionTree
from dendrotweaks.morphology.seg_trees import Segment, SegmentTree

from dendrotweaks.morphology.io.reader import SWCReader

from typing import List, Union
import numpy as np
from pandas import DataFrame

from dendrotweaks.morphology.io.validation import validate_tree

class TreeFactory():

    def __init__(self):
        
        self.reader = SWCReader()

    def create_swc_tree(self, source: Union[str, DataFrame], 
                        standardize:bool = True) -> SWCTree:
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
        swc_tree =  SWCTree(nodes)
        if standardize:
            self._convert_to_3PS_notation(swc_tree)
        return swc_tree

    def _convert_to_3PS_notation(self, swc_tree):
        """
        Convert the soma to 3PS notation.
        """
        if swc_tree.soma_notation == '3PS':
            return

        if swc_tree.soma_notation == '1PS':

            pt = swc_tree.soma_pts3d[0]

            pt_left = SWCNode(
                idx=1,
                type_idx=1,
                x=pt.x - pt.r,
                y=pt.y,
                z=pt.z,
                r=pt.r,
                parent_idx=pt.idx)

            pt_right = SWCNode(
                idx=2,
                type_idx=1,
                x=pt.x + pt.r,
                y=pt.y,
                z=pt.z,
                r=pt.r,
                parent_idx=pt.idx)

            swc_tree.add_subtree(pt_right, pt)
            swc_tree.add_subtree(pt_left, pt)
            
        elif swc_tree.soma_notation =='contour':
            # if soma has contour notation, take the average
            # distance of the nodes from the center of the soma
            # and use it as radius, create 3 new nodes
            raise NotImplementedError('Conversion from contour to 3PS notation is not implemented yet.')

        print('Converted soma to 3PS notation.')


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
        sec_tree._swc_tree = swc_tree

        return sec_tree


    def _create_sections(self, swc_tree: SWCTree, extend: bool = True) -> List[Section]:

        if extend and not swc_tree._is_extended:
            nodes_before = len(swc_tree.pts3d)
            self._extend_sections(swc_tree)
            nodes_after = len(swc_tree.pts3d)
            print(f'Extended {nodes_after - nodes_before} nodes.')
            swc_tree.sort()
        elif extend:
            print('Sections are already extended.')

        sections = self._split_to_sections(swc_tree)

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


        sections = self._merge_soma(sections, swc_tree)

        return sections


    def _merge_soma(self, sections: List[Section], swc_tree: SWCTree):
        """
        If soma has 3PS notation, merge it into one section.
        """

        if swc_tree.soma_notation != '3PS':
            raise ValueError('Soma notation must be 3PS to merge the soma.')

        true_soma = swc_tree.root._section
        true_soma.idx = 0
        true_soma.parent_idx = -1

        false_somas = [sec for sec in sections 
            if sec.domain == 'soma' and sec is not true_soma]
        if len(false_somas) != 2:
            print(false_somas)
            raise ValueError('Soma must have exactly 2 children of domain soma.')

        for i, sec in enumerate(false_somas):
            sections.remove(sec)
            if len(sec.pts3d) != 1:
                raise ValueError('Soma children must have exactly 1 point.')
            for pt in sec.pts3d:
                pt._section = true_soma

        true_soma.pts3d = [
            false_somas[0].pts3d[0], 
            true_soma.pts3d[0], 
            false_somas[1].pts3d[0]
        ]

        for sec in sections:
            if sec is true_soma:
                continue
            sec.idx -= 2
            sec.parent_idx = sec.pts3d[0].parent._section.idx
            

        return sections

    # def _extend_sections(self, sections: List[Section], 
    #                      swc_tree: SWCTree) -> List[Section]:
    #     """
    #     Extends the sections by adding a copy of the last node from the parent section
    #     to the beginning of the section. This ensures continuity between sections.

    #     Warning
    #     -------
    #     Mutates the input sections and the SWC tree.

    #     Notes
    #     -----
    #     - The method is implemented similarly to NEURON's approach to section extension.
    #     - For '3PS' notation, instead of the last point, it copies the second point of 
    #       the parent section (the root point).
    #     """

    #     soma = swc_tree.soma_pts3d[0]._section

    #     for sec in sections:
    #         if not sec.parent:
    #             continue
    #         first_node = sec.pts3d[0]
    #         if sec.parent is soma:
    #             if len(sec.pts3d) > 1:
    #                 continue # do not extend the soma children in general
    #             if swc_tree.soma_notation == '3PS':
    #                 node_to_copy = sec.parent.pts3d[1]
    #             else:
    #                 node_to_copy = sec.parent.pts3d[-1]
    #         node_to_copy = sec.parent.pts3d[-1]
    #         # Compare coordinates to avoid duplication
    #         if np.allclose([first_node.x, first_node.y, first_node.z], 
    #                        [node_to_copy.x, node_to_copy.y, node_to_copy.z], 
    #                        atol=1e-8):
    #             continue
    #         new_node = node_to_copy.copy()
    #         # Copy SWC-specific attributes
    #         new_node.type_idx = first_node.type_idx
    #         new_node._section = first_node._section
    #         # Insert the new node at the beginning of the section
    #         swc_tree.insert_node(first_node.idx, new_node)
    #         sec.pts3d.insert(0, new_node)

    #     return sections


    def _extend_sections(self, swc_tree: SWCTree):

        bifurcations_without_root = [
            b for b in swc_tree.bifurcations if b != swc_tree.root
        ]

        for pt in bifurcations_without_root:
            children = pt.children[:]
            for child in children:
                # Compare coordinates to avoid duplication
                if np.allclose([child.x, child.y, child.z], 
                               [pt.x, pt.y, pt.z], 
                               atol=1e-8):
                    continue
                new_node = pt.copy()
                swc_tree.insert_node_before(new_node, child)

        swc_tree._is_extended = True


    def create_seg_tree(self, sec_tree):

        segments = self._create_segments(sec_tree)

        seg_tree = SegmentTree(segments)
        sec_tree._seg_tree = seg_tree

        return seg_tree


    def _create_segments(self, sec_tree) -> List[Segment]:

        """
        Build the segment tree using the section tree.
        """
        # self.set_geom_nseg(d_lambda, f)

        segments = []  # To store Segment objects

        def add_segments(sec, parent_idx, idx_counter):
            segs = {seg: idx + idx_counter for idx, seg in enumerate(sec._ref)}

            sec.segments = []
            # Add each segment of this section as a Segment object
            for seg, idx in segs.items():
                # Create a Segment object with the parent index
                segment = Segment(
                    idx=idx, parent_idx=parent_idx, neuron_seg=seg, section=sec)
                segments.append(segment)
                sec.segments.append(segment)

                # Update the parent index for the next segment in this section
                parent_idx = idx

            # Update idx_counter for the next section
            idx_counter += len(segs)

            # Recursively add child sections
            for child in sec.children:
                # IMPORTANT: This is needed since 0 and 1 segments are not explicitly
                # defined in the section segments list
                if child._ref.parentseg().x == 1:
                    new_parent_idx = list(segs.values())[-1]
                elif child._ref.parentseg().x == 0:
                    new_parent_idx = list(segs.values())[0]
                else:
                    new_parent_idx = segs[child._ref.parentseg()]
                # Recurse for the child section
                idx_counter = add_segments(child, new_parent_idx, idx_counter)

            return idx_counter

        # Start with the root section of the sec_tree
        add_segments(sec_tree.root, parent_idx=-1, idx_counter=0)

        return segments
        
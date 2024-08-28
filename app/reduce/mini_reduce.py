from neuron import h
from neuron.units import mV, ms
import neuron
import matplotlib.pyplot as plt
import numpy as np
import re

import collections
import itertools as it
import logging
import math
import re
import cmath

from reduce.subtree_reductor_func import CableParams
from reduce.subtree_reductor_func import calculate_nsegs_from_manual_arg, calculate_nsegs_from_lambda
from reduce.reducing_methods import reduce_subtree as get_unique_cable_properties
from reduce.reducing_methods import measure_input_impedance_of_subtree, find_best_real_X
from reduce.reducing_methods import push_section

EXCLUDE_MECHANISMS = ['leak', 'na_ion', 'k_ion', 'ca_ion', 'h_ion', 'ttx_ion', 'leak']


def match_name(func):
    def wrapper(sec):
        name = sec.name()

        if not '[' in name:
            name = f'{name}[0]'

        match = re.search(
            r"(([A-Za-z]+)\[(\d+)\])?\.?(([A-Za-z]+)\[(\d+)\])", name)

        return func(match)
    return wrapper


@match_name
def get_sec_name(match):
    return match.group(4)


@match_name
def get_sec_type(match):
    return match.group(5)


@match_name
def get_sec_id(match):
    return match.group(6)

def get_seg_name(seg):
    return get_sec_name(seg.sec) + f'({seg.x})'

# Mapping
def map_orig_seg_names_to_params(subtree):
    """Maps segment names from the original subtree to their parameters.

    This function takes a list of sections representing a subtree and 
    returns a dictionary that maps segment names to their parameters. 

    This dictionary is used later to restore the active conductances 
    in the reduced cylinder.
    """
    orig_seg_names_to_params = {}
    for sec in subtree:
        for seg in sec:
            seg_name = get_seg_name(seg)
            orig_seg_names_to_params[seg_name] = {}
            for mech in seg:
                if not mech.name().endswith('_ion'):
                    mech_name = mech.name()
                    orig_seg_names_to_params[seg_name][mech_name] = {}
                    for k in mech.__dict__.keys():
                        orig_seg_names_to_params[seg_name][mech_name][k + f'_{mech}'] = getattr(seg, k + f'_{mech}')
    return orig_seg_names_to_params

def remove_active_mechs(subtree):
    """Removes all mechanisms from a subtree except for the passive mechanism.

    This function takes a list of sections representing a subtree and removes all active
    mechanisms. The passive mechanisms are kept because ...
    """
    for sec in subtree:
        with push_section(sec):
            for seg in sec:
                for mech in seg:
                    mech_name = mech.name()
                    if sec.has_membrane(mech_name) and not mech_name in EXCLUDE_MECHANISMS:
                        sec.uninsert(mech_name)
                        # print(f'From section: {get_sec_name(sec)} removed: {mech_name}')

def calculate_nsegs(new_cable_properties, total_segments_manual):

    new_cable_properties = [new_cable_properties]

    if total_segments_manual > 1:
        print('the number of segments in the reduced model will be set to `total_segments_manual`')
        new_cables_nsegs = calculate_nsegs_from_manual_arg(new_cable_properties,
                                                           total_segments_manual)
    else:
        new_cables_nsegs = calculate_nsegs_from_lambda(new_cable_properties)
        if total_segments_manual > 0:
            print('from lambda')
            original_cell_seg_n = (sum(i.nseg for i in list(original_cell.basal)) +
                                   sum(i.nseg for i in list(
                                       original_cell.apical))
                                   )
            min_reduced_seg_n = int(
                round((total_segments_manual * original_cell_seg_n)))
            if sum(new_cables_nsegs) < min_reduced_seg_n:
                logger.debug(f"number of segments calculated using lambda is {sum(new_cables_nsegs)}, "
                             "the original cell had {original_cell_seg_n} segments.  "
                             "The min reduced segments is set to {total_segments_manual * 100}% of reduced cell segments")
                logger.debug("the reduced cell nseg is set to %s" %
                             min_reduced_seg_n)
                new_cables_nsegs = calculate_nsegs_from_manual_arg(new_cable_properties,
                                                                   min_reduced_seg_n)
        else:
            # print('Automatic segmentation')
            pass

    return new_cables_nsegs[0]


def calculate_subtree_q(root, reduction_frequency):
    rm = 1.0 / root.gbar_leak
    rc = rm * (float(root.cm) / 1000000)
    angular_freq = 2 * math.pi * reduction_frequency
    q_imaginary = angular_freq * rc
    q_subtree = complex(1, q_imaginary)   # q=1+iwRC
    q_subtree = cmath.sqrt(q_subtree)
    return q_subtree


def reduce_segment(seg,
                   imp_obj,
                   root_input_impedance,
                   new_cable_electrotonic_length,
                   subtree_q):

    # measures the original transfer impedance from the synapse to the
    # somatic-proximal end in the subtree root section
    sec = seg.sec

    with push_section(sec):
        orig_transfer_imp = imp_obj.transfer(seg.x) * 1000000  # ohms
        orig_transfer_phase = imp_obj.transfer_phase(seg.x)
        # creates a complex Impedance value with the given polar coordinates
        orig_transfer_impedance = cmath.rect(
            orig_transfer_imp, orig_transfer_phase)

    # synapse location could be calculated using:
    # X = L - (1/q) * arcosh( (Zx,0(f) / ZtreeIn(f)) * cosh(q*L) ),
    # derived from Rall's cable theory for dendrites (Gal Eliraz)
    # but we chose to find the X that will give the correct modulus. See comment about L values

    new_electrotonic_location = find_best_real_X(root_input_impedance,
                                                 orig_transfer_impedance,
                                                 subtree_q,
                                                 new_cable_electrotonic_length)
    new_relative_loc_in_section = (float(new_electrotonic_location) /
                                   new_cable_electrotonic_length)

    if new_relative_loc_in_section > 1:  # PATCH
        new_relative_loc_in_section = 0.999999

    return new_relative_loc_in_section


def map_orig_seg_names_to_locs(root, reduction_frequency, new_cable_properties):
    """Maps segment names of the original subtree 
    to their new locations in the reduced cylinder.

    This dictionary is used later to restore 
    the active conductances in the reduced cylinder.
    """
    orig_seg_names_to_locs = {}

    imp_obj, subtree_input_impedance = measure_input_impedance_of_subtree(root,
                                                                        reduction_frequency)
    subtree_q = calculate_subtree_q(root, reduction_frequency)

    for sec in root.subtree():
        for seg in sec:

            seg_name = get_seg_name(seg)

            mid_of_segment_loc = reduce_segment(seg,
                                                imp_obj,
                                                subtree_input_impedance,
                                                new_cable_properties.electrotonic_length,
                                                subtree_q)

            orig_seg_names_to_locs[seg_name] = mid_of_segment_loc

    return orig_seg_names_to_locs


def apply_params_to_section(section, cable_params, nseg):
    section.L = cable_params.length
    section.diam = cable_params.diam
    section.nseg = nseg

    section.insert('leak')
    section.cm = cable_params.cm
    section.gbar_leak = 1.0 / cable_params.rm
    section.Ra = cable_params.ra
    section.e_leak = cable_params.e_leak


def connect_section(section, parentseg):
    section.connect(parentseg.sec(parentseg.x), 0)
    # print('Connected ', sec_name, '→', parent_sec_name)

def replace_locs_with_reduced_segs(orig_seg_names_to_locs, root):
    """Replaces the locations (x values) 
    with the corresponding segments of the reduced cylinder i.e. sec(x).
    """
    orig_seg_names_to_reduced_segs = {k: root(v)
                                 for k, v in orig_seg_names_to_locs.items()}
    return orig_seg_names_to_reduced_segs


def map_reduced_segs_to_params(orig_seg_names_to_reduced_segs, orig_segs_names_to_params):
    reduced_segs_to_params = {}
    for original_seg_name, reduced_seg in orig_seg_names_to_reduced_segs.items():
        if reduced_seg not in reduced_segs_to_params:
            reduced_segs_to_params[reduced_seg] = collections.defaultdict(list)
        for mech_name, mech_params in orig_segs_names_to_params[original_seg_name].items():
            for param_name, param_value in mech_params.items():
                reduced_segs_to_params[reduced_seg][param_name].append(param_value)
            if not reduced_seg.sec.has_membrane(mech_name):
                reduced_seg.sec.insert(mech_name)
    return reduced_segs_to_params


def set_avg_params_to_reduced_segs(reduced_segs_to_params):
    for reduced_seg, params in reduced_segs_to_params.items():
        for param_name, param_values in params.items():
            setattr(reduced_seg, param_name, np.mean(param_values))


def interpolate_missing_values(reduced_segs_to_params, root):
    non_mapped_segs = [seg for seg in root if seg not in reduced_segs_to_params]
    xs = np.array([seg.x for seg in root])
    non_mapped_indices = np.where([seg in non_mapped_segs for seg in root])[0]
    mapped_indices = np.where([seg not in non_mapped_segs for seg in root])[0]
    print(f'Interpolated for ids {non_mapped_indices}')
    for param in list(set([k for val in reduced_segs_to_params.values() for k in val.keys()])):
        values = np.array([getattr(seg, param) for seg in root])
        if np.any(values != 0.) and np.any(values == 0.):
            # Find the indices where param value is zero
            # zero_indices = np.where(values == 0)[0]
            # Interpolate the values for these indices
            # values[zero_indices] = np.interp(xs[zero_indices], xs[values != 0], values[values != 0], left=0, right=0)
            values[non_mapped_indices] = np.interp(xs[non_mapped_indices], xs[mapped_indices], values[mapped_indices], left=0, right=0)
            print(f'     {param} values: {values}')
            # Set the values
            for x, value in zip(xs, values):
                setattr(root(x), param, value)


def remove_intermediate_pts3d(sec):
    while sec.n3d() > 2:
        sec.pt3dremove(1)


def reduce_subtree(cell, root, reduction_frequency = 0, total_segments_manual=-1):

    # subtree_without_root = list(set(root.subtree()).difference(set([root])))
    subtree_without_root = [sec for sec in root.subtree() if sec != root]

    # Map original segment names to their parameters
    orig_seg_names_to_params = map_orig_seg_names_to_params(root.subtree())
    # Question: do we need active mechs to calculate cable properties?
    remove_active_mechs(root.subtree())

    # Find the parenseg and disconnect the subtree
    parentseg = root.parentseg()
    assert root.parentseg
    h.disconnect(sec=root)

    # Calculate new properties of a reduced subtree
    new_cable_properties = get_unique_cable_properties(root, frequency=reduction_frequency)
    new_nseg = calculate_nsegs(new_cable_properties, total_segments_manual)

    # Map original segment names to their new locations in the reduced cylinder
    orig_seg_names_to_locs = map_orig_seg_names_to_locs(root, 
                                          reduction_frequency, 
                                          new_cable_properties)

    # Set passive mechanisms for the reduced cylinder:
    apply_params_to_section(section=root,
                            cable_params=new_cable_properties,
                            nseg=new_nseg)

    # Connect the reduced cylinder back:
    connect_section(section=root,
                    parentseg=parentseg)

    # Replace locations with corresponding segments:
    orig_seg_names_to_reduced_segs = replace_locs_with_reduced_segs(orig_seg_names_to_locs,
                                                   root)

    # Map reduced segments to lists of parameters of corresponding original segments:
    reduced_segs_to_params = map_reduced_segs_to_params(orig_seg_names_to_reduced_segs,
                                                    orig_seg_names_to_params)

    # Copy active mechanisms to the reduced cylinder and interpolate values for non-mapped segments:
    set_avg_params_to_reduced_segs(reduced_segs_to_params)
    interpolate_missing_values(reduced_segs_to_params, root)

    # Delete original subtree
    for sec in subtree_without_root:
        getattr(cell, get_sec_type(sec)).remove(sec)
        cell.all.remove(sec)
        with push_section(sec):
            h.delete_section()

    # Update pts3d

    # ps = h.PlotShape(False)  # False tells h.PlotShape not to use NEURON's gui
    # ps.plot(plt)
    # plt.show()

    remove_intermediate_pts3d(root)


def reduce_cell(cell, roots, reduction_frequency=0, total_segments_manual=-1):
    print('Reducing ', cell)
    for root in roots:
        reduce_subtree(cell,
                       root,
                       reduction_frequency=reduction_frequency,
                       total_segments_manual=total_segments_manual)
        print('    reduced', get_sec_name(root), 'subtree')
    print('Reduction completed')

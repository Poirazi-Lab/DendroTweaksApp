import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.signal import find_peaks, peak_widths
from scipy.optimize import curve_fit


# =============================================================================
# MORPHOLOGY
# =============================================================================

def get_node_data(nodes):

    data = {
        'idx': [node.idx for node in nodes],
        'length': [node.length for node in nodes],
        'diam': [node.diam for node in nodes],
        'area': [node.area for node in nodes],
        'n_children': [len(node.children) for node in nodes]
    }

    return pd.DataFrame(data)


def calculate_section_statistics(sections, param_name=None):
    
    df = get_node_data(sections)

    stats = {
        'N_sections': len(df),
        'N_bifurcations': (df['n_children'] == 2).sum(),
        'N_terminations': (df['n_children'] == 0).sum(),
        'diam': {
            'min': np.round(df['diam'].min(), 2),
            'max': np.round(df['diam'].max(), 2),
            'mean': np.round(df['diam'].mean(), 2),
            'std': np.round(df['diam'].std(), 2)
        },
        'length': {
            'min': np.round(df['length'].min(), 2),
            'max': np.round(df['length'].max(), 2),
            'mean': np.round(df['length'].mean(), 2),
            'std': np.round(df['length'].std(), 2)
        },
        'area': {
            'min': np.round(df['area'].min(), 2),
            'max': np.round(df['area'].max(), 2),
            'mean': np.round(df['area'].mean(), 2),
            'std': np.round(df['area'].std(), 2)
        },
        'total_length': np.round(df['length'].sum(), 2),
        'total_area': np.round(df['area'].sum(), 2)
    }

    return stats


def calculate_cell_statistics(model):

    all_sections = []
    for domain in model.domains:
        all_sections.extend(domain.sections)

    return calculate_section_statistics(all_sections)


def calculate_domain_statistics(model, domain_names=None, param_name=None):

    if domain_names is None:
        return calculate_cell_statistics(model)
    if not isinstance(domain_names, list):
        raise ValueError("domain_names must be a list of strings")

    domains = [domain for domain in model.domains.values() if domain.name in domain_names]

    stats = {}

    for domain in domains:
        stats[domain.name] = calculate_section_statistics(domain.sections)

    return stats
        

def calculate_segment_statistics(self, segments):

    df = self.get_node_data(segments)

    stats = {
        'N_segments': len(df),
        'N_bifurcations': (df['n_children'] == 2).sum(),
        'N_terminations': (df['n_children'] == 0).sum(),
        'diam': (np.round(df['diam'].mean(), 2), np.round(df['diam'].std(), 2), np.round(df['diam'].min(), 2), np.round(df['diam'].max(), 2)),
        'length': (np.round(df['length'].mean(), 2), np.round(df['length'].std(), 2), np.round(df['length'].min(), 2), np.round(df['length'].max(), 2)),
        'area': (np.round(df['area'].mean(), 2), np.round(df['area'].std(), 2), np.round(df['area'].min(), 2), np.round(df['area'].max(), 2)),
        'total_lenght': np.round(df['length'].sum(), 2),
        'total_area': np.round(df['area'].sum(), 2)
    }


def update_histogram(self, param_name, segments, **kwargs):
    if param not in ['diam', 'length', 'area']:
        raise ValueError(f"Invalid parameter: {param}")
    values = [seg.get_param_value(param_name) for seg in segments]
    hist, edges = np.histogram(values, **kwargs)
    return hist, edges



# =============================================================================
# ELECTROPHYSIOLOGY
# =============================================================================

def detect_somatic_spikes(model):
    
    seg = model.seg_tree.root

    if model.simulator.recordings.get(seg):
        v = np.array(model.simulator.recordings[seg].to_python())
        t = np.array(model.simulator.t)

    peaks, _ = find_peaks(v, height=0, distance=10)
    widths, heights, left_ips, right_ips = peak_widths(v, peaks, rel_height=0.5)
    _dt = model.simulator.dt
    widths = widths * _dt
    amplitudes = 2 * (v[peaks] - heights)
    print(f"Detected {len(peaks)} spikes")
    print(f"Average spike width: {np.mean(widths):.2f} ms")
    print(f"Average spike amplitude: {np.mean(amplitudes):.2f} mV")
    print(f"Average spike frequency: {len(peaks) / (t[-1] - t[0]) * 1000:.2f} Hz")
    return t[peaks], v[peaks], widths, amplitudes


def plot_spikes(model, ax=None):

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 2))

    t, v, _, _ = detect_somatic_spikes(model)
    ax.plot(t, v, 'o', color='red')
    ax.set_xlabel('Time (ms)')
    ax.set_ylabel('Amplitude (mV)')
    ax.set_title('Somatic spikes')
    
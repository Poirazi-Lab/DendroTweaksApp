# SPDX-FileCopyrightText: 2025 Poirazi Lab <dendrotweaks@dendrites.gr>
# SPDX-License-Identifier: MPL-2.0

import numpy as np
from bokeh.models import Range1d

from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

from dendrotweaks.analysis import detect_somatic_spikes
from dendrotweaks.analysis import calculate_passive_properties
from dendrotweaks.analysis import calculate_fI_curve
from dendrotweaks.analysis import calculate_voltage_attenuation
from dendrotweaks.analysis import calculate_dendritic_nonlinearity

from dendrotweaks.analysis import calculate_cell_statistics
from dendrotweaks.analysis import calculate_domain_statistics
from dendrotweaks.analysis.morphometric_analysis import calculate_section_statistics

PROTOCOL_DESCRIPTIONS = {
    'Input resistance and time constant': """<ol>
    <li>Place a recording at the soma.</li>
    <li>Inject a hyperpolarizing current into the cell.</li>
    <li>Click "Run protocol" button.</li>
    </ol>""",
    'Somatic spikes': """<ol>
    <li>Place a recording at the soma.</li>
    <li>Inject a depolarizing current into the cell.</li>
    <li>Click "Run protocol" button.</li>
    </ol>""",
    'Voltage attenuation': """<ol>
    <li>Place several recordings at different locations in the cell.</li>
    <li>Inject a hyperpolarizing current at one of the locations.</li>
    <li>Click "Run protocol" button.</li>
    </ol>""",
    'f-I curve': """<ol>
    <li>Place a recording at the soma.</li>
    <li>Inject a depolarizing current at the soma.</li>
    <li>Specify the range of injected current amplitudes to test (minimum and maximum).</li>
    <li>Specify the number of current amplitudes to test (up to 10)</li>
    <li>Click "Run protocol" button.</li>
    </ol>""",
    'Dendritic nonlinearity': """<ol>
    <li>Place a recording at a dendritic location.</li>
    <li>Place a single synapse at the same location.</li>
    <li>Specify the maximum synaptic weight. The minimum weight is 1.</li>
    <li>Specify the number of synaptic weights to test (up to 10).</li>
    <li>Click "Run protocol" button.</li>
    </ol>""",
    'Sag ratio': """<ol>
    <li>Place a recording at the soma.</li>
    <li>Inject a hyperpolarizing current into the cell.</li>
    <li>Click "Run protocol" button.</li>
    </ol>""",
}

class ValidationMixin(): 

    def __init__(self):
        logger.debug('NavigationMixin init')
        super().__init__()   

    def clear_validation_callback(self, event):
        self._clear_validation()

    def _clear_validation(self):
        self.view.sources['stats_ephys'].data = {'x': [], 'y': []}
        self.view.sources['stats_ephys_extra'].data = {'x': [], 'y': []}
        self.view.sources['detected_spikes'].data = {'x': [], 'y': []}
        self.view.sources['frozen_v'].data = {'xs': [], 'ys': []}
        self.view.widgets.switches['frozen_v'].active = False
        self.view.figures['stats_ephys'].visible = False
        self.view.DOM_elements['stats_ephys'].text = "Data cleared. Select a protocol to validate."
        if not self.view.DOM_elements['status'].text.startswith('Select'):
            self.update_status_message('Idle.', 'info')


    def select_protocol_callback(self, attr, old, new):
        
        self._clear_validation()
        self.view.DOM_elements['stats_ephys'].text = PROTOCOL_DESCRIPTIONS[new]
        self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['info']
        if new == 'f-I curve':
            self.view.DOM_elements['protocol_widgets'].visible = True
            self.view.widgets.numeric['protocol_min'].disabled = False
            self.view.widgets.numeric['protocol_min'].value = 0.1
            self.view.widgets.numeric['protocol_max'].value = 0.2
            self.view.widgets.numeric['protocol_n'].value = 5
            self.view.widgets.numeric['protocol_max'].title = 'Max current, nA'
            self.view.widgets.numeric['protocol_min'].title = 'Min current, nA'
        elif new == 'Dendritic nonlinearity':
            self.view.DOM_elements['protocol_widgets'].visible = True
            self.view.widgets.numeric['protocol_min'].disabled = True
            self.view.widgets.numeric['protocol_min'].value = 1
            self.view.widgets.numeric['protocol_max'].value = 10
            self.view.widgets.numeric['protocol_n'].value = 10
            self.view.widgets.numeric['protocol_max'].title = 'Max weight'
            self.view.widgets.numeric['protocol_min'].title = 'Min weight'
        else:
            self.view.DOM_elements['protocol_widgets'].visible = False


    @log
    def run_protocol_callback(self, event):

        protocol = self.view.widgets.selectors['protocol'].value
        self.view.figures['stats_ephys'].visible = False

        if protocol == 'Input resistance and time constant':
            if self._check_passive_protocol():
                passive_data = calculate_passive_properties(self.model)
                self._plot_passive_properties(passive_data)

        elif protocol == 'Somatic spikes':
            if self._check_somatic_spikes_protocol():
                spike_data = detect_somatic_spikes(self.model)
                self._plot_somatic_spikes(spike_data)

        elif protocol == 'Voltage attenuation':
            if self._check_voltage_attenuation_protocol():
                data = calculate_voltage_attenuation(self.model)
                self._plot_voltage_attenuation(data)

        elif protocol == 'f-I curve':
            if self._check_somatic_spikes_protocol():
                min_amp = self.view.widgets.numeric['protocol_min'].value
                max_amp = self.view.widgets.numeric['protocol_max'].value
                n = self.view.widgets.numeric['protocol_n'].value
                duration = self.view.widgets.sliders['duration'].value
                data = calculate_fI_curve(self.model, duration=duration, min_amp=min_amp, max_amp=max_amp, n=n)
                self._plot_fI_curve(data)
                with remove_callbacks(self.view.widgets.sliders['iclamp_amp']):
                    self.view.widgets.sliders['iclamp_amp'].value = max_amp
                self.update_voltage()
            
        
        elif protocol == 'Dendritic nonlinearity':
            if self._check_dendritic_nonlinearity_protocol():
                max_weight = self.view.widgets.numeric['protocol_max'].value
                n = self.view.widgets.numeric['protocol_n'].value
                data = calculate_dendritic_nonlinearity(self.model, max_weight=max_weight, n=n)
                self._plot_dendritic_nonlinearity(data)
                self.update_voltage()

    def _check_passive_protocol(self):
        if len(self.model.recordings['v']) != 1:
            self.view.DOM_elements['stats_ephys'].text = "Please place a single recording at the soma."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        if len(self.model.iclamps) != 1:
            self.view.DOM_elements['stats_ephys'].text = "Please place a single current clamp at the soma."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        if list(self.model.iclamps.values())[0].amp >= 0:
            self.view.DOM_elements['stats_ephys'].text = "Please use hyperpolarizing current injection."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        return True

    def _check_somatic_spikes_protocol(self):
        if len(self.model.recordings['v']) != 1:
            self.view.DOM_elements['stats_ephys'].text = "Please place a single recording at the soma."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        if len(self.model.iclamps) != 1:
            self.view.DOM_elements['stats_ephys'].text = "Please place a single current clamp at the soma."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        if list(self.model.iclamps.values())[0].amp <= 0:
            self.view.DOM_elements['stats_ephys'].text = "Please use depolarizing current injection to elicit spikes."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        return True

    def _check_voltage_attenuation_protocol(self):
        if len(self.model.recordings['v']) < 2:
            self.view.DOM_elements['stats_ephys'].text = "Please place at least two recordings."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        if len(self.model.iclamps) != 1:
            self.view.DOM_elements['stats_ephys'].text = "Please place a single current clamp at one of the recording sites."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        if list(self.model.iclamps.values())[0].amp >= 0:
            self.view.DOM_elements['stats_ephys'].text = "Please use hyperpolarizing current injection."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        return True

    def _check_dendritic_nonlinearity_protocol(self):
        if len(self.model.iclamps) != 0:
            self.view.DOM_elements['stats_ephys'].text = "Please remove current clamp."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        if not any(
            key in self.model.populations and len(self.model.populations[key]) == 1 for key in ['AMPA', 'NMDA', 'AMPA_NMDA']
        ):
            self.view.DOM_elements['stats_ephys'].text = "Please add a valid synapse population with exactly one synapse."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        if len(self.model.recordings['v']) != 1:
            self.view.DOM_elements['stats_ephys'].text = "Please place a single recording at the dendrite."
            self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['error']
            self.update_status_message('Unsupported protocol.', 'error')
            return False
        return True

    def _plot_passive_properties(self, passive_data):

        Rin = passive_data['input_resistance']
        tau = passive_data['time_constant']
        tau1 = passive_data['tau1']
        tau2 = passive_data['tau2']
        v_onset = passive_data['onset_voltage']
        v_offset = passive_data['offset_voltage']
        t_decay = passive_data['decay_time']
        v_decay = passive_data['decay_voltage']
        A1 = passive_data['A1']
        A2 = passive_data['A2']
        start_t = passive_data['start_time']

        def _double_exp_decay(t, A1, tau1, A2, tau2):
            return A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2)

        shifted_exp_decay = _double_exp_decay(t_decay, A1, tau1, A2, tau2) + v_offset
        print(f"Shifted exp decay: {shifted_exp_decay}, v_offset: {v_offset}")
        data = {'xs': [t_decay + start_t], 'ys': [shifted_exp_decay], 'color': ['gold']}
        self.view.sources['frozen_v'].data = data

        stats = f"Input resistance = (V_min - V_init) / I<br>"
        stats += f"Input resistance: {np.round(Rin, 2)} MOhm<br>"
        stats += f"Time constant: {np.round(tau, 2)} ms<br>"
        stats += f"Onset voltage: {np.round(v_onset, 2)} mV<br>"
        stats += f"Offset voltage: {np.round(v_offset, 2)} mV<br>"


        self.view.DOM_elements['stats_ephys'].text = stats
        self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['success']
        self.update_status_message('Passive properties calculated successfully.', 'success')


    def _plot_somatic_spikes(self, spike_data):

        spike_times = spike_data['spike_times']
        spike_values = spike_data['spike_values']
        half_widths = spike_data['half_widths']
        amplitudes = spike_data['amplitudes']
        right_bases = spike_data['right_bases']
        left_bases = spike_data['left_bases']
        duration_ms = spike_data['stimulus_duration']

        self.view.sources['detected_spikes'].data = {'x': spike_times, 'y': spike_values}
        data = {'xs': [], 'ys': [], 'line_color': []}
        for t, v, w, a, lb, rb in zip(spike_times, spike_values, half_widths, amplitudes, left_bases, right_bases):
            data['xs'].append([t, t])
            data['ys'].append([v, v - a])
            data['line_color'].append('lawngreen')
            if not self.model.simulator._cvode:
                data['xs'].append([lb, rb])
                data['ys'].append([v - a/2, v - a/2])
                data['line_color'].append('lawngreen')
        self.view.sources['frozen_v'].data = data

        stats = f"Number of spikes: {len(spike_times)}<br>"
        if len(spike_times) > 1:
            stats += f"ISI: {np.round(np.mean(np.diff(spike_times)), 2)} ms<br>"
            stats += f"Average frequency: {np.round(len(spike_times) / self.view.widgets.sliders['duration'].value * 1000, 2)} Hz<br>"
            stats += f"Average frequency (1/ISI): {np.round(1000 / np.mean(np.diff(spike_times)), 2)} Hz<br>"
            stats += f"ISI-CV: {np.round(np.std(np.diff(spike_times)) / np.mean(np.diff(spike_times)), 2)}<br>"
            stats += f"Adaptation index: {np.round(np.sum(np.diff(np.diff(spike_times))) / np.sum(np.diff(spike_times)), 2)}<br>"
        stats += f"Average spike half-width: {np.round(np.mean(half_widths), 2)} ms<br>"
        stats += f"Average spike amplitude: {np.round(np.mean(amplitudes), 2)} mV<br>"

        self.view.DOM_elements['stats_ephys'].text = stats
        self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['success']
        self.update_status_message('Somatic spikes detected successfully.', 'success')


    def _plot_voltage_attenuation(self, data):
        path_distances = data['path_distances']
        min_voltages = data['min_voltages']
        end_voltages = data['end_voltages']
        attenuation = data['attenuation']

        self.view.figures['stats_ephys'].visible = True
        self.view.figures['stats_ephys'].xaxis.axis_label = 'Distance, µm'
        self.view.figures['stats_ephys'].yaxis.axis_label = 'Attenuation'
        self.view.figures['stats_ephys'].y_range.start = -0.1
        self.view.figures['stats_ephys'].y_range.end = 1.1
        
        self.view.sources['stats_ephys'].data = {'x': path_distances, 'y': attenuation}

        stats = f"<table><tr><th>Dist, µm</th><th>End voltage, mV</th><th>Attenuation</th></tr>"
        for d, min_v, end_v, a in zip(path_distances, min_voltages, end_voltages, attenuation):
            stats += f"<tr><td>{np.round(d,2)}</td><td>{np.round(end_v, 2)}</td><td>{np.round(a, 2)}</td></tr>"
        stats += "</table>"

        self.view.DOM_elements['stats_ephys'].text = stats
        self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['success']
        self.update_status_message('Voltage attenuation calculated successfully.', 'success')

    def _plot_fI_curve(self, data):

        amps = data['current_amplitudes']
        rates = data['firing_rates']
        vs = data['voltages']
        t = data['time']

        self.view.figures['stats_ephys'].visible = True
        self.view.figures['stats_ephys'].xaxis.axis_label = 'Current injection, nA'
        self.view.figures['stats_ephys'].yaxis.axis_label = 'Firing rate, Hz'
        self.view.figures['stats_ephys'].y_range.start = -1
        self.view.figures['stats_ephys'].y_range.end = max(rates) * 1.1
        self.view.sources['stats_ephys'].data = {'x': amps, 'y': rates}
        stats = f"<table><tr><th>Current, nA</th><th>Firing rate, Hz</th></tr>"
        for amp, rate in zip(amps, rates):
            stats += f"<tr><td>{np.round(amp,2)}</td><td>{np.round(rate, 2)}</td></tr>"
        stats += "</table>"
        self.view.DOM_elements['stats_ephys'].text = stats
        self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['success']
        self.update_status_message('f-I curve calculated successfully.', 'success')

    def _plot_dendritic_nonlinearity(self, data):

        expected_delta_vs = data['expected_response']
        delta_vs = data['observed_response']
        vs = data['voltages']
        t = data['time']

        self.view.figures['stats_ephys'].visible = True

        self.view.figures['stats_ephys'].xaxis.axis_label = 'Expected response'
        self.view.figures['stats_ephys'].yaxis.axis_label = 'Observed response'
        self.view.figures['stats_ephys'].y_range.start = -0.1
        self.view.figures['stats_ephys'].y_range.end = max(delta_vs) * 1.1
        self.view.sources['stats_ephys'].data = {'x': expected_delta_vs, 'y': delta_vs}
        self.view.sources['stats_ephys_extra'].data = {'x': expected_delta_vs, 'y': expected_delta_vs}

        stats = f"<table><tr><th>Expected response, ΔV (mV)</th><th>Observed response, ΔV (mV)</th></tr>"
        unitary_delta_v = min(expected_delta_vs)
        for expected, observed in zip(expected_delta_vs, delta_vs):
            stats += f"<tr><td>{np.round(expected,2)}</td><td>{np.round(observed, 2)}</td></tr>"
        stats += "</table>"
        self.view.DOM_elements['stats_ephys'].text = stats
        self.view.DOM_elements['stats_ephys'].styles['color'] = self.view.theme.status_colors['success']
        self.update_status_message('Dendritic nonlinearity calculated successfully.', 'success')



    #    elif event.item == 'sag_ratio':
    #         if len(self.selected_segs) < 1:
    #             stats += f"<b>Unsupported protocol.</b><br>Please select at least one segment to calculate sag ratio"
    #         else:
    #             seg = self.selected_segs[0]
    #             start_ts = int(self.model.iclamps[seg].delay / self.model.simulator.dt)
    #             stop_ts = int((self.model.iclamps[seg].delay + self.model.iclamps[seg].dur) / self.model.simulator.dt)
    #             if self.model.iclamps.get(seg):
    #                 i = self.model.iclamps[seg].amp
    #                 if i >= 0:
    #                     stats += f"<b>Unsupported protocol.</b><br>Please use hyperpolarizing current injection."
    #                 else:
    #                     v = np.array(self.model.simulator.recordings[seg])
    #                     v_end = v[stop_ts]
    #                     v_min = np.min(v)
    #                     v_start = v[start_ts]
    #                     v_min_idx = np.argmin(v)
    #                     sag_ratio = (v_end - v_min) / (v_start - v_min)
    #                     data = {'xs': [[t[v_min_idx], t[v_min_idx]], [t[stop_ts], t[stop_ts]]], 'ys': [[v_min, v_start], [v_min, v_end]]}
    #                     logger.debug(f"Data: {data}")
    #                     data.update({'color': ['red', 'red']})
    #                     self.view.sources['frozen_v'].data = data
    #                     stats += f"a = V_end - V_min = {np.round(v_end, 2)} - {np.round(v_min, 2)} = {np.round(v_end - v_min, 2)}<br>"
    #                     stats += f"b = V_start - V_min = {np.round(v_start, 2)} - {np.round(v_min, 2)} = {np.round(v_start - v_min, 2)}<br>"
    #                     stats += f"Sag ratio = a / b = {np.round(sag_ratio, 3)}"
    #             else:
    #                 stats += f"<b>Unsupported protocol.</b><br>Please apply current injection to the selected segment."



    @log
    def morphometric_stats_callback(self, event):

        selected_sections = list(self.selected_secs)
        if not selected_sections:
            self.view.DOM_elements['stats'].text = "Please select sections to calculate morphometric statistics."
            return

        stats = calculate_section_statistics(selected_sections)
        html_stats = f"""
        <b>Number of sections:</b> {stats['N_sections']}<br>
        <b>Number of bifurcations:</b> {stats['N_bifurcations']}<br>
        <b>Number of terminations:</b> {stats['N_terminations']}<br>
        <b>Depth:</b><br>
        &nbsp;&nbsp;Min: {stats['depth']['min']}<br>
        &nbsp;&nbsp;Max: {stats['depth']['max']}<br>
        <b>Diameter:</b><br>
        &nbsp;&nbsp;Min: {stats['diam']['min']} µm<br>
        &nbsp;&nbsp;Max: {stats['diam']['max']} µm<br>
        &nbsp;&nbsp;Mean: {stats['diam']['mean']} µm<br>
        &nbsp;&nbsp;Std: {stats['diam']['std']} µm<br>
        <b>Length:</b><br>
        &nbsp;&nbsp;Min: {stats['length']['min']} µm<br>
        &nbsp;&nbsp;Max: {stats['length']['max']} µm<br>
        &nbsp;&nbsp;Mean: {stats['length']['mean']} µm<br>
        &nbsp;&nbsp;Std: {stats['length']['std']} µm<br>
        <b>Area:</b><br>
        &nbsp;&nbsp;Min: {stats['area']['min']} µm²<br>
        &nbsp;&nbsp;Max: {stats['area']['max']} µm²<br>
        &nbsp;&nbsp;Mean: {stats['area']['mean']} µm²<br>
        &nbsp;&nbsp;Std: {stats['area']['std']} µm²<br>
        <b>Total length:</b> {stats['total_length']} µm<br>
        <b>Total area:</b> {stats['total_area']} µm²<br>
        """
        self.view.DOM_elements['stats'].text = html_stats

        # self.update_histogram()



    def update_histogram(self):
        diams = [seg.diam for seg in self.selected_segs]
        areas = [seg.area() for seg in self.selected_segs]
        # bins = np.linspace(0, 300, 40)
        hist, edges = np.histogram(areas, bins='auto')
        logger.debug(f'Top: {hist}\nLeft: {edges[:-1]}\nRight: {edges[1:]}')
        self.view.sources['section_param_hist'].data = {'top': hist, 'left': edges[:-1], 'right': edges[1:]}
        
        # self.view.figures['section_param_hist'].yaxis.axis_label = 'Count'
        self.view.figures['section_param_hist'].xaxis.axis_label = 'Area, µm2'
import numpy as np
from bokeh.models import Range1d

# from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

class ValidationMixin(): 

    def __init__(self):
        logger.debug('NavigationMixin init')
        super().__init__()   

    @log
    def stats_callback(self, event):
        stats='Stats: <br>'
        diams = [seg.diam for seg in self.selected_segs]
        lengths = [sec.L for sec in self.selected_secs]
        areas = [seg.area() for seg in self.selected_segs]
        # selection-independent metrics
        stats += f"N soma children: {len(self.model.cell.soma[0].children())}<br>"
        # number of ...
        stats += f"N sections: {len(self.selected_secs)}<br>"
        stats += f"N segments: {len(self.selected_segs)}<br>"
        stats += f"N bifurcations: {sum([1 for sec in self.selected_secs if len(sec.children()) == 2])}<br>"
        # average ...
        stats += f"Average diam: {np.round(np.mean(diams), 2)}±{np.round(np.std(diams), 2)} µm<br>"
        stats += f"Average lenght: {np.round(np.mean(lengths), 2)}±{np.round(np.std(lengths), 2)} µm<br>"
        stats += f"Average surface area: {np.round(np.mean(areas), 2)}±{np.round(np.std(areas), 2)} µm2<br>"
        stats += f"Average extent: ...<br>"
        # total ...
        stats += f"Total length: {np.round(np.sum(lengths), 2)} µm <br>"
        stats += f"Total surface area: {np.round(np.sum(areas), 2)} µm2 <br>"
        
        
        self.view.DOM_elements['stats'].text = stats

        self.update_histogram()

    def detect_somatic_spikes(self):
        from scipy.signal import find_peaks, peak_widths
        seg = self.model.cell.soma[0](0.5)
        if self.model.simulator.recordings.get(seg):
            v = np.array(self.model.simulator.recordings[seg].to_python())
            t = np.array(self.model.simulator.t)

        peaks, _ = find_peaks(v, height=0, distance=10)
        widths, heights, left_ips, right_ips = peak_widths(v, peaks, rel_height=0.5)
        _dt = self.model.simulator.dt
        widths = widths * _dt
        amplitudes = 2 * (v[peaks] - heights)
        logger.debug(f'Peaks: {peaks}')
        logger.debug(f'Widths: {widths}')
        self.view.sources['detected_spikes'].data = {'x': t[peaks], 'y': v[peaks]}
        data = {'xs': [], 'ys': [], 'color': []}
        for _peak, _amplitude in zip(peaks, amplitudes):
            data['xs'].append([t[_peak], t[_peak]])
            data['ys'].append([v[_peak], v[_peak] - _amplitude])
            data['color'].append('red')
        for _height, _left, _right in zip(heights, left_ips * _dt, right_ips * _dt):
            data['xs'].append([_left, _right])
            data['ys'].append([_height, _height])
            data['color'].append('red')
        self.view.sources['frozen_v'].data = data
        return t[peaks], widths, amplitudes

    def calculate_input_resistance(self):
        self.view.sources['detected_spikes'].data = {'x': [], 'y': []}

        seg = self.model.cell.soma[0](0.5)
        if self.model.simulator.recordings.get(seg):
            v = np.array(self.model.simulator.recordings[seg].to_python())
            v_min = np.min(v)
            i = self.model.iclamps[seg].amp
            start_ts = self.model.iclamps[seg].delay / self.model.simulator.dt
            end_ts = int((self.model.iclamps[seg].delay + self.model.iclamps[seg].dur) / self.model.simulator.dt)
            v_onset = v[int(start_ts)]
            v_offset = v[int(end_ts)]
        else:
            return
        
        # R = (v_min - v_onset) / i
        R = (v_onset - v_offset) / i
        return v_onset, v_offset, i, R

    def calculate_time_constant(self):
        from scipy.optimize import curve_fit

        def exp_decay(t, A, tau):
            return A * np.exp(-t / tau)

        seg = self.model.cell.soma[0](0.5)
        if self.model.simulator.recordings.get(seg):
            v = np.array(self.model.simulator.recordings[seg].to_python())
        else:
            return
        t = np.array(self.model.simulator.t)
        _dt = self.model.simulator.dt
        start_ts = int(self.model.iclamps[seg].delay / _dt)
        stop_ts = int((self.model.iclamps[seg].delay + self.model.iclamps[seg].dur) / _dt)
        min_ts = np.argmin(v[start_ts:stop_ts]) + start_ts
        # normalize voltage decay
        v_min = np.min(v[start_ts: min_ts])
        v_decay = v[start_ts: min_ts] - v_min
        t_decay = t[start_ts: min_ts] - t[start_ts]
        popt, pcov = curve_fit(exp_decay, t_decay, v_decay, p0=[1, 100])
        logger.debug(f'Fitted parameters: A={popt[0]}, tau={popt[1]}')
        data = {'xs': [t[start_ts:min_ts]], 'ys': [exp_decay(t_decay, *popt) + v_min] }
        data.update({'color': ['red']})
        self.view.sources['frozen_v'].data = data
        tau = popt[1]
        return tau 

    @log
    def stats_ephys_callback(self, event):
        t = np.array(self.model.simulator.t)
        self.view.figures['stats_ephys'].visible = False
        # self.view.widgets.buttons['iterate'].visible = False
        stats='<b>Validation resutls:</b><br>'

        if event.item == 'spikes':
            spike_times, widths, amplitudes = self.detect_somatic_spikes()
            stats += f"Number of spikes: {len(spike_times)}<br>"
            if len(spike_times) > 1:
                stats += f"ISI: {np.round(np.mean(np.diff(spike_times)), 2)} ms<br>"
                # stats += f"Average frequency: {np.round(len(spike_times) / self.view.widgets.sliders['duration'].value * 1000, 2)} Hz<br>"
                stats += f"Average frequency (1/ISI): {np.round(1000 / np.mean(np.diff(spike_times)), 2)} Hz<br>"
                stats += f"ISI-CV: {np.round(np.std(np.diff(spike_times)) / np.mean(np.diff(spike_times)), 2)}<br>"
                stats += f"Adaptation index: {np.round(np.sum(np.diff(np.diff(spike_times))) / np.sum(np.diff(spike_times)), 2)}<br>"
            stats += f"Average spike half-width: {np.round(np.mean(widths), 2)} ms<br>"
            stats += f"Average spike amplitude: {np.round(np.mean(amplitudes), 2)} mV<br>"

        elif event.item == 'R_in':
            v_min, v_onset, i, R = self.calculate_input_resistance()
            stats += f"Input resistance = (V_min - V_init) / I<br>"
            if i >= 0:
                stats += f"<b>Unsupported protocol.</b><br>Please use hyperpolarizing current injection.<br>Suggested duration 1000 ms, amplitude -0.1 nA"
            else:
                tau = self.calculate_time_constant()
                stats += f"<b>Input resistance</b> = ({np.round(v_min, 2)} - ({np.round(v_onset, 2)})) / {np.round(i, 2)} = <b>{np.round(R, 2)} MOhm</b>"
                if len(self.model.cell.all) == 1:
                    seg = self.model.cell.soma[0](0.5)
                    area_um2 = seg.area()
                    area_cm2 = area_um2 * 1e-8
                    stats += f"<br>Area:<br>{area_um2:.10f} µm2, {area_cm2:.10f} cm2" 
                    specific_capacitance_uf_per_cm2 = seg.cm
                    stats += f"<br>Specific capacitance, cm:<br>{specific_capacitance_uf_per_cm2} uF/cm2"
                    Cm_uf = area_cm2 * specific_capacitance_uf_per_cm2
                    stats += f"<br>Total capacitance, Cm:<br>{Cm_uf:.10f} uF"
                    rm_Ohm_times_cm2 = 1 / seg.gbar_leak
                    stats += f"<br>Leak conductance, gbar_leak:<br>{seg.gbar_leak} S/cm2"
                    stats += f"<br>Specific membrane resistance, rm:<br>{rm_Ohm_times_cm2} Ohm*cm2"
                    Rm_Ohm = rm_Ohm_times_cm2 / area_cm2
                    Rm_MOhm = Rm_Ohm * 1e-6
                    stats += f"<br>Total membrane resistance, Rm:<br>{Rm_MOhm:.10f} MOhm"
                    tau_s = Cm_uf * Rm_MOhm
                    tau_ms = tau_s * 1e3
                    stats += f"<br>Analytical time constant, tau:<br>{tau_ms} ms"
                stats += f"<br>Time constant = {tau:.10f} ms"

        elif event.item == 'sag_ratio':
            if len(self.selected_segs) < 1:
                stats += f"<b>Unsupported protocol.</b><br>Please select at least one segment to calculate sag ratio"
            else:
                seg = self.selected_segs[0]
                start_ts = int(self.model.iclamps[seg].delay / self.model.simulator.dt)
                stop_ts = int((self.model.iclamps[seg].delay + self.model.iclamps[seg].dur) / self.model.simulator.dt)
                if self.model.iclamps.get(seg):
                    i = self.model.iclamps[seg].amp
                    if i >= 0:
                        stats += f"<b>Unsupported protocol.</b><br>Please use hyperpolarizing current injection."
                    else:
                        v = np.array(self.model.simulator.recordings[seg])
                        v_end = v[stop_ts]
                        v_min = np.min(v)
                        v_start = v[start_ts]
                        v_min_idx = np.argmin(v)
                        sag_ratio = (v_end - v_min) / (v_start - v_min)
                        data = {'xs': [[t[v_min_idx], t[v_min_idx]], [t[stop_ts], t[stop_ts]]], 'ys': [[v_min, v_start], [v_min, v_end]]}
                        logger.debug(f"Data: {data}")
                        data.update({'color': ['red', 'red']})
                        self.view.sources['frozen_v'].data = data
                        stats += f"a = V_end - V_min = {np.round(v_end, 2)} - {np.round(v_min, 2)} = {np.round(v_end - v_min, 2)}<br>"
                        stats += f"b = V_start - V_min = {np.round(v_start, 2)} - {np.round(v_min, 2)} = {np.round(v_start - v_min, 2)}<br>"
                        stats += f"Sag ratio = a / b = {np.round(sag_ratio, 3)}"
                else:
                    stats += f"<b>Unsupported protocol.</b><br>Please apply current injection to the selected segment."

        elif event.item == 'attenuation':
            if len(self.selected_segs) < 2:
                stats += f"<b>Unsupported protocol.</b><br>Please select at least two segments to calculate voltage attenuation"
            else:
                stimulated_segs = [seg for seg in self.selected_segs if self.model.iclamps.get(seg)]
                if len(stimulated_segs) > 1:
                    stats += f"<b>Unsupported protocol.</b><br>Only one stimulus is allowed."
                elif len(stimulated_segs) == 0:
                    stats += f"<b>Unsupported protocol.</b><br>Please apply current injection to one of the selected segments."
                else:
                    stimulated_seg = stimulated_segs[0]
                    logger.debug(f'Stimulated seg: {stimulated_seg},') 
                    logger.debug(f'Recordings: {self.model.simulator.recordings}')
                    logger.debug(f'Recording at stimulated seg: {self.model.simulator.recordings[stimulated_seg]}')
                    amp = self.model.iclamps[stimulated_seg].amp
                    if amp >= 0:
                        stats += f"<b>Unsupported protocol.</b><br>Please use hyperpolarizing current injection."
                    else:
                        distances = [self.model.cell.distance_from_soma(seg) for seg in self.selected_segs]
                        start_ts = int(self.model.iclamps[stimulated_seg].delay / self.model.simulator.dt)
                        stop_ts = int((self.model.iclamps[stimulated_seg].delay + self.model.iclamps[stimulated_seg].dur) / self.model.simulator.dt)
                        voltage_at_stimulated = np.array(self.model.simulator.recordings[stimulated_seg])[start_ts:stop_ts]
                        voltages = [np.array(self.model.simulator.recordings[seg])[start_ts:stop_ts] for seg in self.selected_segs]
                        delta_v_at_stimulated = voltage_at_stimulated[0] - np.min(voltage_at_stimulated)
                        delta_vs = [v[0] - np.min(v) for v in voltages]
                        min_voltages = [np.min(v) for v in voltages]
                        attenuation = [dv / delta_v_at_stimulated for dv in delta_vs]
                        ziped = sorted(zip(distances, min_voltages, attenuation), key=lambda x: x[0])
                        # make a table with distances and max voltages
                        stats += f"<table><tr><th>Dist, µm</th><th>Voltage, mV</th><th>Attenuation</th></tr>"
                        for d, v, a in ziped:
                            stats += f"<tr><td>{np.round(d,2)}</td><td>{np.round(v, 2)}</td><td>{np.round(a, 2)}</td></tr>"
                        stats += "</table>"
                        self.view.figures['stats_ephys'].visible = True
                        self.view.figures['stats_ephys'].xaxis.axis_label = 'Distance, µm'
                        self.view.figures['stats_ephys'].yaxis.axis_label = 'Attenuation'
                        self.view.figures['stats_ephys'].y_range = Range1d(0, 1)
                        # scatter plot where x is distance and y is attenuation
                        data = {'x': distances, 'y': attenuation}
                        self.view.sources['stats_ephys'].data = data

        elif event.item == 'nonlinearity':
            seg = self.selected_segs[0]
            _group = self.model.synapses['AMPA_NMDA'].groups[0]
            start_ts = int(_group.start / self.model.simulator.dt)
            delta_vs = []
            max_weight = _group.weight
            for i in range(1, max_weight + 1):
                _group.weight = i
                _duration = self.view.widgets.sliders['duration'].value
                self.model.simulator.run(_duration)
                vs = np.array(self.model.simulator.recordings[seg]).flatten()
                vs = np.array(vs).flatten()
                v_start = vs[start_ts]
                v_max = np.max(vs[start_ts:])
                delta_v = v_max - v_start
                delta_vs.append(delta_v)
                logger.debug(f"Weight: {i}, delta_v: {delta_v}")
            unitary_delta_v = delta_vs[0]
            expected_delta_vs = [i * unitary_delta_v for i in range(1, max_weight + 1)]
            stats += f"Unitary delta V = {unitary_delta_v} mV<br>"
            data = {'x': expected_delta_vs, 'y': delta_vs}
            self.view.sources['stats_ephys'].data = data
            stats += f"To proceed with nonlinearity validation, please press 'Iterate' button"
            self.view.figures['stats_ephys'].visible = True
            # self.view.widgets.buttons['iterate'].visible = True
            self.view.figures['stats_ephys'].xaxis.axis_label = 'Expected EPSP, mV'
            self.view.figures['stats_ephys'].yaxis.axis_label = 'Actual EPSP, mV'
            max_dv = max(max(expected_delta_vs), max(delta_vs))
            self.view.figures['stats_ephys'].y_range.end = max_dv
            self.view.figures['stats_ephys'].x_range.end = max_dv

        elif event.item == 'fI_curve':
            # calculate somatic firing rate for different current injections with step 100 pA
            seg = self.model.cell.soma[0](0.5)
            firing = []
            for amp in range(0, 1001, 100):
                self.model.iclamps[seg].amp = amp * 1e-3
                
                _duration = self.view.widgets.sliders['duration'].value
                self.model.simulator.run(_duration)
                spike_times, _, _ = self.detect_somatic_spikes()
                stats += f"Amplitude: {amp} pA, spikes: {len(spike_times)}<br>"
                firing.append(len(spike_times))
            data = {'x': np.arange(0, 1001, 100), 'y': firing}
            self.view.sources['stats_ephys'].data = data
            self.view.figures['stats_ephys'].visible = True
            self.view.figures['stats_ephys'].xaxis.axis_label = 'Current injection, pA'
            self.view.figures['stats_ephys'].yaxis.axis_label = 'Firing rate, Hz'
            
            

        self.view.DOM_elements['stats_ephys'].text = stats

    # def iterate_validation_callback(self, event):
    #     syn_type = self.view.widgets.selectors['syn_type'].value
    #     _group = self.model.synapses[syn_type].groups[0]
    #     start_ts = int(_group.start / self.model.simulator.dt)

    #     vs = np.array(self.model.simulator.recordings[self.selected_segs[0]]).flatten()
    #     v_start = vs[start_ts]
    #     v_max = np.max(vs[start_ts:])
    #     delta_v = v_max - v_start
    #     logger.debug(f"Weight: {_group.weight}, delta_v: {delta_v}")

    #     data = dict(self.view.sources['stats_ephys'].data)
    #     logger.debug(f"Data before: {data}")
    #     if _group.weight == 1:
    #         data = {'x': [], 'y': []}
    #         data['x'].append(delta_v)
    #         data['y'].append(delta_v)
    #         self.view.DOM_elements['stats_ephys'].text += f"<br>Unitary PSP = {delta_v} mV<br>"
    #     else:
    #         data['x'].append(data['x'][0]*_group.weight)
    #         data['y'].append(delta_v)
    #     logger.debug(f"Data after: {data}")
    #     self.view.sources['stats_ephys'].data = data
    #     max_x, max_y = max(data['x']), max(data['y'])
    #     if max_x > max_y:
    #         self.view.figures['stats_ephys'].y_range.end = max_x
    #     else:
    #         self.view.figures['stats_ephys'].y_range.end = max_y

    #     _group.weight += 1
    #     self.view.DOM_elements['syn_group_panel'].children[3].value += 1
    #     self.update_voltage()

    def update_histogram(self):
        diams = [seg.diam for seg in self.selected_segs]
        areas = [seg.area() for seg in self.selected_segs]
        # bins = np.linspace(0, 300, 40)
        hist, edges = np.histogram(areas, bins='auto')
        logger.debug(f'Top: {hist}\nLeft: {edges[:-1]}\nRight: {edges[1:]}')
        self.view.sources['section_param_hist'].data = {'top': hist, 'left': edges[:-1], 'right': edges[1:]}
        
        # self.view.figures['section_param_hist'].yaxis.axis_label = 'Count'
        self.view.figures['section_param_hist'].xaxis.axis_label = 'Area, µm2'
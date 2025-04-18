from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

import time
from utils import timeit

from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

from bokeh.models import CategoricalColorMapper
import colorcet as cc
from matplotlib import cm
import numpy as np
from bokeh.palettes import Blues6, Oranges6, Greens6, Reds6, Purples6

class SimulationMixin():
    """ This class is a mixin for the Presenter class.
    It provides methods for handling the Simulation panel of the View.
    """

    def __init__(self):
        logger.debug('BiophysMixin init')
        super().__init__()
        self._recorded_segments = []
        
    def get_recorded_segments(self, var=None):
        """ Returns the segments in which the variable is recorded. """
        var_names = [var] if var else self.model.simulator.recordings.keys()
        segments = [seg for var in var_names 
            for seg in self.model.recordings.get(var, [])]
        return segments

    # MODEL TO VIEW

    @log
    @timeit
    def update_voltage(self):
        if not self.model.simulator.recordings:
            logger.warning('No recordings selected, interrupting simulation')
            return

        duration = self.view.widgets.sliders['duration'].value
        start = time.time()
        self.model.simulator.run(duration)
        runtime = time.time() - start
        self.view.DOM_elements['runtime'].text = f'✅ Runtime: {runtime:.2f} s'

        if self.model.simulator.recordings.get('v'):
            self._update_voltage_data()
        else:
            self.view.sources['sim'].data = {'xs': [], 'ys': [], 'labels': []}
        
        current_names = [k for k in self.model.simulator.recordings.keys() if k not in ['v']]
        if current_names:
            self._update_current_data(current_names)
        else:
            self.view.sources['curr'].data = {'xs': [], 'ys': [], 'labels': [], 'names': []}
        
        if any(self.model.populations.values()):
            self.update_spike_times_data()

        
    def _update_voltage_data(self):

        segments = self.get_recorded_segments('v')
        labels = [str(seg.idx) for seg in segments]
        voltages = list(self.model.simulator.recordings['v'].values())

        ts = [self.model.simulator.t for _ in range(len(voltages))]

        self.view.sources['sim'].data = {
            'xs': ts, 
            'ys': voltages, 
            'labels': labels
        }


    def _update_current_data(self, current_names):

        currents = []
        labels = []
        names = []
        
        for current_name in current_names:
            
            _segments = self.get_recorded_segments(current_name)
            _labels = [str(seg.idx) for seg in _segments]
            _currents = list(self.model.simulator.recordings[current_name].values())

            currents.extend(_currents)
            labels.extend(_labels)
            names.extend([current_name] * len(_currents))

        # Time series: same time vector for each trace
        ts = [self.model.simulator.t for _ in range(len(currents))]

        # Push to the Bokeh data source
        self.view.sources['curr'].data = {
            'xs': ts,
            'ys': currents,
            'labels': labels,
            'names': names
        }


    @log
    @timeit
    def update_spike_times_data(self):
        data = {'x': [], 'y': [], 'color': []}
        for syn_type, pops in self.model.populations.items():
            for pop_name, pop in pops.items():
                if not pop: continue
                for seg_idx, synapses in pop.synapses.items():
                    for i, syn in enumerate(synapses):
                        label = f'Pop_{pop_name}_seg_{seg_idx}_syn_{i}'
                        color = 'blue' if syn_type in ['GABAa', 'GABAb'] else 'orange'
                        data['x'].extend(syn.spike_times)
                        data['y'].extend([label] * len(syn.spike_times))
                        data['color'].extend([color] * len(syn.spike_times))
        
        if data['y']:
            synapse_names = sorted(set(data['y']))
            self.view.figures['spikes'].y_range.factors = synapse_names
            if len(synapse_names) > 20:
                self.view.figures['spikes'].yaxis.ticker = []

        self.view.sources['spikes'].data = data


    def runtime_callback_on_change(self, attr, old, new):
        self.view.DOM_elements['runtime'].text = f'Runtime: ⏳'

    def runtime_callback_on_event(self, event):
        self.view.DOM_elements['runtime'].text = f'Runtime: ⏳'
    
    def voltage_callback_on_change(self, attr, old, new):
        if self.view.widgets.switches['run_on_interaction'].active:
            self.update_voltage()

   
    def voltage_callback_on_event(self, event):
        if self.view.widgets.switches['run_on_interaction'].active:
            self.update_voltage()

    def voltage_callback_on_click(self, event):
        self.update_voltage()

    def record_current_callback(self, attr, old, new):
        """ Callback for the record current switch. """
        
        mech_name = self.view.widgets.selectors['mechanism'].value
        if self.view.widgets.switches['record_current'].active and mech_name != 'Independent':
            mech = self.model.mechanisms[mech_name]
            self.update_voltage()
        else:
            self.view.sources['curr'].data = {'xs': [], 'ys': [], 'label': []}
            

    @log
    def toggle_iclamp_callback(self, attr, old, new):
        seg = self.selected_segs[0]
        sec, loc = seg._section, seg.x
        if new:
            with remove_callbacks(self.view.widgets.sliders['iclamp_amp']):
                self.view.widgets.sliders['iclamp_amp'].value = 0
            with remove_callbacks(self.view.widgets.sliders['iclamp_duration']):
                self.view.widgets.sliders['iclamp_duration'].value = [100, 200]
            self.view.widgets.sliders['iclamp_duration'].visible = True
            self.view.widgets.sliders['iclamp_amp'].visible = True
            # self.view.widgets.selectors['iclamp_amp_unit'].visible = True
            self.model.add_iclamp(sec=sec, loc=loc)
            self._update_graph_param('iclamps')
        else:
            self.model.remove_iclamp(sec=sec, loc=loc)
            self.view.widgets.sliders['iclamp_duration'].visible = False
            self.view.widgets.sliders['iclamp_amp'].visible = False
            # self.view.widgets.selectors['iclamp_amp_unit'].visible = False
            self._update_graph_param('iclamps')

    def update_equilibtium_potentials(self):
        for ch in self.model.channels.values():
            if hasattr(ch, 'ion'):
                logger.debug(f'Updating equilibrium potential for {ch.ion}')
                self.view.widgets.spinners[f'e{ch.ion}'].visible = True
                self.model.equilibrium_potentials[ch.ion] = self.view.widgets.spinners[f'e{ch.ion}'].value
            else:
                logger.debug(f'No ion for {ch.name}')


    # VIEW TO MODEL

    def update_dt_callback(self, attr, old, new):
        self.model.simulator.dt = new

    def update_temperature_callback(self, attr, old, new):
        self.model.simulator.temperature = new

    def update_v_init_callback(self, attr, old, new):
        self.model.simulator.v_init = new

    def update_ek_callback(self, attr, old, new):
        self.model.update_e('k', new)

    def update_ena_callback(self, attr, old, new):
        self.model.update_e('na', new)

    def update_eca_callback(self, attr, old, new):
        self.model.update_e('ca', new)

    def update_e_leak_callback(self, attr, old, new):
        self.model.update_e('_leak', new)

    @log
    def update_Ra_callback(self, attr, old, new):
        for sec in self.selected_secs:
            sec.Ra = new
from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

import time
from utils import timeit

from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

from bokeh.models import CategoricalColorMapper
import colorcet as cc

class SimulationMixin():
    """ This class is a mixin for the Presenter class.
    It provides methods for handling the Simulation panel of the View.
    """

    def __init__(self):
        logger.debug('BiophysMixin init')
        super().__init__()
        self.recorded_segments = []

    # MODEL TO VIEW

    @log
    @timeit
    def update_voltage(self):
        if not self.model.simulator.recordings:
            logger.warning('No recordings selected, interrupting simulation')
            return

        ### Get labels for recorded segments ###
        labels = [str(seg.idx) for seg in self.model.simulator.recordings.keys()]
        logger.info(f'Recording voltage from {labels}')

        duration = self.view.widgets.sliders['duration'].value
        start = time.time()
        ts, vs, Is = self.model.simulator.run(duration)
        self.view.DOM_elements['runtime'].text = f'✅ Runtime: {time.time() - start:.2f} s'
    
        ### Update color of voltage and current traces ###
        if self.model.simulator.recordings.keys():
            # color_mapper = CategoricalColorMapper(palette=self.view.theme.palettes['trace'], factors=labels)
            factors = [str(seg.idx) for seg in self.recorded_segments]
            color_mapper = CategoricalColorMapper(palette=cc.glasbey_cool, factors=factors)
            self.view.figures['sim'].renderers[0].glyph.line_color = {'field': 'label', 'transform': color_mapper}
            if Is:
                self.view.figures['curr'].renderers[0].glyph.line_color = {'field': 'label', 'transform': color_mapper}
        else:
            factors = []

        # ts = [t[::25] for t in ts]
        # vs = [v[::25] for v in vs]
        # Is = [I[::25] for I in Is]
        logger.debug(f'Show traces from segments: {self.recorded_segments}')
        vs = [self.model.simulator.recordings[seg].to_python() for seg in self.recorded_segments]
        self.view.sources['sim'].data = {'xs': ts[:len(vs)], 'ys': vs, 'label': factors}
        self.view.sources['curr'].data = {'xs': ts[:len(Is)], 'ys': Is, 'label': factors}
    
        if self.model.synapses:
            self.update_spike_times_data()

    
    @log
    @timeit
    def update_spike_times_data(self):
        # logger.warning('Not implemented')
        data = {'x': [], 'y': [], 'color': []}
        for syn in self.model.synapses.values():
            for group in syn.groups:
                # if group.recordings:
                for seg, seg_stims in group.stims.items():
                    for i, stim in enumerate(seg_stims):
                        stim = stim[1].to_python()
                        for spike_time in stim:
                            data['x'].append(spike_time)
                            data['y'].append(f'G_{group.name}_at_{get_seg_name(seg)}_Syn_{i}')
                            data['color'].append('blue' if syn.name in ['GABAa', 'GABAb'] else 'orange')
        

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
        if self.view.widgets.switches['real_time'].active:
            self.update_voltage()

   
    def voltage_callback_on_event(self, event):
        if self.view.widgets.switches['real_time'].active:
            self.update_voltage()

    def voltage_callback_on_click(self, event):
        self.update_voltage()

    def record_current_callback(self, event):
        
        ch = self.model.channels[self.view.widgets.selectors['channel'].value]
        self.model.simulator.ch = ch
        self.update_voltage()

    @log
    def toggle_iclamp_callback(self, attr, old, new):
        if new:
            with remove_callbacks(self.view.widgets.sliders['iclamp_amp']):
                self.view.widgets.sliders['iclamp_amp'].value = 0
            with remove_callbacks(self.view.widgets.sliders['iclamp_duration']):
                self.view.widgets.sliders['iclamp_duration'].value = [100, 200]
            self.view.widgets.sliders['iclamp_duration'].visible = True
            self.view.widgets.sliders['iclamp_amp'].visible = True
            # self.view.widgets.selectors['iclamp_amp_unit'].visible = True
            self.model.add_iclamp(seg=self.selected_segs[0])
            self.update_graph_param('iclamps')
        else:
            self.model.remove_iclamp(seg=self.selected_segs[0])
            self.view.widgets.sliders['iclamp_duration'].visible = False
            self.view.widgets.sliders['iclamp_amp'].visible = False
            # self.view.widgets.selectors['iclamp_amp_unit'].visible = False
            self.update_graph_param('iclamps')

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

    def update_celsius_callback(self, attr, old, new):
        self.model.simulator.celsius = new

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
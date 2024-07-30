import numpy as np

from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

from logger import logger, decorator_logger

from bokeh.models import RangeSlider, Slider, Select
from bokeh.layouts import row, column

from model.mechanisms.distributions import Distribution

from bokeh_utils import SmartSlider
from bokeh_utils import remove_callbacks

from bokeh.models import LogScale, LinearScale

from bokeh.models import ColumnDataSource

from bokeh.models import Slider, TabPanel, Tabs, Button, Spinner
from bokeh.models import Div
from symfit import variables, parameters, Model, Fit, exp
from typing import List, Dict, Tuple
from bokeh.events import ButtonClick

from bokeh.palettes import Bokeh

from model.mechanisms.channels import StandardIonChannel

from bokeh_utils import log



from presenter.io import IOMixin
from presenter.navigation import NavigationMixin
from presenter.validation import ValidationMixin
from presenter.graph import GraphMixin
from presenter.section import SectionMixin
from presenter.cell import CellMixin
from presenter.biophys import BiophysMixin
from presenter.temp import TempMixin


class Presenter(IOMixin, CellMixin, BiophysMixin, SectionMixin, GraphMixin, NavigationMixin, ValidationMixin, TempMixin):

    def __init__(self, view, model):
        logger.debug('Initializing Presenter')
        # CellMixin.__init__(self)
        # SectionMixin.__init__(self)
        # GraphMixin.__init__(self)
        # BiophysMixin.__init__(self)
        # NavigationMixin.__init__(self)
        super().__init__()
        self.view = view
        self.model = model
        

    @log
    def states_callback(self, attr, old, new):
        import inspect

        ch = self.selected_channel
        if ch.name == 'Leak':
            self.view.sources['inf_orig'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
            self.view.sources['tau_orig'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
            self.view.sources['inf_fit'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
            self.view.sources['tau_fit'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
            return

        # sig = inspect.signature(ch.update)
        # logger.debug(f'{ch.name} `update` signature: {sig}, parameters: {sig.parameters}')
        
        if hasattr(ch, 'cai'):
            x_range = np.logspace(-5, 5, 1000)
            logger.debug(f'X scale {self.view.figures["inf"].x_scale}')
            self.view.figures['inf'].x_scale = LogScale()
            logger.debug(f'X scale {self.view.figures["inf"].x_scale}')
        else: 
            logger.debug('Using linear scale for x-axis')
            x_range = np.linspace(-100, 100, 1000)

        ch.update(x_range)

        inf_values = []
        inf_labels = []
        tau_values = []
        tau_labels = []
        v_ranges = []
        for i, (state_var, state_params) in enumerate(ch.state_vars.items()):
            inf = getattr(ch, state_params['inf']).tolist()
            tau = getattr(ch, state_params['tau']).tolist()
            inf_values.append(inf)
            tau_values.append(tau)
            inf_labels.append(state_var)
            tau_labels.append(state_var)
            v_ranges.append(x_range.tolist())

        if isinstance(ch, StandardIonChannel):
            ch_type = 'fit'
        else:
            ch_type = 'orig'

        self.view.sources[f'inf_{ch_type}'].data = {'xs': v_ranges, 
                                            'ys': inf_values, 
                                            'label': inf_labels,
                                            'color': [Bokeh[8][2*i+1] for i in range(len(inf_labels))]}
        self.view.sources[f'tau_{ch_type}'].data = {'xs': v_ranges, 
                                            'ys': tau_values, 
                                            'label': tau_labels,
                                            'color': [Bokeh[8][2*i+1] for i in range(len(tau_labels))]}

        self.view.figures[f'inf'].title.text = f'Steady state, {ch.name}'
        self.view.figures[f'tau'].title.text = f'Time constant, {ch.name}'

        self.view.sources['inf_fit'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
        self.view.sources['tau_fit'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}

    @log
    def create_channel_panel(self, ch):
        
        if not 'standard' in ch.name:
            button = Button(label=f'Standardize {ch.name}')
            button.on_click(self.standardize_callback)
            button.on_click(self.voltage_callback_on_event)

        def make_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                
                setattr(ch, slider_title, new)
                # ch.update(np.linspace(-100, 100, 1000))

                for seg in self.model.cell.segments.values():
                    setattr(seg, f'{slider_title}_{ch.suffix}', new)

            return slider_callback

        sliders = []
        for var in ch.range_params:
            if var == 'gbar': continue
            logger.info(f'Creating slider for {var}')
            slider = SmartSlider(name=var, value=getattr(ch, var))
            slider.on_change('value_throttled', make_slider_callback(slider.title))
            slider.on_change('value_throttled', self.states_callback)
            slider.on_change('value_throttled', self.voltage_callback_on_change)
            sliders.append(slider.get_widget())
            
        
        if sliders:
            if 'standard' in ch.name:
                panel = TabPanel(child=column([*sliders]), title=ch.name)
            else:
                panel = TabPanel(child=column([button, *sliders]), title=ch.name)
        else:
           panel = TabPanel(child=column([button, Div(text='No sliders to display. Try adding some variables to RANGE')]), 
                            title=ch.name)

        return panel

    @log
    def update_channel_tabs(self):
        logger.debug(f'Updating channel {self.model.channels.values()}')
        self.view.widgets.tabs['channels'].tabs = [self.create_channel_panel(ch) for ch in self.model.channels.values() if ch.name != 'Leak']
        self.view.widgets.tabs['channels'].on_change('active', self.states_callback)
        self.view.widgets.tabs['channels'].on_change('active', self.voltage_callback_on_change)


    @log
    def standardize_callback(self, event):
        custom_ch = self.selected_channel

        self.model.standardize_channel(custom_ch)
        logger.info(f'Standardized {custom_ch.name}')

        self.view.widgets.multichoice['mod_files'].value = [v for v in self.view.widgets.multichoice['mod_files'].value if v != custom_ch.name]
        self.view.widgets.multichoice['mod_files_std'].value = self.view.widgets.multichoice['mod_files_std'].value + [f'{custom_ch.name}_standard']

        # open the new chanel's tab
        with remove_callbacks(self.view.widgets.tabs['channels']):
            self.view.widgets.tabs['channels'].active = len(self.view.widgets.tabs['channels'].tabs) - 1

        standard_ch = self.model.channels[f'{custom_ch.name}_standard']
        v_range = np.linspace(-100, 100, 1000)
        standard_ch.update(v_range)
        for group in custom_ch.to_dict()['groups']:
            segments = [self.model.cell.segments[seg_name] for seg_name in group['seg_names']]
            standard_ch.add_group(segments, f"{group['param_name']}s")
            standard_ch.groups[-1].distribution = Distribution.from_dict(group['distribution'])

        inf_fit_data = {'xs': [v_range.tolist() for _ in range(len(standard_ch.state_vars))],
                        'ys': [getattr(standard_ch, standard_ch.state_vars[state]['inf']).tolist() for state in standard_ch.state_vars],
                        'label': list(standard_ch.state_vars.keys()),
                        'color': [Bokeh[8][2*i+2] for i in range(len(standard_ch.state_vars))]
                        }
        tau_fit_data = {'xs': [v_range.tolist() for _ in range(len(standard_ch.state_vars))],
                        'ys': [getattr(standard_ch, standard_ch.state_vars[state]['tau']).tolist() for state in standard_ch.state_vars],
                        'color': [Bokeh[8][2*i+2] for i in range(len(standard_ch.state_vars))],
                        'label': list(standard_ch.state_vars.keys())} 

        self.view.sources['inf_fit'].data = inf_fit_data
        self.view.sources['tau_fit'].data = tau_fit_data


    @log
    def update_graph_param_selector(self):
        new_params = {f'gbar_{ch.suffix}': 
                      f'Conductance {ch.suffix}, S/cm2' 
                      for ch in self.model.channels.values()}
        self.view.update_ephys_params(new_params)
        logger.debug(f'Updating graph param selector with {new_params}')
        logger.debug(f'Updating graph param selector with ephys params: {self.view.ephys_params}')
        with remove_callbacks(self.view.widgets.selectors['graph_param']):
            if self.view.widgets.tabs['section'].active == 1:
                self.view.widgets.selectors['graph_param'].options = list(self.view.ephys_params)
                self.view.widgets.selectors['graph_param'].value = self.view.widgets.selectors['graph_param'].options[0]
            else:
                self.view.widgets.selectors['graph_param'].options = list(self.view.params)
                self.view.widgets.selectors['graph_param'].value = self.view.widgets.selectors['graph_param'].options[0]

    def reset_simulation_state(self):
        self.view.widgets.switches['record'].active = False
        self.view.widgets.switches['iclamp'].active = False
        self.view.sources['sim'].data = data={'xs': [], 'ys': [], 'color': []}

    def add_group_callback(self, event):
        
        segments = self.selected_segs
        ch = self.selected_channel
        param_name = self.selected_param
        dtype = self.view.widgets.selectors['distribution_type'].value
        if dtype == 'uniform':
            ch.add_group(segments, param_name, Distribution('uniform', value=0))
        elif dtype == 'linear':
            ch.add_group(segments, param_name, Distribution('linear', intercept=0, slope=1))
        elif dtype == 'exponential':
            ch.add_group(segments, param_name, Distribution('exponential', vertical_shift=0, scale_factor=1, growth_rate=1, horizontal_shift=0))
        elif dtype == 'sigmoid':
            ch.add_group(segments, param_name, Distribution('sigmoid', vertical_shift=0, scale_factor=1, growth_rate=1, horizontal_shift=0))
        self.update_graph_param(param_name)

        self.view.widgets.selectors['distribution'].options = [group.name for group in ch.groups]
        self.view.widgets.selectors['distribution'].value = ch.groups[-1].name
    
    def remove_group_callback(self, event):
        ch = self.selected_channel
        group = self.selected_group
        logger.debug(f'Removing group {group.name} from {ch.name}')

        ch.remove_group(group)
        for group in ch.groups:
            group.apply()
        self.update_graph_param(self.selected_param)
        self.update_section_param_data()

        # with remove_callbacks(self.view.widgets.selectors['distribution']):
        self.view.widgets.selectors['distribution'].options = [group.name for group in ch.groups]
        self.view.widgets.selectors['distribution'].value = ch.groups[-1].name if ch.groups else None

    def update_distribution_selector_options_callback(self, attr, old, new):
        if self.view.widgets.tabs['section'].active == 1:
            ch = self.selected_channel
            self.view.widgets.selectors['distribution'].options = [group.name for group in ch.groups]
            self.view.widgets.selectors['distribution'].value = ch.groups[-1].name if ch.groups else None

    @log
    def update_distribution_plot(self):

        param_name = self.selected_param
        group = self.selected_group

        sec_type_to_index = {'soma': 0, 'axon': 1, 'dend': 2, 'apic': 3}

        segs = self.selected_segs
        data = {'x': [self.model.cell.distance_from_soma(seg) for seg in segs], 
                'y': [getattr(seg, param_name) for seg in segs],
                'color': [self.view.theme.palettes['sec_type'][sec_type_to_index[get_sec_type(seg.sec)]] for seg in segs], 
                'label': [get_seg_name(seg) for seg in segs]}


        self.view.sources['distribution'].data = data

    @property
    def selected_synapse(self):
        return self.model.synapses[self.view.widgets.selectors['syn_type'].value]

    @log
    def add_synapse_group_callback(self, event):
        
        segments = self.selected_segs
        syn = self.selected_synapse
        N_syn = self.view.widgets.spinners['N_syn'].value
        syn.add_group(segments=segments, N_syn=N_syn)

        self.update_graph_param(syn.name)

        self.view.widgets.selectors['syn_group'].options = [group.name for group in syn.groups]
        self.view.widgets.selectors['syn_group'].value = syn.groups[-1].name

    def remove_synapse_group_callback(self, event):
        syn = self.selected_synapse
        group = self.selected_syn_group
        
        logger.debug(f'Removing group {group.name} from {syn.name}')

        syn.remove_group(group)
        self.update_graph_param(syn.name)

        self.view.widgets.selectors['syn_group'].options = [group.name for group in syn.groups]
        self.view.widgets.selectors['syn_group'].value = syn.groups[-1].name if syn.groups else None

    def toggle_synapse_group_panel(self):
        
        group = self.selected_syn_group
        if group is None:
            self.view.DOM_elements['syn_group_panel'].children = []
            return

        def make_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                setattr(group, slider_title, new)
            return slider_callback

        
        rate_slider = Slider(title='Rate', value=group.rate, start=0.1, end=100, step=0.1, width=300)
        rate_slider.on_change('value_throttled', make_slider_callback('rate'))
        rate_slider.on_change('value_throttled', self.voltage_callback_on_change)

        noise_slider = Slider(title='Noise', value=group.noise, start=0, end=1, step=0.01, width=300)
        noise_slider.on_change('value_throttled', make_slider_callback('noise'))
        noise_slider.on_change('value_throttled', self.voltage_callback_on_change)

        weight_slider = Slider(title='Weight', value=group.weight, start=0, end=100, step=1, width=300)
        weight_slider.on_change('value_throttled', make_slider_callback('weight'))
        weight_slider.on_change('value_throttled', self.voltage_callback_on_change)

        if group.syn_type == 'AMPA_NMDA':
            logger.debug(f'gmax AMPA: {group.gmax_AMPA}, gmax NMDA: {group.gmax_NMDA}')
            gmax_ampa_slider = Slider(title='gmax_AMPA', value=group.gmax_AMPA, start=0, end=0.01, step=0.0001, width=300, format='0.00000')
            gmax_ampa_slider.on_change('value_throttled', make_slider_callback('gmax_AMPA'))
            gmax_ampa_slider.on_change('value_throttled', self.voltage_callback_on_change)

            gmax_nmda_slider = Slider(title='gmax_NMDA', value=group.gmax_NMDA, start=0, end=0.01, step=0.0001, width=300, format='0.00000')
            gmax_nmda_slider.on_change('value_throttled', make_slider_callback('gmax_NMDA'))
            gmax_nmda_slider.on_change('value_throttled', self.voltage_callback_on_change)

            gmax_sliders = [gmax_ampa_slider, gmax_nmda_slider]

            tau_rise_ampa_slider = Slider(title='tau_rise_AMPA', value=group.tau_rise_AMPA, start=0, end=10, step=0.01, width=150)
            tau_rise_ampa_slider.on_change('value_throttled', make_slider_callback('tau_rise_AMPA'))
            tau_rise_ampa_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_decay_ampa_slider = Slider(title='tau_decay_AMPA', value=group.tau_decay_AMPA, start=0, end=10, step=0.01, width=150)
            tau_decay_ampa_slider.on_change('value_throttled', make_slider_callback('tau_decay_AMPA'))
            tau_decay_ampa_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_rise_nmda_slider = Slider(title='tau_rise_NMDA', value=group.tau_rise_NMDA, start=0, end=10, step=0.01, width=150)
            tau_rise_nmda_slider.on_change('value_throttled', make_slider_callback('tau_rise_NMDA'))
            tau_rise_nmda_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_decay_nmda_slider = Slider(title='tau_decay_NMDA', value=group.tau_decay_NMDA, start=0, end=100, step=0.1, width=150)
            tau_decay_nmda_slider.on_change('value_throttled', make_slider_callback('tau_decay_NMDA'))
            tau_decay_nmda_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_sliders = column(row(tau_rise_ampa_slider, tau_decay_ampa_slider), row(tau_rise_nmda_slider, tau_decay_nmda_slider))

        else:
            logger.debug(f'gmax: {group.gmax}')
            gmax_slider = Slider(title='gmax', value=group.gmax, start=0, end=0.01, step=0.0001, width=300, format='0.00000')
            gmax_slider.on_change('value_throttled', make_slider_callback('gmax'))
            gmax_slider.on_change('value_throttled', self.voltage_callback_on_change)
            gmax_sliders = [gmax_slider]

            tau_rise_slider = Slider(title='tau_rise', value=group.tau_rise, start=0, end=10, step=0.01, width=150)
            tau_rise_slider.on_change('value_throttled', make_slider_callback('tau_rise'))
            tau_rise_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_decay_slider = Slider(title='tau_decay', value=group.tau_decay, start=0, end=10, step=0.01, width=150)
            tau_decay_slider.on_change('value_throttled', make_slider_callback('tau_decay'))
            tau_decay_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_sliders = row(tau_rise_slider, tau_decay_slider)

        e_spinner = Spinner(title='E_syn', value=group.e, low=-100, high=100, step=1, width=50)
        e_spinner.on_change('value_throttled', make_slider_callback('e'))
        e_spinner.on_change('value_throttled', self.voltage_callback_on_change)
        spinners = [e_spinner]

        if group.syn_type == 'AMPA_NMDA' or group.syn_type == 'NMDA':
            gamma_spinner = Spinner(title='Gamma', value=group.gamma, low=0, high=1, step=0.001, width=100)
            gamma_spinner.on_change('value_throttled', make_slider_callback('gamma'))
            gamma_spinner.on_change('value_throttled', self.voltage_callback_on_change)
            mu_spinner = Spinner(title='Mu', value=group.mu, low=0, high=1, step=0.001, width=100)
            mu_spinner.on_change('value_throttled', make_slider_callback('mu'))
            mu_spinner.on_change('value_throttled', self.voltage_callback_on_change)

            spinners += [gamma_spinner, mu_spinner]

        range_slider = RangeSlider(title=f'Range', 
                                   start=0, 
                                   end=self.view.widgets.sliders['duration'].value, 
                                   value=(group.start, group.end), 
                                   step=1, 
                                   width=300)

        def range_slider_callback(attr, old, new):
            group.start = new[0]
            group.end = new[1]

        range_slider.on_change('value_throttled', range_slider_callback)
        range_slider.on_change('value_throttled', self.voltage_callback_on_change)

        
        self.view.DOM_elements['syn_group_panel'].children = [rate_slider, 
                                                              noise_slider, 
                                                              range_slider, 
                                                              weight_slider, 
                                                              *gmax_sliders,
                                                              tau_sliders,
                                                                row(spinners)]
                                                              
                                                              

    def select_synapse_type_callback(self, attr, old, new):
        if self.view.widgets.tabs['section'].active == 2:
            syn = self.selected_synapse
        self.view.widgets.selectors['syn_group'].options = [group.name for group in syn.groups]
        self.view.widgets.selectors['graph_param'].value = syn.name
        if self.view.widgets.selectors['syn_group'].options:
            self.view.widgets.selectors['syn_group'].value = self.view.widgets.selectors['syn_group'].options[-1]
        else:
            self.view.widgets.selectors['syn_group'].value = None
    
    def select_synapse_group_segs_in_graph(self):
        if self.view.widgets.selectors['syn_group'].options:
            group = self.selected_syn_group
            seg_names = [get_seg_name(seg) for seg in group.segments]
            indices = [i for i, name in enumerate(self.view.figures['graph'].renderers[0].node_renderer.data_source.data['name']) if name in seg_names]
            self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = indices
        else:
            self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = []


    def select_synapse_group_callback(self, attr, old, new):
        self.toggle_synapse_group_panel()
        self.select_synapse_group_segs_in_graph()

    @property
    def selected_param(self):
        return self.view.widgets.selectors['graph_param'].value

    @property
    def selected_channel(self):
        if self.view.widgets.tabs['channels'].visible:
            active_tab = self.view.widgets.tabs['channels'].tabs[self.view.widgets.tabs['channels'].active].title
            return self.model.channels[active_tab]
        else:
            suffix = self.selected_param.replace('gbar_', '')
            chs = [ch for ch in self.model.channels.values() if ch.suffix == suffix]
            return chs[0] if chs else self.model.capacitance

    # @property
    # def selected_domain(self):
    #     return self.view.widgets.selectors['domain'].labels[self.view.widgets.selectors['domain'].active]
    
    @property
    def selected_group(self):
        group_name = self.view.widgets.selectors['distribution'].value
        logger.debug(f'Selected group: {group_name}')
        ch = self.selected_channel
        logger.debug(f'Groups: {ch.groups}')
        group = ch.get_by_name(group_name)
        logger.debug(f'Group: {group}')
        return group

    @property
    def selected_syn_group(self):
        group_name = self.view.widgets.selectors['syn_group'].value
        syn = self.selected_synapse
        group = syn.get_by_name(group_name)
        return group
        
    def select_distribution_segs_in_graph(self):
        if self.view.widgets.selectors['distribution'].options:
            group = self.selected_group
            seg_names = [get_seg_name(seg) for seg in group.segments]
            indices = [i for i, name in enumerate(self.view.figures['graph'].renderers[0].node_renderer.data_source.data['name']) if name in seg_names]
            self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = indices            
        else:
            self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = []

    @log
    def select_distribution_callback(self, attr, old, new):
        self.toggle_group_panel()
        self.select_distribution_segs_in_graph()
        self.update_distribution_plot()

    

    def toggle_group_panel(self):

        group = self.selected_group
        if group is None:
            self.view.DOM_elements['distribution_panel'].children = []
            return

        def make_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                logger.info(f'Updating {group.distribution} with {slider_title}={new}')
                group.distribution.update(**{slider_title: new})
                group.apply()
                self.update_graph_param(group.param_name)
                self.update_distribution_plot()
            return slider_callback

        sliders = []
        for k, v in group.distribution.f.keywords.items():
            logger.info(f'Adding slider for {k} with value {v}')
            slider = SmartSlider(name=k, value=v)
            slider_callback = make_slider_callback(slider.title)
            slider.on_change('value_throttled', slider_callback)
            slider.on_change('value_throttled', self.voltage_callback_on_change)
            logger.info(f'Slider title is {slider.title}, value is {slider.value}')
            sliders.append(slider.get_widget())
        self.view.DOM_elements['distribution_panel'].children = sliders


    def record_callback(self, attr, old, new):
        if new:
            self.model.simulator.add_recording(seg=self.selected_segs[0])
            self.recorded_segments.append(self.selected_segs[0])
            self.update_graph_param('recordings')
        else:
            self.model.simulator.remove_recording(seg=self.selected_segs[0])
            self.recorded_segments.remove(self.selected_segs[0])
            self.update_graph_param('recordings')

    @log
    def record_from_all_callback(self, attr, old, new):
        if new:
            for seg in self.model.cell.segments.values():
                self.model.simulator.add_recording(seg=seg)
            self.update_graph_param('recordings')
        else:
            for seg in self.model.cell.segments.values():
                if seg not in self.recorded_segments:
                    self.model.simulator.remove_recording(seg=seg)
            self.update_graph_param('recordings')

    def iclamp_duration_callback(self, attr, old, new):
        seg = self.selected_segs[0]
        self.model.iclamps[seg].delay = new[0]
        self.model.iclamps[seg].dur = np.diff(new)

    @log
    def iclamp_amp_callback(self, attr, old, new):
        seg = self.selected_segs[0]
        unit = self.view.widgets.selectors['iclamp_amp_unit'].value
        amp = self.view.widgets.sliders['iclamp_amp'].value
        factor = {f'pA': 1e-12, f'nA': 1e-9, f'uA': 1e-6}[unit]
        self.model.iclamps[seg].amp = amp * factor * 1e9
        logger.debug(f'Amplitude of iclamp in {seg} set to {self.model.iclamps[seg].amp}')

    

    # def toggle_group_panel(self):

    #     group = self.selected_group
    #     if group is None:
    #         self.view.DOM_elements['distribution_ranges'].children = []
    #         self.view.DOM_elements['distribution_params'].children = []
    #         return
        
    #     if len(group.segments) == 1:
    #         self.view.DOM_elements['distribution_ranges'].children = []
    #         self.toggle_distribution_sliders(group)
    #         return

    #     range_slider = RangeSlider(title=f'Range {group.distribution}', start=0, end=group.max_distance, value=(group.start, group.end), step=0.1, width=200)

    #     def range_slider_callback(attr, old, new):
    #         group.start = new[0]
    #         group.end = new[1]
    #         param_name = self.selected_param
    #         ch = self.selected_channel
    #         domain = self.selected_domain
    #         ch.apply_groups(domain)
    #         self.update_graph_param(param_name)

    #     range_slider.on_change('value_throttled', range_slider_callback)

    #     type_selector = Select(title=f'Distribution type', value=group.distribution.f.func.__name__, options=['uniform', 'linear'])
        
    #     def selector_callback(attr, old, new):
    #         if new == 'uniform':
    #             group.distribution = Distribution('uniform', value=0)
    #         elif new == 'linear':
    #             group.distribution = Distribution('linear', slope=1, intercept=0)
    #         self.toggle_distribution_sliders(group)

    #     type_selector.on_change('value', selector_callback)
    #     widget = row(range_slider, type_selector)
    #     self.view.DOM_elements['distribution_ranges'].children = [widget]

    #     self.toggle_distribution_sliders(group)

    # def toggle_distribution_sliders(self, group):

    #     param_name = self.selected_param

    #     def slider_callback(attr, old, new):
    #         f_name = group.distribution.f.func.__name__
    #         group.distribution = Distribution(f_name, **{slider.children[1].title: slider.children[1].value for slider in sliders})
    #         logger.debug(f'Updated {group.distribution}')
    #         self.update_graph_param(param_name)

    #     sliders = []
    #     for k, v in group.distribution.f.keywords.items():
    #         # sliders.append(Slider(title=k, start=0, end=1, value=v, step=0.01))
    #         slider = SmartSlider(name=k, value=v)
    #         slider.on_change('value_throttled', slider_callback)
    #         slider.on_change('value_throttled', self.voltage_callback_on_change)
    #         sliders.append(slider.get_widget())
    #     self.view.DOM_elements['distribution_params'].children = sliders
    

    @log
    def reduce_subtree_callback(self, event):
        sec = self.selected_sec
        parent = sec.parentseg().sec
        segments_to_remove = [seg for sec in sec.subtree() for seg in sec]
        for ch in self.model.channels.values():
            for group in ch.groups:
                group.segments = [seg for seg in group.segments if seg not in segments_to_remove]
        self.model.reduce_subtree(sec)
        

        self.selected_secs = set()
        self.selected_segs = []
        self.points = self.get_pts3d()
        if hasattr(self.model.cell, 'segments'):
            del self.model.cell.segments
        if hasattr(self.model.cell, 'sections'):
            del self.model.cell.sections

        self.model.add_capacitance()

        self.create_cell_renderer()
        self.create_graph_renderer()
        self.add_lasso_callback()

        self.view.widgets.selectors['section'].options=[''] + list(self.model.cell.sections.keys())
        logger.debug(f"Section selector value: {self.view.widgets.selectors['section'].value}")


    def console_callback(self, attr, old, new):

        import io
        import sys

        # Redirect stdout to a string stream
        new = f"print({new})"
        logger.debug(f'Executing: {new}')
        sys.stdout = io.StringIO()
        try:
            exec(new)
        except Exception as e:
            print(str(e))
        # Get the output and reset stdout
        output = sys.stdout.getvalue()
        logger.debug(f'Output: {output}')
        sys.stdout = sys.__stdout__
        # Update the status bar with the output
        self.view.DOM_elements['status_bar'].text = output
        with remove_callbacks(self.view.DOM_elements['console']):
            self.view.DOM_elements['console'].value = ''
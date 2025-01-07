import numpy as np

from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

from logger import logger, decorator_logger

from bokeh.models import RangeSlider, Slider, Select
from bokeh.layouts import row, column



from bokeh_utils import AdjustableSpinner
from bokeh_utils import remove_callbacks

from bokeh.models import LogScale, LinearScale

from bokeh.models import ColumnDataSource

from bokeh.models import Slider, TabPanel, Tabs, Button, Spinner

from symfit import variables, parameters, Model, Fit, exp
from typing import List, Dict, Tuple
from bokeh.events import ButtonClick

from bokeh.palettes import Bokeh



from bokeh_utils import log



from presenter.io import IOMixin
from presenter.navigation import NavigationMixin
from presenter.validation import ValidationMixin

from presenter.cell_panel import CellMixin
from presenter.section_panel import SectionMixin
from presenter.graph_panel import GraphMixin
from presenter.simulation_panel import SimulationMixin
from presenter.channel_panel import ChannelMixin

from presenter.temp import TempMixin


class Presenter(IOMixin, NavigationMixin, 
                CellMixin, SectionMixin, GraphMixin, SimulationMixin, ChannelMixin, 
                ValidationMixin, TempMixin):

    def __init__(self, view, model):
        logger.debug('Initializing Presenter')
        super().__init__()
        self.view = view
        self.model = model

    @property
    def selected_mech_name(self):
        return self.view.widgets.selectors['mechanism'].value

    @property
    def selected_param_name(self):
        return self.view.widgets.selectors['graph_param'].value

    @property
    def selected_group_name(self):
        return self.view.widgets.selectors['group'].value

    # =================================================================
    # GROUPS TAB
    # =================================================================

    # -----------------------------------------------------------------
    # ADD / REMOVE GROUPS
    # -----------------------------------------------------------------

    def select_by_condition_callback(self, attr, old, new):
        """
        Selects segments by the condition specified in the text input.
        """
        sec_type = self.view.widgets.selectors['sec_type'].value
        select_by = self.view.widgets.selectors['select_by'].value
        condition = self.view.widgets.text['condition'].value

        # Verify the condition, only numbers and operators are allowed
        if not all(c.isdigit() or c in '<>=x-.' for c in condition.replace(' ', '')):
            logger.error('Invalid condition')
            return

        if sec_type == 'all':
            secs = self.model.sec_tree.sections
        else:
            secs = self.model.get_sections(lambda sec : sec.domain == sec_type)

        segs = [seg for sec in secs for seg in sec.segments]

        if condition:
            attr_map = {'dist': 'distance_to_root', 'diam': 'diam'}
            segs = [seg for seg in segs if eval(condition.replace('x', f'seg.{attr_map[select_by]}'))]

        seg_ids = [seg.idx for seg in segs]
        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = seg_ids


    def add_group_callback(self, event):

        group_name = self.view.widgets.text['group_name'].value
        nodes = list(self.selected_secs)[:]
        self.add_group(group_name, nodes)

        with remove_callbacks(self.view.widgets.text['group_name']):
            self.view.widgets.text['group_name'].value = ''


    @log   
    def add_group(self, group_name, nodes):
        """
        Adds a group of nodes (sections) to the model.
        """
        logger.debug(f'Adding group "{group_name}" with {len(nodes)} nodes')
        self.model.add_group(group_name, nodes)
        self._update_group_selector_widget(group_name)
        self._toggle_group_panel(group_name)


    def _update_group_selector_widget(self, group_name=None):
        """
        Updates the selectors['group'] widget options when a group is added or removed.
        """
        with remove_callbacks(self.view.widgets.selectors['group']):
            self.view.widgets.selectors['group'].options = list(self.model.groups.keys())
            self.view.widgets.selectors['group'].value = group_name


    def remove_group_callback(self, event):

        group_name = self.view.widgets.selectors['group'].value
        self.remove_group(group_name)


    @log   
    def remove_group(self, group_name):
        """
        Removes the group from the model.
        """
        self.model.remove_group(group_name)

        remaining_groups = list(self.model.groups.keys())
        group_name = remaining_groups[-1] if remaining_groups else None

        self._update_group_selector_widget(group_name)
        self._toggle_group_panel(group_name)


    # -----------------------------------------------------------------
    # SELECT GROUP / INSERT MECHANISMS
    # -----------------------------------------------------------------    


    def select_group_callback(self, attr, old, new):
        group_name = new
        self._select_group(group_name)


    @log
    def _select_group(self, group_name=None):
        """
        Selects the group sections and updates the widgets.
        """

        group_name = group_name or self.selected_group_name
        param_name = self.selected_param_name

        # Show group in the graph
        self._select_group_secs_in_graph(group_name)

        # Show group panel
        if self.view.widgets.tabs['section'].active == 1:
            self._toggle_group_panel(group_name)

        # Show distributed param panel
        if self.view.widgets.tabs['section'].active == 2:
            
            # Show distribution type
            with remove_callbacks(self.view.widgets.selectors['distribution_type']):    
                self.view.widgets.selectors['distribution_type'].value = self.model.distributed_params[param_name][group_name].function_name

            self._toggle_distributed_param_widget(param_name, group_name)
            
            self._update_distribution_plot(group_name)


    @log
    def _select_group_secs_in_graph(self, group_name):
        """
        Selects the segments in the graph that belong to group sections.
        """
        group = self.model.groups[group_name]
        logger.debug(f'Selected group {group_name} with {(group.sections)} sections')
        seg_ids = [seg.idx for sec in group.sections for seg in sec.segments]

        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = seg_ids


    @log
    def _toggle_group_panel(self, group_name):
        """
        Updates multichoice['mechanisms']
        """
        self._update_inserted_mechnaisms_widget(group_name)


    @log
    def _update_inserted_mechnaisms_widget(self, group_name):
        """
        Updates the multichoice['mechanisms'] widget on group selection.
        """
        group = self.model.groups[group_name]
        with remove_callbacks(self.view.widgets.multichoice['mechanisms']):
            mech_names = [
                mech_name for mech_name in group.mechanisms 
                if mech_name != 'Independent'
            ]
            self.view.widgets.multichoice['mechanisms'].value = mech_names

    
    # MECHANISMS ------------------------------------------------------

    
    @log
    def update_group_mechanisms_callback(self, attr, old, new):
        """
        Callback for the multiselect['mechanisms'] widget.
        Adds or removes mechanisms from the selected group based on the multiselect widget.
        """

        group_name = self.view.widgets.selectors['group'].value

        mechs_to_add = list(set(new).difference(set(old)))
        mechs_to_remove = list(set(old).difference(set(new)))

        if mechs_to_remove:
            logger.debug(f'Mech to remove: {mechs_to_remove}')
            mech_name = mechs_to_remove[0]
            self.uninsert_mech(mech_name, group_name)
        if mechs_to_add:
            logger.debug(f'Mech to add: {mechs_to_add}')
            mech_name = mechs_to_add[0]
            self.insert_mech(mech_name, group_name)
    

    def insert_mech(self, mech_name, group_name):
        """
        Inserts the mechanisms to the groups.
        """
        self.model.insert_mechanism(mech_name, group_name)
        self._update_mechanism_selector_widget(group_name)


    def uninsert_mech(self, mech_name, group_name):
        """
        Uninserts the mechanisms from the groups.
        """
        self.model.uninsert_mechanism(mech_name, group_name)
        self._update_mechanism_selector_widget(group_name)


    def _update_mechanism_selector_widget(self, group_name):
        """
        Updates the multiselect['mechanisms'] widget with the mechanisms that 
        are available for the selected group.
        """
        group = self.model.groups[group_name]
        with remove_callbacks(self.view.widgets.selectors['mechanism']):
            self.view.widgets.selectors['mechanism'].options = group.mechanisms
            mech_name = group.mechanisms[0] if group.mechanisms else None
            self.view.widgets.selectors['mechanism'].value = mech_name

    
    # =================================================================
    # PARAMETERS TAB
    # =================================================================

    # -----------------------------------------------------------------
    # MECHANISMS 
    # -----------------------------------------------------------------

    @log
    def select_mechanism_callback(self, attr, old, new):
        """
        Callback for the multiselect['mechanisms'] widget.
        """
        mech_name = new

        avaliable_params = self.model.mechs_to_params[mech_name]
        param_name = avaliable_params[0]
        
        self.view.widgets.selectors['graph_param'].options = avaliable_params
        self.view.widgets.selectors['graph_param'].value = param_name

    
    # -----------------------------------------------------------------
    # PARAMETERS
    # -----------------------------------------------------------------


    @log
    def select_param_callback(self, attr, old, new):
        """
        Callback for the selectors['graph_param'] widget.
        Toggles the panel with widgets for the selected parameter.
        """
        param_name = new

        if self.view.widgets.tabs['section'].active == 2:

            # HANDLE DISTRIBUTED PARAM
            if param_name in self.model.distributed_params:
                self._toggle_distributed_param_panel(param_name)
                # self._update_distribution_plot(param_name)

            # HANDLE GLOBAL PARAM
            elif param_name in self.model.global_params:
                self._toggle_global_param_panel(param_name)

        self._update_graph_param(param_name, update_colors=True)


    # DISTRIBUTED PARAMS ------------------------------------------------------


    @log
    def _toggle_distributed_param_panel(self, param_name):
        """
        Toggles a panel with widgets for a distributed parameter.
        """
        logger.debug(f'Updating distributed param panel for {param_name}')
        self.view.DOM_elements['select_distribution_panel'].visible = True
        self.view.widgets.buttons['make_distributed'].visible = False
        self.view.widgets.buttons['make_global'].visible = True

        mech_name = self.view.widgets.selectors['mechanism'].value
        mech_groups = [group_name for group_name in self.model.groups.keys() 
                       if mech_name in self.model.groups[group_name].mechanisms]

        with remove_callbacks(self.view.widgets.selectors['group']):
            self.view.widgets.selectors['group'].options = mech_groups
            self.view.widgets.selectors['group'].value = mech_groups[0] if mech_groups else None

        self._select_group()


    @log
    def _toggle_distributed_param_widget(self, param_name, group_name):
        """
        Toggles the widgets for the distribution parameters.
        """

        def make_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                self.model.distributed_params[param_name][group_name].update_parameters(**{slider_title: new})
                self.model.distribute(param_name)
                self._update_graph_param(param_name)
                # self._update_distribution_plot(param_name)
            return slider_callback

        sliders = []
        for k, v in self.model.distributed_params[param_name][group_name].parameters.items():
            logger.info(f'Adding slider for {k} with value {v}')
            slider = AdjustableSpinner(title=k, value=v)
            slider_callback = make_slider_callback(slider.title)
            slider.on_change('value_throttled', slider_callback)
            slider.on_change('value_throttled', self.voltage_callback_on_change)
            logger.info(f'Slider title is {slider.title}, value is {slider.value}')
            sliders.append(slider.get_widget())
        self.view.DOM_elements['distribution_widgets_panel'].children = sliders


    def update_distribution_type_callback(self, attr, old, new):
        """
        Callback for the selectors['distribution_type'] widget.
        """
        group_name = self.selected_group_name
        param_name = self.selected_param_name
        function_name = new
        self.model.set_distributed_param(param_name, 
                                         group_name,
                                         distr_type=function_name)
        self._toggle_distributed_param_widget(param_name, group_name)
        # self._update_distribution_plot(param_name)

    
    def _update_distribution_plot(self, param_name):
        """
        Updates the distribution plot with the selected parameter.
        """

        SEC_TYPE_TO_IDX = {'soma': 0, 'axon': 1, 'dend': 2, 'apic': 3}

        selected_segs = self.selected_segs

        data = {'x': [seg.distance_to_root for seg in selected_segs],
                'y': [seg.get_param_value(param_name) for seg in selected_segs],
                'color': [self.view.theme.palettes['sec_type'][SEC_TYPE_TO_IDX[seg._section.domain]] for seg in selected_segs], 
                'label': [str(seg.idx) for seg in selected_segs]}

        self.view.sources['distribution'].data = data


    # GLOBAL PARAMS ------------------------------------------------------


    def _toggle_global_param_panel(self, param_name):
        """
        Toggles a panel for a global parameter.
        """
        logger.debug(f'Updating global param panel for {param_name}')
        self.view.DOM_elements['select_distribution_panel'].visible = False
        self.view.widgets.buttons['make_global'].visible = False
        self.view.widgets.buttons['make_distributed'].visible = True
        
        self._toggle_global_param_widget(param_name)


    def _toggle_global_param_widget(self, param_name):
        """
        Toggles a widget for a global parameter.
        """
        
        def make_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                self.model.set_global_param(param_name, new)
                self._update_graph_param(param_name)
            return slider_callback

        sliders = []
        value = self.model.global_params[param_name]

        slider = AdjustableSpinner(title=param_name, value=value)
        slider_callback = make_slider_callback(slider.title)
        slider.on_change('value_throttled', slider_callback)
        slider.on_change('value_throttled', self.voltage_callback_on_change)
        logger.info(f'Slider title is {slider.title}, value is {slider.value}')
        sliders.append(slider.get_widget())
        self.view.DOM_elements['distribution_widgets_panel'].children = sliders
    

    # BUTTONS ------------------------------------------------------


    def make_distributed_callback(self, event):
        """
        Makes the selected parameter distributed and toggles the distributed param panel.
        """
        param_name = self.selected_param_name
        logger.debug(f'Making {param_name} distributed')

        self.model.make_distributed(param_name)
        self._toggle_distributed_param_panel(param_name)
        self._update_graph_param(param_name)


    def make_global_callback(self, event):
        """
        Makes the selected parameter global and toggles the global param panel.
        """
        param_name = self.selected_param_name
        logger.debug(f'Making {param_name} global')

        self.model.make_global(param_name)
        self._toggle_global_param_panel(param_name)
        self._update_graph_param(param_name)


    #===============================
    # STIMULI TAB
    #===============================

    # -----------------------------------------------------------------
    # RECORDINGS
    # -----------------------------------------------------------------


    def record_callback(self, attr, old, new):
        seg = self.selected_segs[0]
        sec, loc = seg._section, seg.x
        if new:
            self.model.add_recording(sec, loc)
            self.recorded_segments.append(seg)
            self._update_graph_param('recordings')
        else:
            self.model.remove_recording(sec, loc)
            self.recorded_segments.remove(seg)
            self._update_graph_param('recordings')


    @log
    def record_from_all_callback(self, attr, old, new):
        if new:
            for seg in self.model.cell.segments.values():
                self.model.simulator.add_recording(seg=seg)
            self._update_graph_param('recordings')
        else:
            for seg in self.model.cell.segments.values():
                if seg not in self.recorded_segments:
                    self.model.simulator.remove_recording(seg=seg)
            self._update_graph_param('recordings')


    # -----------------------------------------------------------------
    # ICLAMPS
    # -----------------------------------------------------------------


    def iclamp_duration_callback(self, attr, old, new):
        seg = self.selected_segs[0]
        self.model.iclamps[seg].delay = new[0]
        self.model.iclamps[seg].dur = np.diff(new)


    @log
    def iclamp_amp_callback(self, attr, old, new):
        seg = self.selected_segs[0]
        # unit = self.view.widgets.selectors['iclamp_amp_unit'].value
        unit = 'pA'
        amp = self.view.widgets.sliders['iclamp_amp'].value
        factor = {f'pA': 1e-12, f'nA': 1e-9, f'uA': 1e-6}[unit]
        self.model.iclamps[seg].amp = amp * factor * 1e9
        logger.debug(f'Amplitude of iclamp in {seg} set to {self.model.iclamps[seg].amp}')


    # -----------------------------------------------------------------
    # SYNAPSES
    # -----------------------------------------------------------------

    @property
    def selected_population(self):
        syn_type = self.view.widgets.selectors['syn_type'].value
        pop_name = self.view.widgets.selectors['population'].value
        population = self.model.populations[syn_type].get(pop_name, None)
        return population

    
    # SELECT SYNAPSE TYPE ------------------------------------------------------

    def select_synapse_type_callback(self, attr, old, new):
        
        syn_type = self.view.widgets.selectors['syn_type'].value

        options = list(self.model.populations[syn_type].keys())
        self.view.widgets.selectors['population'].options = options
        self.view.widgets.selectors['graph_param'].value = syn_type
        self.view.widgets.selectors['population'].value = options[-1] if options else None
    

    # ADD / REMOVE POPULATION -----------------------------------------

    @log
    def add_population_callback(self, event):
        
        segments = self.selected_segs[:]
        syn_type = self.view.widgets.selectors['syn_type'].value
        N_syn = self.view.widgets.spinners['N_syn'].value
        
        self.model.add_population(
            segments=segments,
            N=N_syn,
            syn_type=syn_type
            )

        self._update_graph_param(syn_type)

        options = list(self.model.populations[syn_type])
        self.view.widgets.selectors['population'].options = options
        self.view.widgets.selectors['population'].value = options[-1]


    def remove_population_callback(self, event):
        
        pop_name = self.view.widgets.selectors['population'].value
        syn_type = self.view.widgets.selectors['syn_type'].value

        self.model.remove_population(pop_name)
        
        self._update_graph_param(syn_type)

        options = list(self.model.populations[syn_type])
        self.view.widgets.selectors['population'].options = options
        self.view.widgets.selectors['population'].value = options[-1] if options else None


    # SELECT POPULATION ------------------------------------------------------

    def select_population_callback(self, attr, old, new):
        self.toggle_population_panel()
        self.select_population_segs_in_graph()


    def toggle_population_panel(self):
        
        population = self.selected_population
        if population is None:
            self.view.DOM_elements['population_panel'].children = []
            return

        def make_kinetic_param_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                population.update_kinetic_params({slider_title: new})
            return slider_callback

        def make_input_param_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                population.update_input_params({slider_title: new})
            return slider_callback

        
        rate_slider = Slider(title='Rate', value=population.input_params['rate'], start=0.1, end=100, step=0.1, width=300)
        rate_slider.on_change('value_throttled', make_input_param_slider_callback('rate'))
        rate_slider.on_change('value_throttled', self.voltage_callback_on_change)

        noise_slider = Slider(title='Noise', value=population.input_params['noise'], start=0, end=1, step=0.01, width=300)
        noise_slider.on_change('value_throttled', make_input_param_slider_callback('noise'))
        noise_slider.on_change('value_throttled', self.voltage_callback_on_change)

        weight_slider = Slider(title='Weight', value=population.input_params['weight'], start=0, end=100, step=1, width=300)
        weight_slider.on_change('value_throttled', make_input_param_slider_callback('weight'))
        weight_slider.on_change('value_throttled', self.voltage_callback_on_change)

        if population.syn_type == 'AMPA_NMDA':
            logger.debug(f'gmax AMPA: {population.kinetic_params["gmax_AMPA"]}, gmax NMDA: {population.kinetic_params["gmax_NMDA"]}')
            gmax_ampa_slider = Slider(title='gmax_AMPA', value=population.kinetic_params['gmax_AMPA'], start=0, end=0.01, step=0.0001, width=300, format='0.00000')
            gmax_ampa_slider.on_change('value_throttled', make_kinetic_param_slider_callback('gmax_AMPA'))
            gmax_ampa_slider.on_change('value_throttled', self.voltage_callback_on_change)

            gmax_nmda_slider = Slider(title='gmax_NMDA', value=population.kinetic_params['gmax_NMDA'], start=0, end=0.01, step=0.0001, width=300, format='0.00000')
            gmax_nmda_slider.on_change('value_throttled', make_kinetic_param_slider_callback('gmax_NMDA'))
            gmax_nmda_slider.on_change('value_throttled', self.voltage_callback_on_change)

            gmax_sliders = [gmax_ampa_slider, gmax_nmda_slider]

            tau_rise_ampa_slider = Slider(title='tau_rise_AMPA', value=population.kinetic_params['tau_rise_AMPA'], start=0, end=10, step=0.01, width=150)
            tau_rise_ampa_slider.on_change('value_throttled', make_kinetic_param_slider_callback('tau_rise_AMPA'))
            tau_rise_ampa_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_decay_ampa_slider = Slider(title='tau_decay_AMPA', value=population.kinetic_params['tau_decay_AMPA'], start=0, end=10, step=0.01, width=150)
            tau_decay_ampa_slider.on_change('value_throttled', make_kinetic_param_slider_callback('tau_decay_AMPA'))
            tau_decay_ampa_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_rise_nmda_slider = Slider(title='tau_rise_NMDA', value=population.kinetic_params['tau_rise_NMDA'], start=0, end=10, step=0.01, width=150)
            tau_rise_nmda_slider.on_change('value_throttled', make_kinetic_param_slider_callback('tau_rise_NMDA'))
            tau_rise_nmda_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_decay_nmda_slider = Slider(title='tau_decay_NMDA', value=population.kinetic_params['tau_decay_NMDA'], start=0, end=100, step=0.1, width=150)
            tau_decay_nmda_slider.on_change('value_throttled', make_kinetic_param_slider_callback('tau_decay_NMDA'))
            tau_decay_nmda_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_sliders = column(row(tau_rise_ampa_slider, tau_decay_ampa_slider), row(tau_rise_nmda_slider, tau_decay_nmda_slider))

        else:
            logger.debug(f'gmax: {population.kinetic_params["gmax"]}')
            gmax_slider = Slider(title='gmax', value=population.kinetic_params['gmax'], start=0, end=0.01, step=0.0001, width=300, format='0.00000')
            gmax_slider.on_change('value_throttled', make_kinetic_param_slider_callback('gmax'))
            gmax_slider.on_change('value_throttled', self.voltage_callback_on_change)
            gmax_sliders = [gmax_slider]

            tau_rise_slider = Slider(title='tau_rise', value=population.kinetic_params['tau_rise'], start=0, end=10, step=0.01, width=150)
            tau_rise_slider.on_change('value_throttled', make_kinetic_param_slider_callback('tau_rise'))
            tau_rise_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_decay_slider = Slider(title='tau_decay', value=population.kinetic_params['tau_decay'], start=0, end=10, step=0.01, width=150)
            tau_decay_slider.on_change('value_throttled', make_kinetic_param_slider_callback('tau_decay'))
            tau_decay_slider.on_change('value_throttled', self.voltage_callback_on_change)

            tau_sliders = row(tau_rise_slider, tau_decay_slider)

        e_spinner = Spinner(title='E_syn', value=population.kinetic_params['e'], low=-100, high=100, step=1, width=50)
        e_spinner.on_change('value_throttled', make_kinetic_param_slider_callback('e'))
        e_spinner.on_change('value_throttled', self.voltage_callback_on_change)
        spinners = [e_spinner]

        if 'NMDA' in population.syn_type:
            gamma_spinner = Spinner(title='Gamma', value=population.kinetic_params['gamma'], low=0, high=1, step=0.001, width=100)
            gamma_spinner.on_change('value_throttled', make_kinetic_param_slider_callback('gamma'))
            gamma_spinner.on_change('value_throttled', self.voltage_callback_on_change)
            mu_spinner = Spinner(title='Mu', value=population.kinetic_params['mu'], low=0, high=1, step=0.001, width=100)
            mu_spinner.on_change('value_throttled', make_kinetic_param_slider_callback('mu'))
            mu_spinner.on_change('value_throttled', self.voltage_callback_on_change)

            spinners += [gamma_spinner, mu_spinner]

        range_slider = RangeSlider(title=f'Range', 
                                   start=0, 
                                   end=self.view.widgets.sliders['duration'].value, 
                                   value=(population.input_params['start'], population.input_params['end']), 
                                   step=1, 
                                   width=300)

        def range_slider_callback(attr, old, new):
            population.update_input_params({'start': new[0], 'end': new[1]})

        range_slider.on_change('value_throttled', range_slider_callback)
        range_slider.on_change('value_throttled', self.voltage_callback_on_change)

        
        self.view.DOM_elements['population_panel'].children = [rate_slider, 
                                                              noise_slider, 
                                                              range_slider, 
                                                              weight_slider, 
                                                              *gmax_sliders,
                                                              tau_sliders,
                                                                row(spinners)]
                                                              
                                                              
    def select_population_segs_in_graph(self):
        if self.view.widgets.selectors['population'].options:
            population = self.selected_population
            seg_ids = [seg.idx for seg in population.segments]
            self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = seg_ids
        else:
            self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = []


    # =================================================================
    # CHANNELS TAB
    # =================================================================


    @property
    def selected_channel(self):
        if self.view.widgets.selectors['channel'].visible:
            ch_name = self.view.widgets.selectors['channel'].value
            return self.model.channels.get(ch_name, None)
        else:
            suffix = self.selected_param_name.replace('gbar_', '')
            chs = [ch for ch in self.model.channels.values() if ch.suffix == suffix]
            return chs[0] if chs else self.model.capacitance

    @log
    def select_channel_callback(self, attr, old, new):
        self.toggle_channel_panel()

    def toggle_channel_panel(self):
        logger.debug(f'Toggling channel')
        ch = self.selected_channel
        panel = self.create_channel_panel(ch)
        # delete previous widgets:
        for child in self.view.DOM_elements['channel_menu'].children[-1].children:
            logger.debug(f'Child {child}')
            if hasattr(child, 'children'):
                for ch in child.children:
                    logger.debug(f'Ch {ch}')
                    if hasattr(ch, 'children'):
                        for c in ch.children:
                            logger.debug(f'C {c}')
                            c.destroy()
                    ch.destroy()
            child.destroy()
        self.view.DOM_elements['channel_menu'].children[-1] = panel
        

    # =================================================================
    # MORPHOLOGY TAB
    # =================================================================  


    def delete_subtree_callback(self, event):
        sec = self.selected_sec
        parent = sec.parentseg().sec
        logger.debug(sec.parentseg())
        segments_to_remove = [seg for sec in sec.subtree() for seg in sec]
        # Remove the segments from channel groups
        for ch in self.model.channels.values():
            groups_to_remove = []
            for group in ch.groups:
                group.segments = [seg for seg in group.segments if seg not in segments_to_remove]
                logger.debug(f'Group {group.name} has {len(group.segments)} segments')
                if len(group.segments) == 0:
                    groups_to_remove.append(group)
            for group in groups_to_remove:
                ch.remove_group(group)
        # Remove the segments from capacitance the same way
        groups_to_remove = []
        for group in self.model.capacitance.groups:
            group.segments = [seg for seg in group.segments if seg not in segments_to_remove]
            if len(group.segments) == 0:
                groups_to_remove.append(group)
        for group in groups_to_remove:
            self.model.capacitance.remove_group(group)

        self.model.delete_subtree(sec)
        self.selected_secs = set()
        self.selected_segs = []
        self.points = self.get_pts3d()
        if hasattr(self.model.cell, 'segments'):
            del self.model.cell.segments
        if hasattr(self.model.cell, 'sections'):
            del self.model.cell.sections

        self.create_cell_renderer()
        self.create_graph_renderer()
        self.add_lasso_callback()

        self.view.widgets.selectors['section'].options=[''] + list(self.model.cell.sections.keys())
        

    @log
    def reduce_subtree_callback(self, event):
        sec = self.selected_sec
        parent = sec.parentseg().sec
        logger.debug(sec.parentseg())
        segments_to_remove = [seg for sec in sec.subtree() for seg in sec]
        # Remove the segments from channel groups
        for ch in self.model.channels.values():
            groups_to_remove = []
            for group in ch.groups:
                group.segments = [seg for seg in group.segments if seg not in segments_to_remove]
                logger.debug(f'Group {group.name} has {len(group.segments)} segments')
                if len(group.segments) == 0:
                    groups_to_remove.append(group)
            for group in groups_to_remove:
                ch.remove_group(group)
        # Remove the segments from capacitance the same way
        groups_to_remove = []
        for group in self.model.capacitance.groups:
            group.segments = [seg for seg in group.segments if seg not in segments_to_remove]
            if len(group.segments) == 0:
                groups_to_remove.append(group)
        for group in groups_to_remove:
            self.model.capacitance.remove_group(group)


        self.model.reduce_subtree(sec)

        # Handle the out of group segments
        out_of_group_segments = [seg for seg in sec]
        for seg in out_of_group_segments:
            # Create a group for each segment with a default uniform distribution
            for ch in self.model.channels.values():
                ch.add_group([seg], f'gbar_{ch.suffix}', Distribution('uniform', value=getattr(seg, f'gbar_{ch.suffix}')))
            
        # Assumes that the capacitance is the same for all segments in the subtree
        self.model.capacitance.add_group(out_of_group_segments, 'cm', Distribution('uniform', value=out_of_group_segments[0].cm))

        self.selected_secs = set()
        self.selected_segs = []
        self.points = self.get_pts3d()
        if hasattr(self.model.cell, 'segments'):
            del self.model.cell.segments
        if hasattr(self.model.cell, 'sections'):
            del self.model.cell.sections

        # self.model.add_capacitance()        

        self.create_cell_renderer()
        self.create_graph_renderer()
        self.add_lasso_callback()

        self.view.widgets.selectors['section'].options=[''] + list(self.model.cell.sections.keys())
        logger.debug(f"Section selector value: {self.view.widgets.selectors['section'].value}")


    # =================================================================
    # MISC
    # =================================================================


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
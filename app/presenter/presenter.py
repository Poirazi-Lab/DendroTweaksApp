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
        # CellMixin.__init__(self)
        # SectionMixin.__init__(self)
        # GraphMixin.__init__(self)
        # SimulationMixin.__init__(self)
        # NavigationMixin.__init__(self)
        super().__init__()
        self.view = view
        self.model = model

    # =================================================================
    # GROUP TAB
    # =================================================================

    # -----------------------------------------------------------------
    # ADD REMOVE PANEL
    # -----------------------------------------------------------------

    # SELECT SECTIONS TO CREATE A GROUP

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

    # ADD / REMOVE GROUP

    def add_group_callback(self, event):

        group_name = self.view.widgets.text['group_name'].value
        nodes = list(self.selected_secs)[:]
        self.add_group(group_name, nodes)

        # Clear the group name input
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
    # GROUP PANEL
    # -----------------------------------------------------------------

    
    # MECHANISMS ------------------------------------------------------
    # multiselect['mechanisms']
    
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
        # self._update_available_params_widget(mech_name, group_name)


    # def _update_available_params_widget(self, mech_name, group_name):
    #     """
    #     Updates the multiselect['params'] widget with the parameters that 
    #     are available for the selected group.
    #     The list depends on what mechanisms were inserted into the group sections
    #     with the multiselect['mechanisms'] widget.
    #     """
    #     group = self.model.groups[group_name]

    #     # available_parameters = ['cm', 'Ra'] + [
    #     #     param for mech in group_mechanisms.values()
    #     #     for param in mech.parameters.keys()
    #     # ]
        
    #     available_parameters = self.model.groups_to_parameters[group_name][mech_name]

    #     group_parameters = [param_name for param_name in available_parameters
    #                        if isinstance(self.model.parameters[mech_name][param_name], dict)]

    #     # group_parameters = list(group.parameters.keys())

    #     with remove_callbacks(self.view.widgets.multichoice['params']):
    #         self.view.widgets.multichoice['params'].options = available_parameters
    #         self.view.widgets.multichoice['params'].value = group_parameters

    # PARAMETERS ------------------------------------------------------
    # multiselect['params']
    
    # @log
    # def update_group_parameters_callback(self, attr, old, new):
    #     """
    #     Updates the multiselect['params'] widget.
    #     Makes selected parameters available to be distributed within the group.
    #     """

    #     group_name = self.view.widgets.selectors['group'].value

    #     params_to_add = list(set(new).difference(set(old)))
    #     params_to_remove = list(set(old).difference(set(new)))

    #     if params_to_remove:
    #         param_name = params_to_remove[0]
    #         self.model.groups[group_name].remove_parameter(param_name)
    #         # param → ALL groups
    #         self.distribute_params(param_names=[param_name]) 
    #         self._update_graph_param(param_name, update_colors=False)

    #     if params_to_add:
    #         param_name = params_to_add[0]
    #         self.model.groups[group_name].add_parameter(param_name)
    #         logger.debug(f'Added {param_name} to {group_name}')
    #         # param → group
    #         self.distribute_params(param_names=[param_name], 
    #                                group_names=[group_name])
    #         self._update_graph_param(param_name, update_colors=False)
        
    # @log
    # def distribute_params(self, param_names:List[str] = None, 
    #                       group_names:List[str] = None):
    #     """
    #     Distributes the parameters to the groups.
    #     """

    #     self.model.distribute_params(param_names, group_names)


    
    # ===============================
    # DISTRIBUTION TAB
    # ===============================

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

        



    ## SELECTORS

    @property
    def selected_param(self):
        return self.view.widgets.selectors['graph_param'].value

    @property
    def selected_group(self):
        # group_name = self.view.widgets.selectors['group'].value
        # logger.debug(f'Selected group: {group_name}')
        # group = self.model.groups.get(group_name, None)
        # return group
        return self.view.widgets.selectors['group'].value

    def make_distributed_callback(self, event):
        param_name = self.selected_param
        logger.debug(f'Making {param_name} distributed')
        self.model.make_distributed(param_name)
        self._update_graph_param(param_name)

        self._toggle_distributed_param_panel(param_name)

    def make_global_callback(self, event):
        param_name = self.selected_param
        logger.debug(f'Making {param_name} global')
        # self.model.make_global(param_name)

    ### selectors['graph_param']

    @log
    def select_param_callback(self, attr, old, new):
        """
        Callback for the selectors['graph_param'] widget.
        Show the panel with distribution sliders for the 
        selected range parameter.
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

    # ****************************************************************
    # DISTRIBUTED PARAMS
    # ****************************************************************

    @log
    def _toggle_distributed_param_panel(self, param_name):
        """
        Updates the panel with the sliders for the distributed parameters.
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


        # # Show distribution type
        # with remove_callbacks(self.view.widgets.selectors['distribution_type']):    
        #     self.view.widgets.selectors['distribution_type'].value = self.model.distributed_params[param_name][group_name].function_name

        # # Show distribution sliders
        # self._toggle_distributed_param_widget(param_name, group_name)

    @log
    def _toggle_distributed_param_widget(self, param_name, group_name):

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

    ### selectors['distribution']

    def update_distribution_type_callback(self, attr, old, new):
        """
        Callback for the selectors['distribution_type'] widget.
        """
        group_name = self.selected_group
        param_name = self.selected_param
        function_name = new
        self.model.set_distributed_param(param_name, 
                                         group_name,
                                         distr_type=function_name)
        self._toggle_distributed_param_widget(param_name, group_name)
        # self._update_distribution_plot(param_name)

    
    def _update_distribution_plot(self, param_name):

        SEC_TYPE_TO_IDX = {'soma': 0, 'axon': 1, 'dend': 2, 'apic': 3}

        selected_segs = self.selected_segs

        data = {'x': [seg.distance_to_root for seg in selected_segs],
                'y': [seg.get_param_value(param_name) for seg in selected_segs],
                'color': [self.view.theme.palettes['sec_type'][SEC_TYPE_TO_IDX[seg._section.domain]] for seg in selected_segs], 
                'label': [str(seg.idx) for seg in selected_segs]}

        self.view.sources['distribution'].data = data

    # ****************************************************************
    # GLOBAL PARAMS
    # ****************************************************************

    def _toggle_global_param_panel(self, param_name):
        """
        Updates the panel with the sliders for the global parameters.
        """
        logger.debug(f'Updating global param panel for {param_name}')
        self.view.DOM_elements['select_distribution_panel'].visible = False
        self.view.widgets.buttons['make_global'].visible = False
        self.view.widgets.buttons['make_distributed'].visible = True
        
        self._toggle_global_param_widget(param_name)

    def _toggle_global_param_widget(self, param_name):
        
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
    
    # @log
    # def _update_group_selector_on_param_selection(self, param_name):
    #     """
    #     Update selectors['group'] when selectors['graph_param'] is updated
    #     to show only the groups that contain the selected parameter.
    #     """
    #     if self.view.widgets.tabs['section'].active == 2:
    #         groups_containing_param = self.model.parameters_to_groups[param_name]
    #         self.view.widgets.selectors['group'].options = groups_containing_param
    #         if not self.view.widgets.selectors['group'].value in groups_containing_param:
    #             group_name = groups_containing_param[0] or None
    #             self.view.widgets.selectors['group'].value = group_name

    # @log
    # def _update_param_selector_on_group_selection(self, group_name):
    #     """
    #     Update selectors['graph_param'] when selectors['group'] is updated
    #     to show only the parameters that are available for the selected group.
    #     """
    #     if self.view.widgets.tabs['section'].active == 2:
    #         group = self.model.groups[group_name]
    #         available_params = list(group.parameters.keys())
    #         self.view.widgets.selectors['graph_param'].options = available_params
    #         if not self.view.widgets.selectors['graph_param'].value in available_params:
    #             param_name = available_params[0] or None
    #             self.view.widgets.selectors['graph_param'].value = param_name


    ### selectors['group']
    
    
    def select_group_callback(self, attr, old, new):
        group_name = new
        self._select_group(group_name)

    @log
    def _select_group(self, group_name=None):

        group_name = group_name or self.selected_group
        param_name = self.selected_param

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
        group = self.model.groups[group_name]
        logger.debug(f'Selected group {group_name} with {(group.sections)} sections')
        seg_ids = [seg.idx for sec in group.sections for seg in sec.segments]

        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = seg_ids
        # else:
        #     self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = []

    @log
    def _toggle_group_panel(self, group_name):
        """
        Updates two widgets: multichoice['mechanisms'] and 
        multichoice['params']
        """
        self._update_inserted_mechnaisms_widget(group_name)
        # self._update_available_params_widget(group_name)

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










    #===============================
    # SYNAPSE TAB
    #===============================


    @property
    def selected_synapse(self):
        return self.model.synapses[self.view.widgets.selectors['syn_type'].value]
    

    @log
    def add_synapse_group_callback(self, event):
        
        segments = self.selected_segs
        syn = self.selected_synapse
        N_syn = self.view.widgets.spinners['N_syn'].value
        syn.add_group(segments=segments, N_syn=N_syn)

        self._update_graph_param(syn.name)

        self.view.widgets.selectors['syn_group'].options = [group.name for group in syn.groups]
        self.view.widgets.selectors['syn_group'].value = syn.groups[-1].name

    def remove_synapse_group_callback(self, event):
        syn = self.selected_synapse
        group = self.selected_syn_group
        
        logger.debug(f'Removing group {group.name} from {syn.name}')

        syn.remove_group(group)
        self._update_graph_param(syn.name)

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
    def selected_channel(self):
        if self.view.widgets.selectors['channel'].visible:
            ch_name = self.view.widgets.selectors['channel'].value
            return self.model.channels.get(ch_name, None)
        else:
            suffix = self.selected_param.replace('gbar_', '')
            chs = [ch for ch in self.model.channels.values() if ch.suffix == suffix]
            return chs[0] if chs else self.model.capacitance

    # @property
    # def selected_domain(self):
    #     return self.view.widgets.selectors['domain'].labels[self.view.widgets.selectors['domain'].active]
    


    @property
    def selected_syn_group(self):
        group_name = self.view.widgets.selectors['syn_group'].value
        syn = self.selected_synapse
        group = syn.get_by_name(group_name)
        return group
        
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
    #         self._update_graph_param(param_name)

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
    #         self._update_graph_param(param_name)

    #     sliders = []
    #     for k, v in group.distribution.f.keywords.items():
    #         # sliders.append(Slider(title=k, start=0, end=1, value=v, step=0.01))
    #         slider = SmartSlider(name=k, value=v)
    #         slider.on_change('value_throttled', slider_callback)
    #         slider.on_change('value_throttled', self.voltage_callback_on_change)
    #         sliders.append(slider.get_widget())
    #     self.view.DOM_elements['distribution_params'].children = sliders

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
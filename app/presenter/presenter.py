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

# TODO: Remove this when dd installed through pip
import sys
sys.path.append('app/src')
from dendrotweaks.membrane import StandardIonChannel

class Presenter(IOMixin, NavigationMixin, 
                CellMixin, SectionMixin, GraphMixin, SimulationMixin, ChannelMixin, 
                ValidationMixin):

    def __init__(self, path_to_data, view=None, model=None, simulator='NEURON'):
        logger.debug('Initializing Presenter')
        super().__init__()
        self.path_to_data = path_to_data
        self.view = view
        self.view._presenter = self
        self.model = model
        self._simulator = simulator
        self.config = None

    @property
    def selected_mech_name(self):
        return self.view.widgets.selectors['mechanism'].value

    @property
    def selected_param_name(self):
        return self.view.widgets.selectors['param'].value

    @property
    def selected_group_name(self):
        return self.view.widgets.selectors['assigned_group'].value

    def update_model_version_callback(self, attr, old, new):
        self.model.version = new

    # =================================================================
    # MORPHOLOGY TAB
    # =================================================================

    # -----------------------------------------------------------------
    # DOMAIN
    # -----------------------------------------------------------------

    def define_domain_callback(self, attr, old, new):
        """
        Callback for the buttons['create_domain'] widget.
        """
        # GET VIEW
        domain_name = new
        # SET MODEL
        self.model.define_domain(domain_name, sections=self.selected_secs)
        # SET VIEW
        self._update_graph_param('domain')
        self._create_cell_renderer()
        self.view.widgets.selectors['domain'].options = list(self.model.domains.keys())
        self.view.widgets.selectors['domain'].value = domain_name
        
        self._update_multichoice_domain_widget()
            
        with remove_callbacks(self.view.widgets.selectors['group']):
            self.view.widgets.selectors['group'].options = list(self.model.groups.keys())
            self.view.widgets.selectors['group'].value = domain_name

        domains_to_sec_ids = {domain.name: sorted([str(sec.idx) for sec in domain.sections], key=lambda x: int(x)) 
                             for domain in self.model.domains.values()}
        self.view.widgets.selectors['section'].options = domains_to_sec_ids

        # TODO: Need a warning here if some mechanisms are already inserted
        # as they will be removed
        self.update_status_message(f'Domain {domain_name} created.', status='success')

    def _update_multichoice_domain_widget(self):
        mech_name = self.view.widgets.selectors['mechanism_to_insert'].value
        available_domains = list(self.model.domains.keys()) if self.model.sec_tree else []
        mech_domains = list(self.model.mechs_to_domains.get(mech_name, []))
        logger.debug(f'Available domains: {available_domains}, mech domains: {mech_domains}')
        with remove_callbacks(self.view.widgets.multichoice['domains']):
            self.view.widgets.multichoice['domains'].options = list(self.model.domains.keys())
            self.view.widgets.multichoice['domains'].value = mech_domains

    def _update_multichoice_mechanisms_widget(self):
        added_mechs = list(self.model.mechanisms)
        with remove_callbacks(self.view.widgets.multichoice['mechanisms']):
            self.view.widgets.multichoice['mechanisms'].options = added_mechs
            self.view.widgets.multichoice['mechanisms'].value = added_mechs

    def update_status_message(self, message, status='info'):
        color = self.view.theme.status_colors[status]
        self.view.DOM_elements['status'].text = f'<span style="color: {color};">{message}</span>'

    # =================================================================
    # GROUPS TAB
    # =================================================================

    # -----------------------------------------------------------------
    # INSERT MECHANISMS TO DOMAINS
    # -----------------------------------------------------------------

    def select_domain_segments_callback(self, attr, old, new):
        """
        Callback for the selectors['subtree'] widget.
        """
        # GET VIEW
        domain_name = new
        self._select_domain_segs_in_graph(domain_names=[domain_name])

    @log
    def _select_domain_segs_in_graph(self, domain_names):
        """
        Selects the segments in the graph that belong to the domain.
        """
        # GET MODEL
        sections = self.model.get_sections(lambda sec : sec.domain in domain_names)
        seg_ids = [seg.idx for sec in sections for seg in sec.segments]
        # SET VIEW
        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = seg_ids
        

    # -----------------------------------------------------------------
    # ADD / REMOVE GROUPS
    # -----------------------------------------------------------------


    def select_group_segments_callback(self, attr, old, new):
        """
        Selects segments by the condition specified in multichoice['group_domains'],
        the selectors['select_by'], ['condition_min'], ['condition_max'].
        """
        # GET VIEW
        domains = self.view.widgets.multichoice['group_domains'].value
        select_by = self.view.widgets.selectors['select_by'].value
        min_val = self.view.widgets.spinners['condition_min'].value
        max_val = self.view.widgets.spinners['condition_max'].value

        # GET MODEL
        if select_by == 'distance':
            condition = lambda seg: seg.domain in domains and \
                        (min_val is None or seg.path_distance() >= min_val) and \
                        (max_val is None or seg.path_distance() <= max_val)
        elif select_by == 'domain_distance':
            condition = lambda seg: seg.domain in domains and \
                        (min_val is None or seg.path_distance(within_domain=True) >= min_val) and \
                        (max_val is None or seg.path_distance(within_domain=True) <= max_val)
        elif select_by == 'diam':
            condition = lambda seg: seg.domain in domains and \
                        (min_val is None or seg.diam >= min_val) and \
                        (max_val is None or seg.diam <= max_val)
        elif select_by == 'section_diam':
            condition = lambda seg: seg.domain in domains and \
                        (min_val is None or seg._section.diam >= min_val) and \
                        (max_val is None or seg._section.diam <= max_val)
        
        segs = [seg for seg in self.model.seg_tree.segments if condition(seg)]
        seg_ids = [seg.idx for seg in segs]
        
        # SET VIEW
        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = seg_ids


    def add_group_callback(self, event):

        # GET VIEW
        group_name = self.view.widgets.text['group_name'].value
        domains = self.view.widgets.multichoice['group_domains'].value
        select_by = self.view.widgets.selectors['select_by'].value
        min_value = self.view.widgets.spinners['condition_min'].value
        max_value = self.view.widgets.spinners['condition_max'].value
            
        # SET MODEL
        self.model.add_group(group_name, domains, 
                             select_by=select_by,
                             min_value=min_value, 
                             max_value=max_value)

        # SET VIEW
        self._reset_group_filter_widgets()
        self._set_group_selector_widget(group_name)
        

    def _reset_group_filter_widgets(self):
        with remove_callbacks(self.view.widgets.text['group_name']):
            self.view.widgets.text['group_name'].value = ''
        with remove_callbacks(self.view.widgets.selectors['select_by']):
            self.view.widgets.selectors['select_by'].value = 'dist'
        with remove_callbacks(self.view.widgets.multichoice['group_domains']):
            self.view.widgets.multichoice['group_domains'].value = []
        with remove_callbacks(self.view.widgets.spinners['condition_min']):
            self.view.widgets.spinners['condition_min'].value = None
        with remove_callbacks(self.view.widgets.spinners['condition_max']):
            self.view.widgets.spinners['condition_max'].value = None


    def _set_group_selector_widget(self, group_name=None):
        """
        Updates the selectors['group'] widget options when a group is added or removed.
        """
        options = list(self.model.groups.keys())
        self.view.widgets.selectors['group'].options = options
        self.view.widgets.selectors['group'].value = group_name or (options[-1] if options else None)

    # -----------------------------------------------------------------
    # SELECT / REMOVE GROUP
    # -----------------------------------------------------------------    


    def select_group_segs_callback(self, attr, old, new):
        
        group_name = new
        self._select_group_segs_in_graph(group_name)


    @log
    def _select_group_segs_in_graph(self, group_name):
        """
        Selects the segments in the graph that belong to group sections.
        """
        # GET MODEL
        group_segments = self.model.get_segments([group_name])
        logger.debug(f'Group {group_name} segments: {len(group_segments)}')
        seg_ids = [seg.idx for seg in group_segments]
        logger.debug(f'Selected segments: {seg_ids}')

        # SET VIEW
        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = seg_ids


    def remove_group_callback(self, event):
        """
        Callback for the buttons['remove_group'] widget.
        """
        # GET VIEW
        group_name = self.view.widgets.selectors['group'].value
        # SET MODEL
        self.model.remove_group(group_name)
        # SET VIEW
        self._set_group_selector_widget()

    
    # =================================================================
    # MECHANISMS TAB
    # =================================================================

    # -----------------------------------------------------------------
    # INSERT MECHANISMS TO DOMAINS
    # -----------------------------------------------------------------

    def select_mechanism_to_insert_callback(self, attr, old, new):
        """
        Callback for the multiselect['mechanisms'] widget.
        """
        self._select_mechanism_to_insert()


    @log
    def _select_mechanism_to_insert(self):
        
        self._update_multichoice_domain_widget()

        mech_domains = self.view.widgets.multichoice['domains'].value
        self._select_domain_segs_in_graph(domain_names=mech_domains)


    @log
    def insert_mechanism_callback(self, attr, old, new):
        """
        Callback for the multiselect['mechanisms'] widget.
        Adds or removes mechanisms from the selected group based on the multiselect widget.
        """

        mech_name = self.view.widgets.selectors['mechanism_to_insert'].value
        domains_to_add = list(set(new).difference(set(old)))
        domains_to_remove = list(set(old).difference(set(new)))

        if domains_to_remove:
            logger.debug(f'Domains from which to remove: {domains_to_remove}')
            domain_name = domains_to_remove[0]
            self.model.uninsert_mechanism(mech_name, domain_name)
            # TODO: update the list of inserted mechanisms (Params tab)
        if domains_to_add:
            logger.debug(f'Domains to which to add: {domains_to_add}')
            domain_name = domains_to_add[0]
            self.model.insert_mechanism(mech_name, domain_name)

        self._select_domain_segs_in_graph(domain_names=new)
        self._update_mechanism_selector_widget()


    def _update_mechanism_selector_widget(self):
        """
        Updates the selectors['mechanism'] widget options when a mechanism is added or removed.
        """
        available_mechs = list(self.model.mechs_to_params.keys()) # both inserted and with range params
        with remove_callbacks(self.view.widgets.selectors['mechanism']):
            self.view.widgets.selectors['mechanism'].options = available_mechs
            self.view.widgets.selectors['mechanism'].value = available_mechs[-1] if available_mechs else None
        

    # =================================================================
    # PARAMETERS TAB
    # =================================================================

    # -----------------------------------------------------------------
    # MECHANISMS 
    # -----------------------------------------------------------------

    def select_mechanism_callback(self, attr, old, new):
        """
        Callback for the selectors['mechanism'] widget.
        """
        mech_name = new
        self._select_mechanism(mech_name)
        if self.view.widgets.switches['show_kinetics'].active:
            self.view.sources['inf_orig'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
            self.view.sources['tau_orig'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
            self.view.sources['inf_fit'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
            self.view.sources['tau_fit'].data = {'xs': [], 'ys': [], 'label': [], 'color': []}
            self._toggle_kinetic_plots(mech_name)
            


    @log
    def _select_mechanism(self, mech_name):
        logger.debug(f'Selected mechanism: {mech_name}')

        self._update_param_selector_widget(mech_name)


    @log
    def _update_param_selector_widget(self, mech_name):

        available_params = self.model.mechs_to_params.get(mech_name, [])
        param_name = available_params[0]
        with remove_callbacks(self.view.widgets.selectors['param']):
            self.view.widgets.selectors['param'].options = available_params
            self.view.widgets.selectors['param'].value = param_name
        self._select_param(param_name)

    def toggle_kinetic_plots_callback(self, attr, old, new):
        """
        Callback for the switches['show_kinetics'] widget.
        """
        if not new:
            self.view.figures['inf'].visible = False
            self.view.figures['tau'].visible = False
            self.view.figures['inf_log'].visible = False
            self.view.figures['tau_log'].visible = False
            self.view.figures['distribution'].visible = True
            return

        self.view.figures['distribution'].visible = False
        mech_name = self.selected_mech_name
        self._toggle_kinetic_plots(mech_name)
    
    @log
    def _toggle_kinetic_plots(self, mech_name):

        if mech_name in ['Independent', 'Leak', 'CaDyn']:
            self.view.widgets.buttons['standardize'].visible = False
            self.view.figures['inf_log'].visible = False
            self.view.figures['inf'].visible = False
            self.view.figures['tau_log'].visible = False
            self.view.figures['tau'].visible = False
            return

        # 2. Get the mechanism
        mech = self.model.mechanisms[mech_name]
        logger.debug(f'Toggling kinetic plots for {mech.name}')

        # 3. Enable/ disable the standardize button
        if isinstance(mech, StandardIonChannel):
            ch_type = 'fit'
            factor = 2
            self.view.widgets.buttons['standardize'].visible = False
        else:
            ch_type = 'orig'
            factor = 1
            self.view.widgets.buttons['standardize'].visible = True

        # 4. Adjust the x-axis scale based on the independent variable
        if mech.independent_var_name == 'v':
            self.view.figures['inf_log'].visible = False
            self.view.figures['inf'].visible = True
            self.view.figures['tau_log'].visible = False
            self.view.figures['tau'].visible = True
        elif mech.independent_var_name == 'cai':
            self.view.figures['inf'].visible = False
            self.view.figures['inf_log'].visible = True
            self.view.figures['tau'].visible = False
            self.view.figures['tau_log'].visible = True

        # 5. Get the data for the mechanism
        data = mech.get_data()
        logger.debug(f'Updating kinetic plots for {mech.name} with data: {data}')
        x = data.pop('x').tolist()


        inf_data = {'xs': [x for _ in range(len(data))],
                    'ys': [state['inf'] for state in data.values()],
                    'label': [state for state in data.keys()],
                    'color': [Bokeh[8][2*i+factor] for i in range(len(data))]
        }
        tau_data = {'xs': [x for _ in range(len(data))],
                    'ys': [state['tau'] for state in data.values()],
                    'label': [state for state in data.keys()],
                    'color': [Bokeh[8][2*i+factor] for i in range(len(data))]
        }

        # 6. Update the figures
        self.view.sources[f'inf_{ch_type}'].data = inf_data
        self.view.sources[f'tau_{ch_type}'].data = tau_data

        self.view.figures[f'inf'].title.text = f'Steady state, {mech.name}'
        self.view.figures[f'tau'].title.text = f'Time constant, {mech.name}'

    
    # -----------------------------------------------------------------
    # PARAMETERS
    # -----------------------------------------------------------------

    @log
    def select_param_callback(self, attr, old, new):
        """
        Callback for the selectors['param'] widget.
        """
        param_name = new
        self._select_param(param_name)

    @log
    def _select_param(self, param_name):
        """
        Selects the parameter and updates the widgets.
        """
        logger.debug(f'Selected param: {param_name}')

        self._toggle_param_panel()

        with remove_callbacks(self.view.widgets.selectors['graph_param']):
            self.view.widgets.selectors['graph_param'].value = param_name
        self._update_graph_param(param_name)


    @log
    def _toggle_param_panel(self):
        """
        """
        
        mech_name = self.selected_mech_name

        # Such groups that span the domain where the mechanism is inserted
        if mech_name == 'Independent':
            available_groups = list(self.model.groups.keys())
        else:
            available_groups = [
                group_name for group_name, group in self.model.groups.items()
                if any(mech_name in self.model.domains_to_mechs[domain_name] 
                    for domain_name in group.domains)
            ]

        logger.debug(f'Avaliable groups: {available_groups}')

        if available_groups:
            self.view.DOM_elements['param_panel'].visible = True
            group_name = available_groups[0]
            # SET VIEW
            with remove_callbacks(self.view.widgets.selectors['group']):
                self.view.widgets.selectors['assigned_group'].options = available_groups
                self.view.widgets.selectors['assigned_group'].value = group_name
            self._select_group(group_name)
        else: 
            self.view.DOM_elements['param_panel'].visible = False
            

    @log
    def select_group_callback(self, attr, old, new):
        group_name = new
        self._select_group(group_name)


    @log
    def _select_group(self, group_name):
        """
        Selects the group sections and updates the widgets.
        """
        # GET VIEW
        logger.debug(f'Selected group: {group_name}')

        # SET VIEW
        param_name = self.selected_param_name
        self._toggle_group_panel(param_name, group_name)

        if group_name:
            self._select_group_segs_in_graph(group_name)
            
    @log
    def _toggle_group_panel(self, param_name, group_name):
        # GET MODEL
        groups_to_distrs = self.model.params[param_name]

        # SET VIEW
        if groups_to_distrs.get(group_name):
            # 1. Replace Add with Remove button
            self.view.widgets.buttons['add_distribution'].visible = False
            self.view.widgets.buttons['remove_distribution'].visible = True
            
            # 2. Show the group panel
            self.view.DOM_elements['group_panel'].visible = True

            # 3. Update the distribution type selector
            with remove_callbacks(self.view.widgets.selectors['distribution_type']):
                self.view.widgets.selectors['distribution_type'].value = groups_to_distrs[group_name].function_name
        else:
            # 1. Replace Remove with Add button
            self.view.widgets.buttons['remove_distribution'].visible = False
            self.view.widgets.buttons['add_distribution'].visible = True
            # 2. Show the group panel
            self.view.DOM_elements['group_panel'].visible = False

        self._toggle_distribution_widgets(param_name)
        self._update_distribution_plot()

    @log
    def _toggle_distribution_widgets(self, param_name):
        """
        Toggles the widgets for the distribution parameters.
        """
        group_name = self.selected_group_name

        group_has_distribution = bool(self.model.params[param_name].get(group_name))

        self.view.DOM_elements['distribution_widgets_panel'].visible = group_has_distribution

        if not group_has_distribution:
            self.view.DOM_elements['distribution_widgets_panel'].children = []
            return

        if self.model.params[param_name][group_name] == 'inherit':
            self.view.DOM_elements['distribution_widgets_panel'].visible = False
            self.view.DOM_elements['distribution_widgets_panel'].children = []
            return
            
        def make_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                logger.debug(f'Group name: {group_name}, param name: {param_name}, slider title: {slider_title}, new value: {new}')
                self.model.params[param_name][group_name].update_parameters(**{slider_title: new})
                self.model.distribute(param_name)
                mech_name = self.selected_mech_name
                if mech_name not in ['Independent', 'Leak']:
                    mech = self.model.mechanisms[mech_name]
                    mech.params[param_name.replace(f'_{mech.name}', '')] = round(new, 10) # TODO: actually should take the seg value, but which seg
                    self._toggle_kinetic_plots(mech.name)
                self._update_graph_param(param_name)
                self._update_distribution_plot()
            return slider_callback

        sliders = []
        for k, v in self.model.params[param_name][group_name].parameters.items():
            logger.info(f'Adding slider for {k} with value {v}')
            slider = AdjustableSpinner(title=k, value=v)
            slider_callback = make_slider_callback(slider.title)
            slider.on_change('value_throttled', slider_callback)
            slider.on_change('value_throttled', self.voltage_callback_on_change)
            sliders.append(slider.get_widget())
        self.view.DOM_elements['distribution_widgets_panel'].children = sliders
        

    def add_distribution_callback(self, event):
        """
        Callback for the buttons['add_distribution'] widget.
        """

        param_name = self.selected_param_name
        group_name = self.selected_group_name

        self.model.set_param(param_name, group_name)

        self._select_group(group_name)

    def remove_distribution_callback(self, event):

        param_name = self.selected_param_name
        group_name = self.selected_group_name

        self.model.remove_distribution(param_name, group_name)

        self.view.widgets.buttons['remove_distribution'].visible = False
        self.view.widgets.buttons['add_distribution'].visible = True
        self.view.DOM_elements['group_panel'].visible = False
        self._update_graph_param(param_name, update_colors=True)

    def update_distribution_type_callback(self, attr, old, new):
        """
        Callback for the selectors['distribution_type'] widget.
        """
        group_name = self.selected_group_name
        param_name = self.selected_param_name
        function_name = new
        self.model.set_param(param_name, 
                             group_name,
                             distr_type=function_name)
        self._toggle_distribution_widgets(param_name)
        self._update_distribution_plot()

    
    def _update_distribution_plot(self):
        """
        Updates the distribution plot with the selected parameter.
        """
        param_name = self.selected_param_name
        selected_segs = self.selected_segs

        data = {'x': [seg.path_distance() for seg in selected_segs],
                'y': [seg.get_param_value(param_name) for seg in selected_segs],
                'color': [self.view.get_domain_color(seg.domain) for seg in selected_segs],
                'label': [str(seg.idx) for seg in selected_segs]}

        self.view.sources['distribution'].data = data
        

    @log
    def _update_diam_distribution_plot(self):

        param_name = 'diam'
        selected_segs = self.selected_segs

        data = {'x': [seg.path_distance() for seg in selected_segs],
                'y': [seg.diam for seg in selected_segs],
                'color': [self.view.get_domain_color(seg.domain) for seg in selected_segs],
                'label': [str(seg.idx) for seg in selected_segs]}

        self.view.sources['diam_distribution'].data = data


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

        self.update_status_message(f'{syn_type} population added.', status='success')


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
                population.update_kinetic_params(**{slider_title: new})
            return slider_callback

        def make_input_param_slider_callback(slider_title):
            def slider_callback(attr, old, new):
                population.update_input_params(**{slider_title: new})
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
            population.update_input_params(**{'start': new[0], 'end': new[1]})

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
    # MORPHOLOGY TAB
    # =================================================================  


    def delete_subtree_callback(self, event):

        if len(self.selected_secs) != 1:
            return

        sec = self.selected_secs.pop()

        self.model.remove_subtree(sec)
        
        self.selected_secs = set()
        self.selected_segs = []
        
        self._create_cell_renderer()
        self._init_cell_widgets()
        self._create_graph_renderer()
        self.view.widgets.selectors['section'].value = None

        self.update_voltage()
        

    @log
    def reduce_subtree_callback(self, event):

        if self.model.mechs_to_domains.get('Leak') is None:
            self.update_status_message(message='Insert the Leak mechanism first.', status='error')
            return
        
        sec = next(iter(self.selected_secs))
        self.model.reduce_subtree(sec)

        self._create_cell_renderer()
        self._init_cell_widgets()

        self.view.widgets.multichoice['domains'].options = list(self.model.domains.keys())
        
        self._create_graph_renderer()
        self._update_group_selector_widget()
        self._update_graph_param_widget()

        self._update_multichoice_mechanisms_widget()
        self._update_mechs_to_insert_widget()
        self._update_multichoice_domain_widget()

        self.update_status_message(message='Subtree reduced.', status='success')
        

    # =================================================================
    # MISC
    # =================================================================

    # self.view.widgets.multichoice['group_domains'].options = list(self.model.domains.keys())
    
    def select_graph_param_based_on_tab(self):

        TABS_TO_PARAMS = {
            0: ('morphology', ['domain']*4),
            1: ('membrane', ['domain', 'domain', self.view.widgets.selectors['param'].value]),
            2: ('stimuli', ['recordings', 'iclamps', 'AMPA_NMDA']),
        }

        active_tab_id = self.view.widgets.buttons['switch_right_menu'].active
        tab_name, params = TABS_TO_PARAMS[active_tab_id]
        tab_idx = self.view.widgets.tabs[tab_name].active

        logger.debug(f'Switching to "{tab_name}" tab with index {tab_idx}')

        param_name = params[tab_idx]
        options = {**self.view.params, **self.model.mechs_to_params} if tab_name == 'membrane' else {**self.view.params}

        self.view.widgets.selectors['graph_param'].options = options
        self.view.widgets.selectors['graph_param'].value = param_name

    def switch_tab_callback(self, attr, old, new):

        self.select_graph_param_based_on_tab()
        if self.view.widgets.tabs['morphology'].visible:
            if self.view.widgets.tabs['morphology'].active == 0:
                self.view.widgets.selectors['section'].value = '0'
            elif self.view.widgets.tabs['morphology'].active == 1:
                self.view.widgets.selectors['section'].value = '0'
                self.view.widgets.selectors['domain'].value = 'soma'
            else:
                self.view.widgets.selectors['section'].value = None

  
    def switch_right_menu_tab_callback(self, attr, old, new):
        if new == 0:
            logger.debug('Switching to Morphology Tabs')
            self.view.widgets.tabs['stimuli'].visible = False
            self.view.widgets.tabs['membrane'].visible = False
            self.view.widgets.tabs['morphology'].visible = True
            if self.view.widgets.tabs['morphology'].active == 0:
                self.view.widgets.selectors['section'].value = '0'
            else:
                self.view.widgets.selectors['section'].value = None
        elif new == 1:
            logger.debug('Switching to Membrane Tabs')
            self.view.widgets.tabs['morphology'].visible = False
            self.view.widgets.tabs['stimuli'].visible = False
            self.view.widgets.tabs['membrane'].visible = True
            self.view.widgets.selectors['section'].value = None
        elif new == 2:
            logger.debug('Switching to Stimuli Tabs')
            self.view.widgets.tabs['morphology'].visible = False
            self.view.widgets.tabs['membrane'].visible = False
            self.view.widgets.tabs['stimuli'].visible = True
            self.view.widgets.selectors['section'].value = '0'
        self.select_graph_param_based_on_tab()

    def save_preferences_callback(self, event):

        import json
        
        preferences = {
            "appearance": {
                "theme": self.view.theme.name,
                "plots": {
                    "graph_plot":{
                        "layout": self.view.widgets.selectors['graph_layout'].value,
                    },
                    "voltage_plot": {
                        "ymin": self.view.widgets.sliders['voltage_plot_y_range'].value[0],
                        "ymax": self.view.widgets.sliders['voltage_plot_y_range'].value[1],
                    }
                }
            },
            "data": {
                "path_to_data": self.path_to_data,
                "recompile_MOD_files": self.view.widgets.switches['recompile'].active,
            },
            "simulation": {
                "simulator": self.view.widgets.selectors['simulator'].value,
                "run_on_interaction": self.view.widgets.switches['run_on_interaction'].active,
            }
        }

        with open('app/user_config.json', 'w') as f:
            json.dump(preferences, f, indent=4)

        self.update_status_message('Preferences saved.', status='success')
        

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
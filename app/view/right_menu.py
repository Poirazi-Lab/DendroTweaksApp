
from bokeh.models import Button, Select, Slider, RadioButtonGroup
from bokeh.models import RangeSlider, Switch, Spinner
from bokeh.models import ColumnDataSource, HoverTool, Patches
from bokeh.layouts import column, row
from bokeh.models import Tabs, TabPanel
from bokeh.events import ButtonClick
from bokeh.models import MultiChoice
from bokeh.models import TextInput, NumericInput
from bokeh.models import Dropdown

from bokeh.models import CustomJS

from bokeh.models import Div
from bokeh_utils import AdjustableSpinner
AVAILABLE_DOMAINS = [
    'soma', 'perisomatic', 
    'axon', 
    'dend', 'basal', 
    'apic', 'trunk', 'tuft', 'oblique', 
    'custom_0', 'custom_1', 'custom_2', 'custom_3'
]

class RightMenuMixin():

    def __init__(self):
        super().__init__()

    # =================================================================
    # MORPHOLOGY 
    # =================================================================

    # -----------------------------------------------------------------
    # Sections tab
    # -----------------------------------------------------------------

    def _create_nseg_spinner(self):

        self.widgets.spinners['n_seg'] = Spinner(
            title='N seg', 
            value=1, 
            step=1, 
            width=100,
            name='n_seg'
        )
        self.widgets.spinners['n_seg'].on_change('value_throttled', self.p.nseg_callback)


    def _create_sections_tab_panel(self):

        self._create_nseg_spinner()
        section_figures = self.create_section_panel()
        self.DOM_elements['psection'] = Div(
            text="""Select a section to show.""",
            styles={'width': '500px', 'height':'200px', 
                    'margin-top': '60px',
                    'overflow': 'auto', 'font-size': '12px'})
        
        sections_layout = column(
            [
                self.widgets.spinners['n_seg'],
                section_figures,
                self.DOM_elements['psection']
            ],
            name='sections_layout',
            sizing_mode='stretch_width',
        )

        self.widgets.tab_panels['sections'] = TabPanel(
            title='Sections',
            child=sections_layout,
        )

    # -----------------------------------------------------------------
    # Domains tab
    # -----------------------------------------------------------------

    def _create_domain_selector(self):

        self.widgets.selectors['domain'] = Select(options=[],
                                            value=None,
                                            title='Select domain',
                                            width=100)
        self.widgets.selectors['domain'].on_change('value', self.p.select_domain_segments_callback)


    def _create_set_domain_selector(self):

        self.widgets.selectors['set_domain'] = Select(title='Set domain',
                                        options=AVAILABLE_DOMAINS,
                                        value='soma',
                                        width=150)
        self.widgets.selectors['set_domain'].on_change('value', self.p.define_domain_callback)


    def _create_domains_tab_panel(self):

        self._create_domain_selector()
        self._create_set_domain_selector()

        domains_panel = column([
            self.widgets.selectors['domain'],
            self.widgets.selectors['set_domain'],
        ])

        self.widgets.tab_panels['domains'] = TabPanel(
            title='Domains',
            child=domains_panel,
        )

    # -----------------------------------------------------------------
    # Morphology modification tab
    # -----------------------------------------------------------------

    def _create_reduce_subtree_button(self):
        self.widgets.buttons['reduce_subtree'] = Button(label='Reduce subtree', button_type='warning')
        self.add_message(self.widgets.buttons['reduce_subtree'], 'Reducing the subtree. Please wait...', callback_type='on_click')
        self.widgets.buttons['reduce_subtree'].on_event(ButtonClick, self.p.reduce_subtree_callback)
        self.widgets.buttons['reduce_subtree'].on_event(ButtonClick, self.p.voltage_callback_on_event)

    def _create_delete_subtree_button(self):
        self.widgets.buttons['delete_subtree'] = Button(label='Delete subtree', button_type='danger')
        self.widgets.buttons['delete_subtree'].on_event(ButtonClick, self.p.delete_subtree_callback)


    def _create_reduction_tab_panel(self):

        self._create_reduce_subtree_button()
        self._create_delete_subtree_button()

        tree_modification_panel = column(
            [
                self.widgets.buttons['reduce_subtree'],
                self.widgets.buttons['delete_subtree'],
            ]
        )

        self.widgets.tab_panels['reduction'] = TabPanel(
            title='Reduction',
            child=tree_modification_panel,
        )

    # -----------------------------------------------------------------
    # Morphometric analysis tab
    # -----------------------------------------------------------------

    def _create_morphometric_analysis_tab_panel(self):
        
        self.DOM_elements['stats'] = Div(text='Stats:')

        self.widgets.buttons['stats'] = Button(label='Stats', button_type='default')
        self.widgets.buttons['stats'].on_event(ButtonClick, self.p.stats_callback)

        stats_panel = column(
            [
                self.widgets.buttons['stats'], 
                self.DOM_elements['stats'],
            ],
            name='stats_panel'
        )

        self.widgets.tab_panels['morphometric_analysis'] = TabPanel(
            title='Morphometric analysis',
            child=stats_panel,
        )
        

    def _create_morphology_tabs(self):

        self._create_sections_tab_panel()
        self._create_domains_tab_panel()
        self._create_reduction_tab_panel()
        self._create_morphometric_analysis_tab_panel()
        
        self.widgets.tabs['morphology'] = Tabs(
            tabs = [
                self.widgets.tab_panels['sections'],
                self.widgets.tab_panels['domains'],
                self.widgets.tab_panels['reduction'],
                self.widgets.tab_panels['morphometric_analysis']
            ],
            active = 0,
            sizing_mode='stretch_width',
        )
        self.widgets.tabs['morphology'].on_change('active', self.p.switch_tab_callback)

    # =================================================================
    # MEMBRANE
    # =================================================================

    # -----------------------------------------------------------------
    # Membrane mechanisms tab
    # -----------------------------------------------------------------

    def _create_mechanisms_multichoice(self):

        self.widgets.multichoice['mechanisms'] = MultiChoice(title='Added mechanisms',
                                                            options=[],
                                                            value=[],
                                                            visible=True,
                                                            width=300)
        self.widgets.multichoice['mechanisms'].on_change('value', self.p.add_mechanism_callback)


    def _create_recompile_switch(self):

        self.widgets.switches['recompile'] = Switch(active=self.p.config['data']['recompile_MOD_files'], 
                                                    name='recompile')


    def _create_add_default_mechanisms_button(self):
        self.widgets.buttons['add_default_mechanisms'] = Button(label='Add default mechanisms', button_type='primary', width=100)
        self.widgets.buttons['add_default_mechanisms'].on_event(ButtonClick, self.p.add_default_mechanisms_callback)


    def _create_mechanisms_to_insert_selector(self):

        self.widgets.selectors['mechanism_to_insert'] = Select(
            title='Mechanism',
            options=['Leak'],
            value = 'Leak',
        )
        self.widgets.selectors['mechanism_to_insert'].on_change('value', self.p.select_mechanism_to_insert_callback)


    def _create_domains_multichoice(self):

        self.widgets.multichoice['domains'] = MultiChoice(title='Domains where to insert:',
                                                                  options=[],
                                                                  value=[],
                                                                  visible=True,
                                                                  width=300)
        self.widgets.multichoice['domains'].on_change('value', self.p.insert_mechanism_callback)


    def _create_membrane_mechanisms_tab_panel(self):
        
        self._create_mechanisms_multichoice()
        self._create_recompile_switch()
        self._create_add_default_mechanisms_button()
        self._create_mechanisms_to_insert_selector()
        self._create_domains_multichoice()

        mechanisms_panel = column([
            row(self.widgets.switches['recompile'], Div(text='Recompile mod files')),
            self.widgets.multichoice['mechanisms'],
            self.widgets.buttons['add_default_mechanisms'],
            self.widgets.selectors['mechanism_to_insert'],
            self.widgets.multichoice['domains'],
        ])

        self.widgets.tab_panels['membrane_mechanisms'] = TabPanel(
            title='Membrane mechanisms',
            child=mechanisms_panel,
        )

    # -----------------------------------------------------------------
    # Segment groups tab
    # -----------------------------------------------------------------

    def _create_group_name_text_input(self):
        self.widgets.text['group_name'] = TextInput(value='', 
                                                    title='Group name', 
                                                    placeholder='New group name',
                                                    width=150)
        def check_name_exists_callback(attr, old, new):
            if new in self.widgets.selectors['group'].options:
                self.widgets.buttons['add_group'].disabled = True
            else:
                self.widgets.buttons['add_group'].disabled = False
        self.widgets.text['group_name'].on_change('value_input', check_name_exists_callback)


    def _create_add_group_button(self):
        self.widgets.buttons['add_group'] = Button(label='Add group', 
                                                   button_type='primary', 
                                                   disabled=False,
                                                   width=100,
                                                   styles={"padding-top":"20px"}
                                                   )
                                                
        self.widgets.buttons['add_group'].on_event(ButtonClick, self.p.add_group_callback)


    def _create_group_domains_multichoice(self):
        self.widgets.multichoice['group_domains'] = MultiChoice(
            title='Domain',
            options=[],
            width=300
        )
        self.widgets.multichoice['group_domains'].on_change('value', self.p.select_group_segments_callback)


    def _create_select_by_selector(self):
        self.widgets.selectors['select_by'] = Select(options=['distance', 'domain_distance', 'diam', 'section_diam'],
                                                value='distance',
                                                title='Select by',
                                                width=100)

        self.widgets.selectors['select_by'].on_change('value', self.p.select_group_segments_callback)                                            

        self.widgets.spinners['condition_min'] = NumericInput(value=None, title='Min', width=75, mode='float')
        self.widgets.spinners['condition_max'] = NumericInput(value=None, title='Max', width=75, mode='float')

        self.widgets.spinners['condition_min'].on_change('value', self.p.select_group_segments_callback)
        self.widgets.spinners['condition_max'].on_change('value', self.p.select_group_segments_callback)


    def _create_group_selector(self):
        self.widgets.selectors['group'] = Select(title='Groups',
                                            options=[], 
                                            value=None,
                                            width=150,
                                            )

        self.widgets.selectors['group'].on_change('value', self.p.select_group_segs_callback)


    def _create_remove_group_button(self):
        self.widgets.buttons['remove_group'] = Button(label='Remove group',
                                                        button_type='danger',
                                                        disabled=False,
                                                        width=100,
                                                        styles={"padding-top":"20px"}
                                                        )

        self.widgets.buttons['remove_group'].on_event(ButtonClick, self.p.remove_group_callback)


    def _create_segment_groups_tab_panel(self):

        self._create_group_name_text_input()
        self._create_add_group_button()
        self._create_group_domains_multichoice()
        self._create_select_by_selector()
        self._create_group_selector()
        self._create_remove_group_button()
        
        groups_panel = column(
            [
                row(
                    [
                        self.widgets.text['group_name'],
                        self.widgets.buttons['add_group']
                    ]
                ),
                self.widgets.multichoice['group_domains'],
                row(
                    [
                        self.widgets.selectors['select_by'],
                        self.widgets.spinners['condition_min'],
                        self.widgets.spinners['condition_max'],
                    ]
                ),
                row(
                    [
                        self.widgets.selectors['group'],
                        self.widgets.buttons['remove_group'],
                    ]
                )
            ], 
        )

        self.widgets.tab_panels['segment_groups'] = TabPanel(
            title='Segment groups',
            child=groups_panel,
        )

    # -----------------------------------------------------------------
    # Parameters tab (Distribution and kinetics)
    # -----------------------------------------------------------------

    def _create_mechanism_selector(self):

        self.widgets.selectors['mechanism'] = Select(title='Mechanism',
                                                    options=['Independent'],
                                                    value = 'Independent',
                                                    )

        self.widgets.selectors['mechanism'].on_change('value', self.p.select_mechanism_callback)


    def _create_standardize_button(self):

        self.widgets.buttons['standardize'] = Button(label='Standardize',
                                                    button_type='warning',
                                                    visible=False,
                                                    width=100,
                                                    styles={"padding-top":"20px"}
                                                    )

        self.add_message(self.widgets.buttons['standardize'], 'Standardizing. Please wait...', callback_type='on_click')
        
        self.widgets.buttons['standardize'].on_event(ButtonClick, self.p.standardize_callback)
        self.widgets.buttons['standardize'].on_event(ButtonClick, self.p.voltage_callback_on_event)
        
    def _create_show_kinetics_switch(self):

        self.widgets.switches['show_kinetics'] = Switch(
            active=False, )
        self.widgets.switches['show_kinetics'].on_change('active', self.p.toggle_kinetic_plots_callback)



    def _create_param_selector(self):
        self.widgets.selectors['param'] = Select(title='Parameter',
                                                options=[],
                                                value=None,
                                                width=150)

        self.widgets.selectors['param'].description = 'Select a parameter defined as a RANGE variable in the MOD file.'

        self.widgets.selectors['param'].on_change('value', self.p.select_param_callback)


    def _create_assigned_group_selector(self):
        self.widgets.selectors['assigned_group'] = Select(title='Groups',
                                            options=[], 
                                            value=None,
                                            width=150,
                                            )

        self.widgets.selectors['assigned_group'].on_change('value', self.p.select_group_callback)


    def _create_add_distribution_button(self):

        self.widgets.buttons['add_distribution'] = Button(label='Add distribution',
                                                        button_type='primary',
                                                        disabled=False,
                                                        visible=True,
                                                        width=150,
                                                        styles={"padding-top":"20px"}
                                                        )

        self.widgets.buttons['add_distribution'].on_event(ButtonClick, self.p.add_distribution_callback)


    def _create_remove_distribution_button(self):

        self.widgets.buttons['remove_distribution'] = Button(label='Remove distribution',
                                                        button_type='danger',   
                                                        disabled=False,
                                                        visible=False,
                                                        width=150,
                                                        styles={"padding-top":"20px"}
                                                        )

        self.widgets.buttons['remove_distribution'].on_event(ButtonClick, self.p.remove_distribution_callback)


    def _create_distribution_type_selector(self):

        self.widgets.selectors['distribution_type'] = Select(
            title='Distribution type',
            value='constant',
            options=['constant', 'linear', 'exponential', 'sigmoid', 'sinusoidal', 'gaussian', 'step', 'inherit'],
            width=150,
            visible=True
        )
        self.widgets.selectors['distribution_type'].on_change('value', self.p.update_distribution_type_callback)
 

    def _create_parameters_tab_panel(self):
        
        self._create_mechanism_selector()
        self._create_standardize_button()
        self._create_show_kinetics_switch()
        self._create_param_selector()

        self._create_assigned_group_selector()
        self._create_add_distribution_button()
        self._create_remove_distribution_button()

        self._create_distribution_type_selector()

        kinetics_panel = self._create_kinetics_panel()
        self._create_distribution_figure()

        # Distr → Group → Param → Mech

        self.DOM_elements['distribution_widgets_panel'] = column(width=300)
        
        self.DOM_elements['group_panel'] = column(
            [
                self.widgets.selectors['distribution_type'],
                self.DOM_elements['distribution_widgets_panel'],
                self.figures['distribution'],
            ], 
            visible=False
        )

        self.DOM_elements['param_panel'] = column(
            [
                row(
                    [
                        self.widgets.selectors['assigned_group'],
                        self.widgets.buttons['add_distribution'],
                        self.widgets.buttons['remove_distribution'],
                    ]
                ),
                self.DOM_elements['group_panel'],
            ], 
            visible=False
        )

        mech_panel = column(
            [
                row(
                    [
                        self.widgets.selectors['mechanism'], 
                        self.widgets.buttons['standardize'],
                    ]
                ),
                row(Div(text='Show distribution'), self.widgets.switches['show_kinetics'], Div(text='Show kinetics'),
                        # styles={"padding-top":"20px"},
                        ),
                kinetics_panel,
                self.widgets.selectors['param'],
            ]
        )
        
        parameters_panel = column(
            [
                mech_panel,
                self.DOM_elements['param_panel'],
                
            ]
        )

        self.widgets.tab_panels['parameters'] = TabPanel(
            title='Parameters', 
            child=parameters_panel
        )

    def _create_membrane_tabs(self):

        self._create_membrane_mechanisms_tab_panel()
        self._create_segment_groups_tab_panel()
        self._create_parameters_tab_panel()
        
        self.widgets.tabs['membrane'] = Tabs(
            tabs = [
                self.widgets.tab_panels['membrane_mechanisms'],
                self.widgets.tab_panels['segment_groups'],
                self.widgets.tab_panels['parameters']
            ],
            active = 0,
            visible=False,
            sizing_mode='stretch_width',
        )
        self.widgets.tabs['membrane'].on_change('active', self.p.switch_tab_callback)

    # =================================================================
    # STIMULI
    # =================================================================

    # -----------------------------------------------------------------
    # Recordings tab
    # -----------------------------------------------------------------

    def _create_remove_all_recordings_button(self):
        self.widgets.buttons['remove_all'] = Button(label='Remove all recordings', button_type='danger')
        self.widgets.buttons['remove_all'].on_event(ButtonClick, self.p.remove_all_recordings_callback)
        self.widgets.buttons['remove_all'].on_event(ButtonClick, self.p.voltage_callback_on_event)

    def _create_record_from_all_swwitch(self):
        self.widgets.switches['record_from_all'] = Switch(
            active=False, 
            disabled=True
        )
        self.widgets.switches['record_from_all'].on_change('active', self.p.record_from_all_callback)
        self.widgets.switches['record_from_all'].on_change('active', self.p.voltage_callback_on_change)

    def _create_recording_switch(self):
        self.widgets.switches['record'] = Switch(
            active=False,
            disabled=True
        )
        self.widgets.switches['record'].on_change('active', self.p.record_callback)
        self.widgets.switches['record'].on_change('active', self.p.voltage_callback_on_change)
        


    def _create_recordings_tab_panel(self):

        self._create_record_from_all_swwitch()
        self._create_recording_switch()
        self._create_remove_all_recordings_button()

        recordings_panel = column(
            [
                row([self.widgets.switches['record_from_all'], Div(text='Record from all')]),
                row([self.widgets.switches['record'], Div(text='Record from segment')]),
                self.widgets.buttons['remove_all']
            ],
            name='recordings_panel'
        )

        self.widgets.tab_panels['recordings'] = TabPanel(
            title='Recordings',
            child=recordings_panel,
        )

    # -----------------------------------------------------------------
    # Iclamps tab
    # -----------------------------------------------------------------

    def _create_iclamp_switch(self):
        self.widgets.switches['iclamp'] = Switch(active=False)
        self.widgets.switches['iclamp'].on_change('active', self.p.toggle_iclamp_callback)
        self.widgets.switches['iclamp'].on_change('active', self.p.voltage_callback_on_change)

    def _create_iclamp_duration_slider(self):
        self.widgets.sliders['iclamp_duration'] = RangeSlider(
            start=0,
            end=300,
            value=(100,200),
            step=10,
            title="Duration, ms",
            visible=False
        )
        self.widgets.sliders['iclamp_duration'].on_change('value_throttled', self.p.iclamp_duration_callback)
        self.widgets.sliders['iclamp_duration'].on_change('value_throttled', self.p.voltage_callback_on_change)

    def _create_iclamp_delay_slider(self):
        self.widgets.sliders['iclamp_amp'] = AdjustableSpinner(
            title="Amp (pA)", 
            value=0, 
            step=1, 
            visible=False)
        self.widgets.sliders['iclamp_amp'].on_change('value_throttled', self.p.iclamp_amp_callback)
        self.widgets.sliders['iclamp_amp'].on_change('value_throttled', self.p.voltage_callback_on_change)

    def _create_remove_all_iclamps_button(self):

        self.widgets.buttons['remove_all_iclamps'] = Button(
            label='Remove all IClamps', 
            button_type='danger'
        )
        self.widgets.buttons['remove_all_iclamps'].on_event(ButtonClick, self.p.remove_all_iclamps_callback)
        self.widgets.buttons['remove_all_iclamps'].on_event(ButtonClick, self.p.voltage_callback_on_event)

    def _create_iclamp_tab_panel(self):
        
        self._create_iclamp_switch()
        self._create_iclamp_duration_slider()
        self._create_iclamp_delay_slider()
        self._create_remove_all_iclamps_button()
        
        iclamp_panel = column(
            [
                row([self.widgets.switches['iclamp'], Div(text='Add IClamp to segment')]),
                self.widgets.sliders['iclamp_amp'].get_widget(),
                self.widgets.sliders['iclamp_duration'],
                self.widgets.buttons['remove_all_iclamps'],
            ],
            name='iclamp_panel'
        )

        self.widgets.tab_panels['iclamp'] = TabPanel(
            title='IClamps',
            child=iclamp_panel,
        )

    # -----------------------------------------------------------------
    # Synapses tab
    # -----------------------------------------------------------------

    def _create_syn_type_selector(self):
        self.widgets.selectors['syn_type'] = Select(
            title='Synaptic type', 
            value='AMPA_NMDA', 
            options=['AMPA', 'NMDA', 'AMPA_NMDA', 'GABAa'], 
            width=150
        )
        self.widgets.selectors['syn_type'].on_change('value', self.p.select_synapse_type_callback)


    def _create_n_syn_spinner(self):
        self.widgets.spinners['N_syn'] = NumericInput(value=1, title='N syn', width=100)


    def _create_add_population_button(self):
        self.widgets.buttons['add_population'] = Button(label='Add population', 
                                                        button_type='primary', 
                                                        disabled=False)
        self.add_message(self.widgets.buttons['add_population'], 'Adding population. Please wait...', callback_type='on_click')
        self.widgets.buttons['add_population'].on_event(ButtonClick, 
                                                        self.p.add_population_callback)
        self.widgets.buttons['add_population'].on_event(ButtonClick, 
                                                        self.p.voltage_callback_on_event)


    def _create_population_selector(self):

        self.widgets.selectors['population'] = Select(options=[], title='Population', width=150)
        self.widgets.selectors['population'].on_change('value', self.p.select_population_callback)


    def _create_remove_population_button(self):

        self.widgets.buttons['remove_population'] = Button(label='Remove population', button_type='danger', disabled=False, styles={"padding-top":"20px"})
        self.widgets.buttons['remove_population'].on_event(ButtonClick, self.p.remove_population_callback)
        self.widgets.buttons['remove_population'].on_event(ButtonClick, self.p.voltage_callback_on_event)


    def _create_synapses_tab_panel(self):
        
        self._create_syn_type_selector()
        self._create_n_syn_spinner()
        self._create_add_population_button()
        self._create_population_selector()
        self._create_remove_population_button()

        self.DOM_elements['population_panel'] = column(width=300)

        synapses_panel = column([
            # self.widgets.buttons['remove_all_populations'],
            row([self.widgets.selectors['syn_type'], self.widgets.spinners['N_syn']]),
            self.widgets.buttons['add_population'],
            Div(text='<hr style="width:30em">'),
            row([self.widgets.selectors['population'], self.widgets.buttons['remove_population']]),
            self.DOM_elements['population_panel'],
        ])

        self.widgets.tab_panels['synapses'] = TabPanel(
            title='Synapses',
            child=synapses_panel,
        )

    # ------------------------------------------------------------------------------------
    # Validation tab panel
    # ------------------------------------------------------------------------------------

    def _create_protocol_selector(self):

        self.widgets.selectors['protocol'] = Select(
            title='Validation protocol',
            value='Select validation protocol',
            options=[
                    'Somatic spikes',
                    'Input resistance and time constant',
                    'Attenuation',
                    'Sag ratio',
                    'f-I curve',
                    'Dendritic nonlinearity',
                ]
            )
        self.widgets.selectors['protocol'].on_change('value', self.p.select_protocol_callback)
    
    def _create_stats_ephys_button(self):
        
        self.widgets.buttons['stats_ephys'] = Dropdown(
            label='Validate', 
            button_type='default', 
            menu=[
                ('Detect spikes', 'spikes'), 
                ('Input resistance and time constant', 'R_in'), 
                ('Atttenuation', 'attenuation'), 
                ('Sag ratio', 'sag_ratio'), 
                ('f-I curve', 'fI_curve'), 
                ('I-V curve', 'iv_curve'),
                ('Dendritic nonlinearity', 'nonlinearity'),
            ]
        )
        self.widgets.buttons['stats_ephys'].on_event("menu_item_click", self.p.stats_ephys_callback)

    def _create_run_protocol_button(self):
        self.widgets.buttons['run_protocol'] = Button(
            label='Run protocol', 
            button_type='primary'
        )
        self.widgets.buttons['run_protocol'].on_event(ButtonClick, self.p.run_protocol_callback)

    # Clear validation
    def _create_clear_validation_button(self):

        self.widgets.buttons['clear_validation'] = Button(
            label='Clear', 
            button_type='danger'
        )
        def clear_validation_callback():
            self.sources['stats_ephys'].data = {'x': [], 'y': []}
            self.sources['detected_spikes'].data = {'x': [], 'y': []}
            self.sources['frozen_v'].data = {'xs': [], 'ys': []}
            self.widgets.switches['frozen_v'].active = False
            self.figures['stats_ephys'].visible = False
            self.DOM_elements['stats_ephys'].text = "Data cleared. Select a protocol to validate."
        self.widgets.buttons['clear_validation'].on_event(ButtonClick, clear_validation_callback)


    # Tab panel

    def _create_validation_tab_panel(self):

        self.DOM_elements['stats_ephys'] = Div(
            text="",
            width=400,
            styles={
                'color': self.theme.status_colors['info'],
                'margin': '10px',
                'background-color': 'rgba(255, 255, 255, 0.2)',
                'padding': '10px',
                'border-radius': '5px',
            }
        )

        self._create_protocol_selector()
        self._create_stats_ephys_figure()
        self._create_run_protocol_button()
        self._create_clear_validation_button()

        validation_layout = column(
            [
                self.widgets.selectors['protocol'],
                self.DOM_elements['stats_ephys'],
                self.figures['stats_ephys'],
                self.widgets.buttons['run_protocol'], 
                self.widgets.buttons['clear_validation'],
            ],
            sizing_mode='scale_both',
        )
        
        self.widgets.tab_panels['validation'] = TabPanel(
            title='Ephys analysis',
            child=validation_layout,
        )


    def _create_stimuli_tabs(self):

        self._create_recordings_tab_panel()
        self._create_iclamp_tab_panel()
        self._create_synapses_tab_panel()
        self._create_validation_tab_panel()

        self.widgets.tabs['stimuli'] = Tabs(
            tabs = [
                self.widgets.tab_panels['recordings'],
                self.widgets.tab_panels['iclamp'],
                self.widgets.tab_panels['synapses'],
                self.widgets.tab_panels['validation'],
            ],
            active = 0,
            visible=False,
        )
        self.widgets.tabs['stimuli'].on_change('active', self.p.switch_tab_callback)

    def _create_radio_buttons(self):

        self.widgets.buttons['switch_right_menu'] = RadioButtonGroup(
            labels=['Morphology', 'Membrane mechanisms', 'Recordings and Stimuli'], 
            active=0, 
            align='center', 
            disabled=False,
            sizing_mode='stretch_width',
            styles={"padding": "10px 0 20px 0"}
        )
        self.widgets.buttons['switch_right_menu'].on_change('active', self.p.switch_right_menu_tab_callback)


    def create_right_menu(self):

        self._create_morphology_tabs()
        self._create_membrane_tabs()
        self._create_stimuli_tabs()

        self._create_radio_buttons()

        return column(
            [
                self.widgets.buttons['switch_right_menu'],
                self.widgets.tabs['morphology'], 
                self.widgets.tabs['membrane'], 
                self.widgets.tabs['stimuli'],
            ],
            align='center',
            name='right_menu_section',
            sizing_mode='stretch_width',
            visible=False,
        )
# ====================================================================================
# LEFT MENU
# ====================================================================================

# ------------------------------------------------------------------------------------
# I/O tab panel
# ------------------------------------------------------------------------------------

# Loading

from bokeh.models import Select
from bokeh.models import Button, Dropdown, TextInput, FileInput
from bokeh.models import Slider, Switch
from bokeh.models import ColumnDataSource
from bokeh.models import Tabs, TabPanel
from bokeh.models import Div

from bokeh.layouts import column, row
from bokeh.plotting import figure
from bokeh.events import ButtonClick
from bokeh.models import CustomJS



class LeftMenuMixin():


    def __init__(self):
        super().__init__()


    def _create_model_selector(self):
        
        available_models = self.p.list_models()
        self.widgets.selectors['model'] = Select(
            value='Select a model to load',
            options=['Select a model to load'] + available_models,
            title='Model',
            width=242, 
            align='center'
        )
        self.widgets.selectors['model'].on_change('value', self.p.select_model_callback)
        self.widgets.selectors['model'].description = 'Select a neuronal model to load. To select another model, reload the page.'


    def _create_morphology_selector(self):

        self.widgets.selectors['morphology'] = Select(
            value='Select morphology',
            options=['Select a morphology'],
            title='Morphology',
            width=242, 
            align='center'
        )
        self.add_message(self.widgets.selectors['morphology'], 'Loading morphology. Please wait...', callback_type='on_change')
        self.widgets.selectors['morphology'].on_change('value', self.p.load_morphology_callback)


    def _create_biophys_selector(self):

        self.widgets.selectors['biophys'] = Select(
            value='Select biophys config.',
            options=['Select biophys config.'],
            title='Biophys config.',
            width=242, 
            align='center',
        )
        self.add_message(self.widgets.selectors['biophys'], 'Loading biophys config. Please wait...', callback_type='on_change')
        self.widgets.selectors['biophys'].on_change('value', self.p.load_biophys_callback)


    def _create_stimuli_selector(self):

        self.widgets.selectors['stimuli'] = Select(
            value='Select stimuli',
            options=['Select stimuli'],
            title='Stimuli',
            width=242,
            align='center',
        )
        self.add_message(self.widgets.selectors['stimuli'], 'Loading stimuli. Please wait...', callback_type='on_change')
        self.widgets.selectors['stimuli'].on_change('value', self.p.load_stimuli_callback)


    # Exporting
    def _create_file_name_text_input(self):

        self.widgets.text['file_name'] = TextInput(
            value='', 
            title='File name', 
            placeholder='Enter file name ...', 
            width=242, 
            align='center'
        )


    def _create_export_model_button(self):

        self.widgets.buttons['export_model'] = Dropdown(
            label='Export model',
            width=242, align='center',
            button_type='default',
            menu=[
                ('Export morphology', 'morphology'), 
                ('Export biophys config', 'biophys'),
                ('Export stimuli', 'stimuli')
            ]
        )
        self.widgets.buttons['export_model'].on_event("menu_item_click", self.p.export_model_callback)


    def _create_download_model_button(self):

        self.widgets.buttons['download_model'] = Button(
            label='Download model as .zip', 
            button_type='primary', 
            width=242,
            align='center',
        )
        self.widgets.buttons['download_model'].on_event(ButtonClick, self.p.download_model_callback)

    # File import
    # self.widgets.file_input['all'] = FileInput(accept='.swc, .asc, .mod', name='file', visible=True, width=242, disabled=False)
    # self.widgets.file_input['all'].on_change('filename', self.p.import_file_callback)
    # self.widgets.file_input['all'].on_change('value', self.p.import_file_callback)

    def _create_io_tab_panel(self):

        self._create_model_selector()
        self._create_morphology_selector()
        self._create_biophys_selector()
        self._create_stimuli_selector()

        import_layout = column(
            [
                Div(text='File Import', align='center', styles={'padding-top': '20px'}),
                self.widgets.selectors['model'],
                self.widgets.selectors['morphology'],
                self.widgets.selectors['biophys'],
                self.widgets.selectors['stimuli'],
            ],
            align='center',
        )

        if self.p.config['dev_tools']['allow_file_io']:
            self._create_file_name_text_input()
            self._create_export_model_button()
            self._create_download_model_button()

            export_layout = column(
                [
                    Div(text='File Export', align='center', styles={'padding-top': '20px'}),
                    # self.widgets.file_input['all'],
                    self.widgets.text['file_name'],
                    self.widgets.buttons['export_model'],
                    self.widgets.buttons['download_model'],
                ],
                align='center',
            )
        else:
            export_layout = column(
                [
                    Div(text='File Export', align='center', styles={'padding-top': '20px'}),
                    Div(text='File upload/download is disabled in this version.', align='center'),
                ],
                align='center',
            )

        io_layout = column(
            [
                import_layout,
                export_layout,
            ],
            align='center',
        )

        self.widgets.tab_panels['io'] = TabPanel(
            title='Import/Export', 
            child=io_layout,
        )

    # ------------------------------------------------------------------------------------
    ## Simulation tab panel                            
    # ------------------------------------------------------------------------------------

    # Segmentation
    def _create_d_lambda_slider(self):
        self.widgets.sliders['d_lambda'] = Slider(
            start=0, 
            end=0.2, 
            value=0.1, 
            step=0.01, 
            title="d_lambda", 
            width=242, 
            align='center'
        )

    def _create_set_segmentation_button(self):
        self.widgets.buttons['set_segmentation'] = Button(
            label='Set segmentation', 
            button_type='primary', 
            disabled=False, 
            width=242, 
            align='center'
        )
        self.widgets.buttons['set_segmentation'].on_event(ButtonClick, self.p.build_seg_tree_callback)


    # Simulation

    def _create_duration_slider(self):
        self.widgets.sliders['duration'] = Slider(
            value=300,
            start=100,
            end=1000,
            step=100,
            title='Duration, ms',
            format='0[.]0',
            width=242,
            align='center'
        )
        self.widgets.sliders['duration'].js_link('value', self.widgets.sliders['iclamp_duration'], 'end')
        self.widgets.sliders['duration'].on_change('value_throttled', self.p.voltage_callback_on_change)


    def _create_dt_slider(self):
        self.widgets.sliders['dt'] = Slider(
            value=0.025,
            start=0.025,
            end=0.1,
            step=0.025, 
            title='dt, ms',
            format='0[.]000',
            width=242,
            align='center'
        )
        self.widgets.sliders['dt'].on_change('value_throttled', self.p.update_dt_callback)
        self.widgets.sliders['dt'].on_change('value_throttled', self.p.voltage_callback_on_change)


    def _create_temperature_slider(self):
        self.widgets.sliders['temperature'] = Slider(
            value=37,
            start=0,
            end=45,
            step=0.1, 
            title='Temperature, °C',
            format='0[.]0',
            width=242,
            align='center'
        )
        self.widgets.sliders['temperature'].on_change('value_throttled', self.p.update_temperature_callback)
        self.widgets.sliders['temperature'].on_change('value_throttled', self.p.voltage_callback_on_change)


    def _create_v_init_slider(self):
        self.widgets.sliders['v_init'] = Slider(
            value=-70, 
            start=-100, 
            end=100, 
            step=0.5, 
            title='V init, mV', 
            format='0[.]0', 
            width=242, 
            align='center'
        )
        self.widgets.sliders['v_init'].on_change('value_throttled', self.p.update_v_init_callback)
        self.widgets.sliders['v_init'].on_change('value_throttled', self.p.voltage_callback_on_change)

    # Run

    def _create_run_on_interaction_switch(self):
        self.widgets.switches['run_on_interaction'] = Switch(
            active=self.p.config['simulation']['run_on_interaction']
        )
        def enable_run_button(attr, old, new):
            self.widgets.buttons['run'].disabled = new
        self.widgets.switches['run_on_interaction'].on_change('active', enable_run_button)


    def _create_run_button(self):
        
        self.DOM_elements['runtime'] = Div(text='', align='center')

        self.widgets.buttons['run'] = Button(
            label='Run',
            button_type='primary',
            width=242,
            height=50,
            disabled=True,
            align='center'
        )
        runtime_callback = CustomJS(args=dict(runtime=self.DOM_elements['runtime']), code="""
            runtime.text = '<img src="app/static/images/loading.gif" alt="Loading..." width="20" height="20">';
        """)
        self.widgets.buttons['run'].js_on_click(runtime_callback)    
        self.widgets.buttons['run'].on_event(ButtonClick, self.p.voltage_callback_on_click)


    # Tab panel

    def _create_simulation_tab_panel(self):

        self._create_d_lambda_slider()
        self._create_set_segmentation_button()
        self._create_duration_slider()
        self._create_dt_slider()
        self._create_temperature_slider()
        self._create_v_init_slider()
        self._create_run_on_interaction_switch()
        self._create_run_button()
        
        simulation_layout = column(
            [
                Div(text='Segmentation', align='center', styles={'padding-top': '20px'}),
                self.widgets.sliders['d_lambda'],
                self.widgets.buttons['set_segmentation'],
                Div(text='Simulation parameters', align='center', styles={'padding-top': '20px'}),
                self.widgets.sliders['duration'],
                self.widgets.sliders['dt'],
                self.widgets.sliders['temperature'],
                self.widgets.sliders['v_init'],
                Div(text='Simulation controls', align='center', styles={'padding-top': '20px'}),
                row(self.widgets.switches['run_on_interaction'], Div(text='Run on interaction'), align='center'),
                self.widgets.buttons['run'],
                self.DOM_elements['runtime'],
            ],
            align='center',
            width=280,
        )

        self.widgets.tab_panels['simulation'] = TabPanel(
            title='Simulation',
            child=simulation_layout,
        )


    # ------------------------------------------------------------------------------------
    # Assembling the left menu
    # ------------------------------------------------------------------------------------

    def _create_left_menu_tabs(self):

        self._create_io_tab_panel()
        self._create_simulation_tab_panel()

        self.widgets.tabs['left_menu'] = Tabs(
            tabs=[
                self.widgets.tab_panels['io'],
                self.widgets.tab_panels['simulation'],
            ],
            visible=True,
        )

    
    def _create_status_bar(self):

        self.DOM_elements['status'] = Div(
            text='Select a model to start', 
            height=50,
            width=300, align='center',
            styles={
                'color': self.theme.status_colors['info'],
                'margin': '10px',
                'background-color': 'rgba(125, 125, 125, 0.1)',
                'padding': '10px',
                'border-radius': '5px',
            }
        )


    def create_left_menu(self):

        self._create_left_menu_tabs()

        return column(
            [
            Div(
                text='<img id="logo" src="https://dendrotweaks.readthedocs.io/en/latest/_static/logo.png" alt="logo" width="200">',
                align='center'
            ),
            self.DOM_elements['status'],
            self.widgets.tabs['left_menu']
            ],
            width=300,
            height=940,
            name='left_menu',
            styles={
            'padding': '10px',
            'background-color': '#20262B',
            },
        )

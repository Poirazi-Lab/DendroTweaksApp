from bokeh.models import Select, Button, RangeSlider, TextInput, Div, Switch
from bokeh.layouts import column, row
from bokeh.events import ButtonClick
from bokeh.models import CustomJS
from bokeh.models import ColumnDataSource
from bokeh.models import MultiLine
from bokeh.models import Patches
from bokeh.models import ColorPicker


class SettingsMixin():

    def __init__(self):
        super().__init__()


    def _create_console(self):
        
        console = TextInput(value='Only for development', title='Console', width=500, height=50, name='console', disabled=False)
        console.on_change('value', self.p.console_callback)

        status_bar = Div(text="""Launched GUI""", name='status_bar', styles={'width': '500px', 'height':'100px', 
                                                                            'overflow': 'auto', 'font-size': '12px'})
        self.DOM_elements['status_bar'] = status_bar
        self.DOM_elements['console'] = console
        self.DOM_elements['controller'] = column(console, status_bar, name='status_bar')
            

    def _create_voltage_plot_settings(self):

        # self.widgets.switches['enable_record_from_all'] = Switch(active=False, name='enable_record_from_all')
        # def enable_record_from_all_callback(attr, old, new):
        #     self.widgets.switches['record_from_all'].disabled = not new

        # self.widgets.switches['enable_record_from_all'].on_change('active', enable_record_from_all_callback)
        # self.widgets.switches['show_kinetics'] = Switch(active=True, name='show_kinetics')

        self.widgets.sliders['voltage_plot_x_range'] = RangeSlider(
            start=0, 
            end=1000, 
            value=(0, 300), 
            step=1, 
            title='Voltage plot x range', 
            width=200
        )
        self.widgets.sliders['voltage_plot_y_range'] = RangeSlider(
            start=-200, 
            end=200, 
            value=(
                self.p.config['appearance']['plots']['voltage_plot']['ymin'], 
                self.p.config['appearance']['plots']['voltage_plot']['ymax']
            ),
            step=1,
            title='Voltage plot y range',
            width=200
        )

        def update_voltage_plot_x_range(attr, old, new):
            self.figures['sim'].x_range.start = new[0]
            self.figures['sim'].x_range.end = new[1]

        def update_voltage_plot_y_range(attr, old, new):
            self.figures['sim'].y_range.start = new[0]
            self.figures['sim'].y_range.end = new[1]

        self.widgets.sliders['voltage_plot_x_range'].on_change('value_throttled', update_voltage_plot_x_range)
        self.widgets.sliders['voltage_plot_y_range'].on_change('value_throttled', update_voltage_plot_y_range)


    def _create_graph_layout_selector(self):

        self.widgets.selectors['graph_layout'] = Select(title='Graph layout', 
            options=['kamada-kawai', 'dot', 'neato', 'twopi'], 
            value=self.p.config['appearance']['plots']['graph_plot']['layout'],
        )
        self.widgets.selectors['graph_layout'].on_change('value', self.p.update_graph_layout_callback)

    # Simulation
    def _create_simulator_selector(self):
        self.widgets.selectors['simulator'] = Select(title='Simulator',
                                                    value=self.p.config['simulation']['simulator'],
                                                    options=['NEURON', 'Jaxley'],
                                                    width=200)
        if not self.p.config['dev_tools']['choose_simulator']:
            self.widgets.selectors['simulator'].disabled = True

    def _create_cvode_switch(self):
        self.widgets.switches['cvode'] = Switch(
            active=self.p.config['simulation']['cvode'], 
            disabled=True,
            name='cvode'
            )
        self.widgets.switches['cvode'].on_change('active', self.p.update_cvode_callback)

    def _create_save_preferences_button(self):

        self.widgets.buttons['save_preferences'] = Button(label='Save preferences', button_type='warning', width=200)
        self.widgets.buttons['save_preferences'].on_event(ButtonClick, self.p.save_preferences_callback)

        if not self.p.config['dev_tools']['save_preferences']:
            self.widgets.buttons['save_preferences'].visible = False


    def create_settings_panel(self):

        if self.p.config['dev_tools']['console']:
            self._create_console()
        else:
            self.DOM_elements['controller'] = Div(text='Console disabled', name='status_bar')
        # self._create_theme_selector()
        self._create_voltage_plot_settings()
        self._create_graph_layout_selector()
        self._create_simulator_selector()
        self._create_cvode_switch()
        self._create_save_preferences_button()


        settings = column(
            [
            Div(text='Settings', styles={'font-size': '20px', 'font-weight': 'bold'}),
            Div(text='For more information, visit <a href="https://dendrotweaks.dendrites.gr" target="_blank" style="color: dodgerblue;">DendroTweaks online platform</a>'),
            
            Div(text='Appearance', styles={'font-size': '16px', 'font-weight': 'bold'}),
            self.widgets.selectors['theme'],
            # self.widgets.switches['show_kinetics'],
            self.widgets.sliders['voltage_plot_x_range'],
            self.widgets.sliders['voltage_plot_y_range'],
            # row(self.widgets.switches['enable_record_from_all'], Div(text='Enable record from all')),
            self.widgets.selectors['graph_layout'],
            Div(text='Simulation', styles={'font-size': '16px', 'font-weight': 'bold'}),
            self.widgets.selectors['simulator'],
            row(self.widgets.switches['cvode'], Div(text='Use adaptive time step (CVode)')),
            Div(text='Development tools', styles={'font-size': '16px', 'font-weight': 'bold'}),
            self.widgets.buttons['save_preferences'],
            self.DOM_elements['controller'],
            ],
            name='settings_panel',

        )

        self.layout_elements['settings'] = settings

        return settings
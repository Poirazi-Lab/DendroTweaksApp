import numpy as np
import pprint

from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

from bokeh.models import Slider, TabPanel, Tabs, Button, Spinner
from bokeh_utils import AdjustableSpinner
from bokeh.layouts import row, column
from bokeh.models import Div
from bokeh.palettes import Bokeh
from bokeh.models import LogScale

from model.mechanisms.channels import StandardIonChannel

from model.mechanisms.distributions import Distribution


class ChannelMixin():
    """ This class is a mixin for the Presenter class. 
    It provides methods for handling the Channel panel of the View.
    """

    def __init__(self):
        logger.debug('ChannelMixin init')
        super().__init__()


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
            slider = AdjustableSpinner(title=var, value=getattr(ch, var))
            slider.on_change('value_throttled', make_slider_callback(slider.title))
            slider.on_change('value_throttled', self.states_callback)
            slider.on_change('value_throttled', self.voltage_callback_on_change)
            sliders.append(slider.get_widget())
            
        ch.sliders = sliders
        
        if sliders:
            if 'standard' in ch.name:
                return column([*sliders])
            else:
                return column([button, *sliders])
        else:
           return column([button, Div(text='No sliders to display. Try declaring some RANGE variables in the mod file (requires reuploading the file).')])
                   
        # return panel


    @log
    def standardize_callback(self, event):
        custom_ch = self.selected_channel
        copy_of_groups = custom_ch.to_dict()["groups"]

        self.model.standardize_channel(custom_ch)
        logger.info(f'Standardized {custom_ch.name}')
        
        # logger.debug(f'Avaliable groups before: {len(custom_ch.to_dict()["groups"])}')
        self.view.widgets.multichoice['mod_files'].value = [v for v in self.view.widgets.multichoice['mod_files'].value if v != custom_ch.name]
        # logger.debug(f'Avaliable groups after: {len(custom_ch.to_dict()["groups"])}')
        self.view.widgets.multichoice['mod_files_std'].value = self.view.widgets.multichoice['mod_files_std'].value + [f'{custom_ch.name}_standard']
        

        # open the new chanel's tab
        # with remove_callbacks(self.view.widgets.selectors['channel']):
        self.view.widgets.selectors['channel'].value = f'{custom_ch.name}_standard'
        

        standard_ch = self.model.channels[f'{custom_ch.name}_standard']
        v_range = np.linspace(-100, 100, 1000)
        standard_ch.update(v_range)

        
        for group in copy_of_groups:
            segments = [self.model.cell.segments[seg_name] for seg_name in group['seg_names']]
            standard_ch.add_group(segments, 
                                  param_name=f"{group['param_name']}s", 
                                  distribution=Distribution.from_dict(group['distribution']))
        self.update_graph_param(f"{group['param_name']}s")

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
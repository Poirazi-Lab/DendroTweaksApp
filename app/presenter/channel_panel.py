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

# from model.mechanisms.channels import StandardIonChannel

# from model.mechanisms.distributions import Distribution


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
            self.view.figures['inf'].visible = False
            self.view.figures['inf_log'].visible = True
            self.view.figures['tau'].visible = False
            self.view.figures['tau_log'].visible = True
        else: 
            logger.debug('Using linear scale for x-axis')
            x_range = np.linspace(-100, 100, 1000)
            self.view.figures['inf_log'].visible = False
            self.view.figures['inf'].visible = True
            self.view.figures['tau_log'].visible = False
            self.view.figures['tau'].visible = True

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
    def standardize_callback(self, event):

        ch_name = self.view.widgets.selectors['mechanism'].value
        
        self.model.standardize_channel(ch_name)

        self._update_multichoice_domain_widget()
        self._update_mechs_to_insert_widget()
        self._update_multichoice_mechanisms_widget()
        
        self._update_mechanism_selector_widget()
        self._select_mechanism(f'std{ch_name}')
        self.view.widgets.buttons['standardize'].visible = False
        
        standard_ch = self.model.mechanisms[f'std{ch_name}']
        data = standard_ch.get_data()
        x = data.pop('x')
        # data is of the form {'state_var': {'inf': [], 'tau': []}}

        
        inf_fit_data = {'xs': [x for _ in range(len(data))],
                        'ys': [state['inf'] for state in data.values()],
                        'label': [state for state in data.keys()],
                        'color': [Bokeh[8][2*i+2] for i in range(len(data))]
                        }
        tau_fit_data = {'xs': [x for _ in range(len(data))],
                        'ys': [state['tau'] for state in data.values()],
                        'label': [state for state in data.keys()],
                        'color': [Bokeh[8][2*i+2] for i in range(len(data))]
                        }
                        

        self.view.sources['inf_fit'].data = inf_fit_data
        self.view.sources['tau_fit'].data = tau_fit_data

        self.update_status_message(f'Channel {ch_name} standardized', status='success')
        
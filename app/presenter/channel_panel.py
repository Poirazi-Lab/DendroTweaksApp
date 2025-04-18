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
    def standardize_callback(self, event):

        ch_name = self.view.widgets.selectors['mechanism'].value
        
        self.model.standardize_channel(ch_name)

        self._update_multichoice_domain_widget()
        self._update_mechs_to_insert_widget()
        self._update_multichoice_mechanisms_widget()
        
        self._update_mechanism_selector_widget()
        self._update_recording_variable_selector_widget()
        self._select_mechanism(f'std{ch_name}')
        self.view.widgets.buttons['standardize'].visible = False
        
        standard_ch = self.model.mechanisms[f'std{ch_name}']
        data = standard_ch.get_data()
        x = data.pop('x')
        # data is of the form {'state_var': {'inf': [], 'tau': []}}

        
        inf_fit_data = {'xs': [x for _ in range(len(data))],
                        'ys': [state['inf'] for state in data.values()],
                        'label': [state for state in data.keys()],
                        'line_color': [Bokeh[8][2*i+2] for i in range(len(data))]
                        }
        tau_fit_data = {'xs': [x for _ in range(len(data))],
                        'ys': [state['tau'] for state in data.values()],
                        'label': [state for state in data.keys()],
                        'line_color': [Bokeh[8][2*i+2] for i in range(len(data))]
                        }
                        

        self.view.sources['inf_fit'].data = inf_fit_data
        self.view.sources['tau_fit'].data = tau_fit_data

        self.update_status_message(f'Channel {ch_name} standardized', status='success')
        
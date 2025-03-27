import networkx as nx
import numpy as np

import os

import networkx as nx
from bokeh.plotting import figure, show
from bokeh.models import Plot, Range1d, Circle, HoverTool
from bokeh.plotting import from_networkx, show
from bokeh.layouts import row, column
from bokeh.io import curdoc

from bokeh.models import Select, MultiChoice
from bokeh.models import Button, Dropdown
from bokeh.events import ButtonClick
from bokeh.models import Patches
from bokeh.models import LinearColorMapper, CategoricalColorMapper
from bokeh.palettes import viridis, inferno, magma, plasma, gray, cividis
from bokeh.palettes import Reds256, Blues256, Greens256, Oranges256, Purples256, Greys256 #YlGnBu256

from bokeh.models import WheelZoomTool
from bokeh.models import TapTool

from bokeh.models import MultiLine
from bokeh.models import Span

from bokeh.models import ColorPicker

from bokeh.events import Tap

from bokeh.models import LassoSelectTool

from bokeh.models import ColumnDataSource, MultiLine

from bokeh.models import Tabs, TabPanel
from bokeh.models import InlineStyleSheet, Slider
from bokeh.models import NumericInput
from bokeh.models import Spinner, RadioButtonGroup

from bokeh.models import RangeSlider
from bokeh.models import Div
from bokeh.models import Switch
from bokeh.models import TextInput, AutocompleteInput
from bokeh.models import FileInput

from logger import logger

from bokeh.models import CustomJS

import colorcet as cc

from utils import get_sec_name, get_sec_type, get_sec_id

from collections import defaultdict

from bokeh_utils import AdjustableSpinner
import json

import dendrotweaks as dd

# =================================================================
# CONSTANTS
# =================================================================

AVAILABLE_DOMAINS = [
    'soma', 'perisomatic', 
    'axon', 
    'dend', 'basal', 
    'apic', 'trunk', 'tuft', 'oblique', 
    'custom_0', 'custom_1', 'custom_2', 'custom_3'
]

# =================================================================
# LOAD CONFIG
# =================================================================

with open('app/default_config.json', 'r') as f:
    default_config = json.load(f)

with open('app/user_config.json', 'r') as f:
    user_config = json.load(f)

default_config.update(**user_config)
config = default_config

theme_name = config['appearance']['theme']
path_to_data = config['data']['path_to_data']
simulator = config['simulation']['simulator']


# =================================================================
# INITIALIZATION
# =================================================================

from view.view import CellView
view = CellView(theme=theme_name)

from presenter.presenter import Presenter
p = Presenter(path_to_data=path_to_data, view=view, model=None, simulator=simulator)
p.config = config

view.create_status_bar()



# =================================================================
# WORKSPACE
# =================================================================

# CELL PANEL
panel_cell = view.create_cell_panel()
curdoc().add_root(panel_cell)

# SECTION PANEL
panel_section = view.create_section_panel()

# GRAPH PANEL
panel_graph = view.create_graph_panel()
curdoc().add_root(panel_graph)

# SIMULATION PANEL
panel_simulation = view.create_simulation_panel()
curdoc().add_root(panel_simulation)


# =================================================================
# RIGHT MENU
# =================================================================

# -----------------------------------------------------------------
# MORPHOLOGY TAB
# -----------------------------------------------------------------

# ## Auxillary plots

# view.figures['diam_distribution'] = figure(width=400,
#                                         height=150,
#                                         match_aspect=False,
#                                         tools='pan, box_zoom, hover, reset, save',)

# view.figures['diam_distribution'].toolbar.autohide = True
# view.figures['diam_distribution'].background_fill_color = None
# view.figures['diam_distribution'].border_fill_color = None
# view.sources['diam_distribution'] = ColumnDataSource(data={'x': [], 'y': []})

# view.figures['diam_distribution'].circle(x='x', y='y', source=view.sources['diam_distribution'], line_width=2, color='color')
# view.figures['diam_distribution'].y_range.start = 0

# section_plots = column(
#     [view.figures['section_diam'], 
#     view.figures['section_param']],
#     sizing_mode='stretch_width',
#     height=200
# )

# ## Assembling the panel

# navigation_panel = column([
#                         row([view.widgets.selectors['section'],
#                             view.widgets.selectors['seg_x'],
#                         ]),
#                         row([
#                           view.widgets.buttons['parent'], 
#                           view.widgets.buttons['sibling'], 
#                           view.widgets.buttons['child']]
#                         )
#                         ])

# view.layout_elements['section'] = column(
#     [
#         Div(text='<h3>Navigation</h3>'),
#         navigation_panel,
#         Div(text='<h3>Section parameters</h3>'),
#         section_param_panel,
#         Div(text='<h3>Auxillary plots</h3>'),
#         section_plots
#     ],
#     sizing_mode='stretch_width',
# )



# # =================================================================
# # PARAMETERS TAB
# # =================================================================


# def create_distribution_plot():

#     view.figures['distribution'] = figure(width=400,
#                                           height=150,
#                                           match_aspect=False,
#                                           tools='pan, box_zoom, hover, reset, save',)

#     view.figures['distribution'].toolbar.autohide = True
#     view.figures['distribution'].background_fill_color = None
#     view.figures['distribution'].border_fill_color = None

#     view.sources['distribution'] = ColumnDataSource(data={'x': [], 'y': []})

#     view.figures['distribution'].circle(x='x', y='y', source=view.sources['distribution'], line_width=2, color='color')
#     hspan = Span(location=0, dimension='width', line_color='white', line_width=1)
#     view.figures['distribution'].add_layout(hspan)
#     vspan = Span(location=0, dimension='height', line_color='white', line_width=1)
#     view.figures['distribution'].add_layout(vspan)



# # -----------------------------------------------------------
# # STIMULI TAB 
# # -----------------------------------------------------------

# # -----------------------------------------------------------
# # SYNAPSES
# # -----------------------------------------------------------

# # ADD POPULATION

# view.widgets.selectors['syn_type'] = Select(
#     title='Synaptic type', 
#     value='AMPA_NMDA', 
#     options=['AMPA', 'NMDA', 'AMPA_NMDA', 'GABAa'], 
#     width=150
# )
# view.widgets.selectors['syn_type'].on_change('value', p.select_synapse_type_callback)

# view.widgets.spinners['N_syn'] = NumericInput(value=1, title='N syn', width=100)

# view.widgets.buttons['add_population'] = Button(label='Add population', 
#                                                 button_type='primary', 
#                                                 disabled=False)
# view.add_message(view.widgets.buttons['add_population'], 'Adding population. Please wait...', callback_type='on_click')
# view.widgets.buttons['add_population'].on_event(ButtonClick, 
#                                                 p.add_population_callback)
# view.widgets.buttons['add_population'].on_event(ButtonClick, 
#                                                 p.voltage_callback_on_event)

# # SELECT / REMOVE POPULATION

# view.widgets.selectors['population'] = Select(options=[], title='Population', width=150)
# view.widgets.selectors['population'].on_change('value', p.select_population_callback)

# view.widgets.buttons['remove_population'] = Button(label='Remove population', button_type='danger', disabled=False, styles={"padding-top":"20px"})
# view.widgets.buttons['remove_population'].on_event(ButtonClick, p.remove_population_callback)
# view.widgets.buttons['remove_population'].on_event(ButtonClick, p.voltage_callback_on_event)

# view.DOM_elements['population_panel'] = column(width=300)

# widgets_stimuli = column([
#     view.widgets.buttons['remove_all'],
#     row([view.widgets.selectors['section'],
#     view.widgets.selectors['seg_x']]),
#     row([view.widgets.switches['iclamp'], Div(text='Inject current')]),
#     view.widgets.sliders['iclamp_duration'], 
#     view.widgets.sliders['iclamp_amp'].get_widget(),
#     Div(text='<hr style="width:30em">'),
#     row([view.widgets.selectors['syn_type'], view.widgets.spinners['N_syn']]),
#     view.widgets.buttons['add_population'],
#     Div(text='<hr style="width:30em">'),
#     row([view.widgets.selectors['population'], view.widgets.buttons['remove_population']]),
#     view.DOM_elements['population_panel'],
# ])

# widgets_recordings = column([
#     row([view.widgets.selectors['section'],
#     view.widgets.selectors['seg_x']]),
#     row([view.widgets.switches['record_from_all'], Div(text='Record from all')]),
#     row([view.widgets.switches['record'], Div(text='Record voltage')]),
# ])



right_menu = view.create_right_menu()
curdoc().add_root(right_menu)









# ====================================================================================
# LEFT MENU
# ====================================================================================

left_menu = view.create_left_menu()
curdoc().add_root(left_menu)









# ====================================================================================
# SETTINGS
# ====================================================================================

console = TextInput(value='Only for development', title='Console', width=500, height=50, name='console', disabled=False)
console.on_change('value', p.console_callback)

status_bar = Div(text="""Launched GUI""", name='status_bar', styles={'width': '500px', 'height':'200px', 
                                                                     'overflow': 'auto', 'font-size': '12px'})
view.DOM_elements['status_bar'] = status_bar
view.DOM_elements['console'] = console
view.DOM_elements['controller'] = column(console, status_bar, name='status_bar')

view.widgets.selectors['output_format'] = Select(title="Output format:",
                                                value='png',
                                                options=['canvas', 'svg', 'webgl'],
                                                name='output_format')



def update_output_format(attr, old, new):
    for fig in view.figures.values():
        print(f'Before: {fig.output_backend}')
        fig.output_backend = new
        print(f'After: {fig.output_backend}')

view.widgets.selectors['output_format'].on_change('value', update_output_format)

view.widgets.color_pickers['color_picker'] = ColorPicker(title='Background color', color='red', width=50, height=20)

def update_background_color(attr, old, new):
    view.theme.background_fill_color = new
    for fig in view.figures.values():
            if fig.background_fill_color is not None:
                fig.background_fill_color = new
    
view.widgets.color_pickers['color_picker'].on_change('color', update_background_color)

view.widgets.sliders['voltage_plot_x_range'] = RangeSlider(start=0, end=1000, value=(0, 300), step=1, title='Voltage plot x range', width=200)
view.widgets.sliders['voltage_plot_y_range'] = RangeSlider(
    start=-200, 
    end=200, 
    value=(config['appearance']['plots']['voltage_plot']['ymin'], config['appearance']['plots']['voltage_plot']['ymax']),
    step=1, title='Voltage plot y range', width=200)

view.widgets.switches['enable_record_from_all'] = Switch(active=False, name='enable_record_from_all')

def enable_record_from_all_callback(attr, old, new):
    view.widgets.switches['record_from_all'].disabled = not new

view.widgets.switches['enable_record_from_all'].on_change('active', enable_record_from_all_callback)

def update_voltage_plot_x_range(attr, old, new):
    view.figures['sim'].x_range.start = new[0]
    view.figures['sim'].x_range.end = new[1]

def update_voltage_plot_y_range(attr, old, new):
    view.figures['sim'].y_range.start = new[0]
    view.figures['sim'].y_range.end = new[1]

view.widgets.switches['show_kinetics'] = Switch(active=True, name='show_kinetics')

view.widgets.sliders['voltage_plot_x_range'].on_change('value_throttled', update_voltage_plot_x_range)
view.widgets.sliders['voltage_plot_y_range'].on_change('value_throttled', update_voltage_plot_y_range)

view.widgets.selectors['graph_layout'] = Select(title='Graph layout', 
    options=['kamada-kawai', 'dot', 'neato', 'twopi'], 
    value=config['appearance']['plots']['graph_plot']['layout'],
)

# Simulation

view.widgets.selectors['simulator'] = Select(title='Simulator',
                                            value=config['simulation']['simulator'],
                                            options=['NEURON', 'Jaxley'],
                                            width=200)

view.widgets.buttons['save_preferences'] = Button(label='Save preferences', button_type='warning', width=200)
view.widgets.buttons['save_preferences'].on_event(ButtonClick, p.save_preferences_callback)

settings_panel = column(view.widgets.selectors['theme'],
                        # view.widgets.selectors['output_format'],
                        # view.widgets.color_pickers['color_picker'],
                        view.widgets.switches['show_kinetics'],
                        view.widgets.sliders['voltage_plot_x_range'],
                        view.widgets.sliders['voltage_plot_y_range'],
                        row(view.widgets.switches['enable_record_from_all'], Div(text='Enable record from all')),
                        view.widgets.selectors['graph_layout'],
                        view.widgets.selectors['simulator'],
                        view.widgets.buttons['save_preferences'],
                        view.DOM_elements['controller'],
                        name='settings_panel')

curdoc().add_root(settings_panel)

for name, fig in view.figures.items():
    fig.toolbar.logo = None
#     fig.background_fill_color = None
    # logger.info(f'Background color: {fig.background_fill_color}')
    fig.border_fill_color = None
    # if name == 'graph':
    fig.output_backend = "svg"
    # else:
    #     fig.output_backend = "webgl"
    
    
    
    if name in ['cell', 'graph']:
        fig.toolbar.logo = None
        fig.grid.visible = False
        
        fig.axis.visible = False
        
        fig.outline_line_color = None

# for slider in view.widgets.sliders.values():
#     slider.background = None

# ====================================================================================
# ON LOAD
# ====================================================================================

curdoc().theme = theme_name
curdoc().on_event('document_ready', lambda event: setattr(view.widgets.selectors['theme'], 'value', theme_name))
# curdoc().on_event('document_ready', lambda event: setattr(view.widgets.tabs['right_menu'], 'disabled', True))

curdoc().js_on_event('document_ready', CustomJS(code="""
    console.log('Document ready');
"""))

# custom_js = CustomJS(args=dict(), code="""
#     console.log('Before');
    
#     const columnElement = document.querySelector('.bk-Column');
#     const TabsElement = columnElement.shadowRoot.querySelector('.bk-Tabs');
#     const columnElement2 = TabsElement.shadowRoot.querySelector('.bk-Column');
#     const MultiChoiceElement = columnElement2.shadowRoot.querySelector('.bk-MultiChoice');
#     const choicesInner = MultiChoiceElement.shadowRoot.querySelector('.choices__inner');

#     choicesInner.style.height = '100px';
#     choicesInner.style.overflow = 'auto';

#     console.log('After');
# """)

# view.widgets.buttons['from_json'].js_on_event(ButtonClick, custom_js)
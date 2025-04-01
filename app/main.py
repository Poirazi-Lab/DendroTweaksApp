import os
import json
import numpy as np

from bokeh.plotting import figure

from bokeh.models import CustomJS
from bokeh.io import curdoc

from logger import logger

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

view._create_status_bar()



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

view.menus['right_menu'] = view.create_right_menu()
curdoc().add_root(view.menus['right_menu'])


# ====================================================================================
# LEFT MENU
# ====================================================================================

view.menus['left_menu'] = view.create_left_menu()
curdoc().add_root(view.menus['left_menu'])


# ====================================================================================
# SETTINGS
# ====================================================================================

settings_panel = view.create_settings_panel()
curdoc().add_root(settings_panel)


# ====================================================================================
# FIGURE ADJUSTMENTS
# ====================================================================================

for name, fig in view.figures.items():
    fig.toolbar.logo = None
    # fig.background_fill_color = None
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
curdoc().on_event('document_ready', lambda event: setattr(view.widgets.selectors['protocol'], 'value', 'Somatic spikes'))
# curdoc().on_event('document_ready', lambda event: setattr(view.menus['right_menu'], 'visible', False))

curdoc().js_on_event('document_ready', CustomJS(code="""
    console.log('Document ready');
"""))
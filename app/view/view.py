from collections import defaultdict

from bokeh.models import ColumnDataSource, Select, Slider, Button

from bokeh.plotting import figure

from bokeh.models import Tabs, TabPanel

from dataclasses import dataclass, field

from bokeh.layouts import column, row

from bokeh.models import CustomJS

from bokeh.io import curdoc

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import colorcet as cc

from view.left_menu import LeftMenuMixin
from view.right_menu import RightMenuMixin
from view.workspace import WorkspaceMixin
from view.settings import SettingsMixin
from view.auxiliary import AuxiliaryMixin

from bokeh.models import Div


DARK_PALETTES = {
    'trace': ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'continuous': cc.glasbey_dark,
    'params': cc.rainbow4,
}

LIGHT_PALETTES = {
    'trace': ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'continuous': cc.glasbey_light,
    'params': cc.rainbow4,
}

DARK_STATUS_COLORS = {
    'info': 'magenta',
    'success': 'lawngreen',
    'warning': 'orange',
    'error': 'red',
}

LIGHT_STATUS_COLORS = {
    'info': 'magenta',
    'success': 'seagreen',
    'warning': 'darkorange',
    'error': 'red',
}

DARK_GRAPH_COLORS = {
    'edge': 'white',
    'node_fill': '#15191C'
}

LIGHT_GRAPH_COLORS = {
    'edge': 'black',
    'node_fill': 'white'
}

class Theme:
    def __init__(self, name, selected_sec, graph_colors, background_fill_color, status_colors, frozen, palettes):
        self.name = name
        self.selected_sec = selected_sec
        self.graph_colors = graph_colors
        self.background_fill_color = background_fill_color
        self.palettes = palettes
        self.status_colors = status_colors
        self.frozen = frozen
        self.primary_background_color = '#15191c' if 'dark' in name else '#ebe6e4'
        self.secondary_background_color = '#20262b' if 'dark' in name else '#d8d2d0'

THEMES = {
    'dark_minimal': Theme('dark_minimal', '#f064ae', DARK_GRAPH_COLORS, '#20262B', DARK_STATUS_COLORS, 'white', DARK_PALETTES),
    'light_minimal': Theme('light_minimal', '#f064ae', LIGHT_GRAPH_COLORS, 'white', LIGHT_STATUS_COLORS, 'black', LIGHT_PALETTES),
}


PARAMS_TO_UNITS = {
    'morph': {'domain': 'Section domain',
              'diam': 'Diameter (μm)',
              'area': 'Area (μm²)',
              'subtree_size': 'Subtree size',
              'section_diam': 'Diameter (μm)',
              'distance': 'Distance to soma (μm)',
              'domain_distance': 'Distance to parent domain (μm)',
              'Ra': 'Axial resistance (Ωcm)',
              },
    'ephys': {'cm': 'Capacitance (μF/cm²)',
              'Ra': 'Axial resistance (Ωcm)',
              'gbar': 'Conductance (S/cm²)',
              },
    'sim': {'iclamps': 'Injected current (nA)',
            'rec_v': 'Voltage (mV)'
            }
}

PARAMS = {
    'Topology': ['domain', 'subtree_size'],
    'Geometry': ['diam', 'section_diam', 'area', 'distance', 'domain_distance'],
    'Stimuli': ['iclamps'],
    'Recordings': ['rec_v'],
    'Synapses': []
}


@dataclass
class WidgetManager():
    text: dict = field(default_factory=dict)
    selectors: dict = field(default_factory=dict)
    sliders: dict = field(default_factory=dict)
    buttons: dict = field(default_factory=dict)
    switches: dict = field(default_factory=dict)
    spinners: defaultdict = field(default_factory=lambda: defaultdict(dict))
    multichoice: defaultdict = field(default_factory=lambda: defaultdict(dict))
    color_pickers: dict = field(default_factory=dict)
    tabs: dict = field(default_factory=dict)
    tab_panels: dict = field(default_factory=dict)
    numeric: dict = field(default_factory=dict)
    file_input: dict = field(default_factory=dict)



class CellView(LeftMenuMixin, WorkspaceMixin, RightMenuMixin, SettingsMixin, AuxiliaryMixin):
    
    def __init__(self, theme='dark_minimal'):
        super().__init__()
        self._presenter = None
        self.theme = THEMES[theme]
        self.figures = {}
        self.sources = {}
        self.renderers = {}
        self.widgets = WidgetManager()
        self.DOM_elements = {}
        self.layout_elements = {}
        self.params = PARAMS
        self._add_theme_callbacks()
        self._file_content = None
        self._filename = None
        self.recordings_color_mapper = None

    @property
    def p(self):
        return self._presenter

    def add_message(self, widget, message, callback_type='on_change', status='info'):
    
        color = self.theme.status_colors[status]

        callback = CustomJS(args=dict(status=self.DOM_elements['status']),
                            code=f"status.text = '<span style=\"color:{color}\">{message}</span>'")
        if callback_type == 'on_change':
            widget.js_on_change('value', callback)
        elif callback_type == 'on_click':
            widget.js_on_click(callback)


    def set_theme(self, theme_name):
        self.theme = THEMES[theme_name]
        
        curdoc().theme = self.theme.name

        for fig in self.figures.values():
            if fig.background_fill_color is not None:
                fig.background_fill_color = self.theme.background_fill_color

        if len(self.figures['graph'].renderers):
            renderer = self.figures['graph'].renderers[0]
            renderer.node_renderer.glyph.line_color = self.theme.graph_colors['edge']
            renderer.node_renderer.selection_glyph.line_color = self.theme.graph_colors['edge']
            renderer.node_renderer.nonselection_glyph.line_color = self.theme.graph_colors['edge']
            renderer.edge_renderer.glyph.line_color = self.theme.graph_colors['edge']

        self.layout_elements['app'].styles.update({'background-color': self.theme.primary_background_color})
        self.layout_elements['right_menu'].styles.update({'background-color': self.theme.secondary_background_color})
        self.layout_elements['left_menu'].styles.update({'background-color': self.theme.secondary_background_color})
        

        self.DOM_elements['status'].styles.update({'color': self.theme.status_colors['info']})
        

    def _add_theme_callbacks(self):

        self.widgets.selectors['theme'] = Select(title="Theme:", 
                                                value=None, 
                                                options=list(THEMES.keys()),
                                                name='theme_select')
        
        def update_theme(attr, old, new):
            self.set_theme(new)

        self.widgets.selectors['theme'].on_change("value", update_theme)

        callback = CustomJS(code="""
            var theme = cb_obj.value;

            var appContainerElement = document.querySelector('.app-container');
            var settingsContentElement = document.querySelector('.settings-content');
            
            appContainerElement.className = 'app-container ' + theme;
            settingsContentElement.className = 'settings-content ' + theme;

            console.log('Theme changed to: ' + theme);
            """
        )

        self.widgets.selectors['theme'].js_on_change("value", callback)

    def create_app(self):

        self.layout_elements['workspace'] = self.create_workspace()
        self.layout_elements['right_menu'] = self.create_right_menu()
        self.layout_elements['left_menu'] = self.create_left_menu()        

        app = row(
            self.layout_elements['left_menu'],
            self.layout_elements['workspace'],
            self.layout_elements['right_menu'],
            name='app',
            width=1914,
            height=922,
            styles={
                'background-color': self.theme.primary_background_color,
                # 'display': 'flex',
                # 'flex-direction': 'row',
                # 'align-items': 'center',
                # 'justify-content': 'center',
                },
            sizing_mode='fixed',
        )

        self.layout_elements['app'] = app

        return app
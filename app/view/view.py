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

from dendrotweaks.utils import get_domain_color

from view.left_menu import LeftMenuMixin
from view.right_menu import RightMenuMixin
from view.workspace import WorkspaceMixin
from view.settings import SettingsMixin
from view.auxiliary import AuxiliaryMixin

from bokeh.models import Div

CANOPY_COLORS = {
    'negative':[
        '#89b1fdff',
        '#16b1ffff',
        '#00a1a1ff',
        '#00865aff',
        '#006725ff',
        # '#333333ff',
    ],
    'positive':[
        # '#333333ff',
        '#615100ff',
        '#b15900ff',
        '#ff5e3fff',
        '#ff7a8fff',
        '#ff97c9ff',
    ]
}

def create_palette(palette_dict, n_colors=256):

    negative_colors = palette_dict['negative']
    positive_colors = palette_dict['positive']
    negative_palette = LinearSegmentedColormap.from_list("negative", negative_colors, N=128)
    positive_palette = LinearSegmentedColormap.from_list("positive", positive_colors, N=128)

    n_half = n_colors // 2

    colors_combined = np.vstack([
        negative_palette(np.linspace(0, 1, n_half)),
        positive_palette(np.linspace(0, 1, n_half))
    ])

    concatenated_palette = LinearSegmentedColormap.from_list("concatenated", colors_combined)

    return concatenated_palette

def palette_to_hex(palette, n_samples=256):
    color_samples = palette(np.linspace(0, 1, n_samples))
    return [f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}' for r, g, b, _ in color_samples]

def _insert_gray(palette, gray_color):
    L = len(palette)
    return palette[:L//2] + [gray_color] + palette[L//2:]

canopy = palette_to_hex(create_palette(CANOPY_COLORS))
canopy = _insert_gray(canopy, 'gray')


DARK_PALETTES = {
    'trace': ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'continuous': cc.glasbey_dark,
    'params': canopy,
}

LIGHT_PALETTES = {
    'trace': ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'continuous': cc.glasbey_light,
    'params': canopy,
}

DARK_STATUS_COLORS = {
    'info': 'gold',
    'success': 'lawngreen',
    'warning': 'salmon',
    'error': 'red',
}

LIGHT_STATUS_COLORS = {
    'info': '#85643a',
    'success': 'green',
    'warning': 'brown',
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
            'AMPA': 'Number of synapses',
            'NMDA': 'Number of synapses',
            'AMPA_NMDA': 'Number of synapses',
            'GABAa': 'Number of synapses',
            'rec_v': 'Voltage (mV)'
            }
}

PARAMS = {
    'Topology': ['domain', 'subtree_size'],
    'Geometry': ['diam', 'section_diam', 'area', 'distance', 'domain_distance'],
    'Stimuli': ['iclamps'],
    'Recordings': ['rec_v'],
    'Synapses': ['AMPA', 'NMDA', 'AMPA_NMDA', 'GABAa']
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
        self.menus = {}
        self.widgets = WidgetManager()
        self.DOM_elements = {}
        self.layout_elements = {}
        self.params = PARAMS
        self._add_theme_callbacks()
        self._file_content = None
        self._filename = None
        self.get_domain_color = get_domain_color
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
            var appElement = document.querySelector('.app');
            var leftMenuElement = document.querySelector('.left-menu');
            var mainElement = document.querySelector('.workspace');
            var rightMenuElement = document.querySelector('.right-menu');
            var settingsPanelElement = document.querySelector('.settings-content');

            appElement.className = 'app ' + theme;
            leftMenuElement.className = 'left-menu ' + theme;
            mainElement.className = 'workspace ' + theme;
            rightMenuElement.className = 'right-menu ' + theme;
            settingsPanelElement.className = 'settings-content ' + theme;

            console.log('Theme changed to: ' + theme);
            """
        )

        self.widgets.selectors['theme'].js_on_change("value", callback)

    def create_app(self):

        self.menus['workspace'] = self.create_workspace()
        self.menus['right_menu'] = self.create_right_menu()
        self.menus['left_menu'] = self.create_left_menu()        

        app = row(
            self.menus['left_menu'],
            self.menus['workspace'],
            self.menus['right_menu'],
            name='app',
            width=1914,
            height=922,
            # styles={
            #     'display': 'flex',
            #     'flex-direction': 'row',
            #     'align-items': 'center',
            #     'justify-content': 'center',
            #     },
            sizing_mode='fixed',
        )

        return app
from collections import defaultdict

from bokeh.models import ColumnDataSource, Select, Slider, Button

from bokeh.plotting import figure

from bokeh.models import Tabs, TabPanel

from dataclasses import dataclass, field

from bokeh.layouts import column, row

from bokeh.models import CustomJS

from bokeh.io import curdoc

import numpy as np

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
    numeric: dict = field(default_factory=dict)
    file_input: dict = field(default_factory=dict)

# @dataclass
# class AppManager():
#     theme: dict = field(default_factory=dict)
#     figures: dict = field(default_factory=dict)
#     sources: dict = field(default_factory=dict)
#     renderers: dict = field(default_factory=dict)
#     widgets: WidgetManager = field(default_factory=WidgetManager)
#     DOM_elements: dict = field(default_factory=dict)

DOMAINS_TO_COLORS = {
    'soma': '#E69F00',       
    'apic': '#0072B2',       
    'dend': '#019E73',       
    'basal': '#31A354',      
    'axon': '#F0E442',       
    'trunk': '#56B4E9',
    'tuft': '#A55194', #'#9467BD',
    'oblique': '#8C564B',
    'perisomatic': '#D55E00',
    # 'custom': '#BDBD22',
    'custom': '#D62728',
    'custom2': '#E377C2',
    'undefined': '#7F7F7F',
}

import colorcet as cc
from matplotlib.colors import LinearSegmentedColormap

# dark
colors1 = [
    '#7fbfcdff',
    '#71b4d5ff',
    '#6aa8dcff',
    '#7a93c8ff',
    '#7f87b8ff',
    '#7b7ba7ff',
]

#light
colors2 = [ 
    '#aa7383ff',
    '#cb7687ff',
    '#d77f7fff',
    '#dc8e7aff',
    '#f0976bff',
    '#f5a656ff',
]

# Create colormaps
custom_palette1 = LinearSegmentedColormap.from_list("custom1", colors1, N=128)
custom_palette2 = LinearSegmentedColormap.from_list("custom2", colors2, N=128)

# Sample colors from each colormap
n_colors = 256  # Total number of colors in the combined colormap
n_half = n_colors // 2  # Half the colors from each colormap

colors_combined = np.vstack([
    custom_palette1(np.linspace(0, 1, n_half)),
    np.array([[0.5, 0.5, 0.5, 1]]),  # Insert gray in the middle
    custom_palette2(np.linspace(0, 1, n_half))
])

# Create the concatenated colormap
custom_palette = LinearSegmentedColormap.from_list("concatenated", colors_combined)

custom_palette = ['#7fbfcd',
 '#7ebecd',
 '#7cbdcd',
 '#7bbdcd',
 '#7abccd',
 '#78bbce',
 '#77bace',
 '#76b9ce',
 '#74b8ce',
 '#73b8ce',
 '#72b7ce',
 '#70b6ce',
 '#6fb5ce',
 '#6eb4cf',
 '#6cb3cf',
 '#6bb3cf',
 '#6ab2cf',
 '#68b1cf',
 '#67b0cf',
 '#66afcf',
 '#64aecf',
 '#63aecf',
 '#62add0',
 '#60acd0',
 '#5fabd0',
 '#5eaad0',
 '#5ca9d0',
 '#5ba9d0',
 '#5ba8d0',
 '#5aa7d0',
 '#59a6d1',
 '#58a5d1',
 '#57a4d1',
 '#56a3d1',
 '#55a2d1',
 '#54a1d1',
 '#53a0d1',
 '#529fd1',
 '#519fd1',
 '#509ed2',
 '#4f9dd2',
 '#4e9cd2',
 '#4d9bd2',
 '#4c9ad2',
 '#4b99d2',
 '#4a98d2',
 '#4a97d2',
 '#4996d3',
 '#4896d3',
 '#4795d3',
 '#4694d3',
 '#4593d3',
 '#4692d2',
 '#4690d1',
 '#478fd0',
 '#488ecf',
 '#488dce',
 '#498ccd',
 '#4a8bcc',
 '#4a8acb',
 '#4b88ca',
 '#4c87c9',
 '#4c86c8',
 '#4d85c7',
 '#4e84c5',
 '#4f83c4',
 '#4f82c3',
 '#5081c2',
 '#517fc1',
 '#517ec0',
 '#527dbf',
 '#537cbe',
 '#537bbd',
 '#547abc',
 '#5579bb',
 '#5577ba',
 '#5676b9',
 '#5675b8',
 '#5674b7',
 '#5673b5',
 '#5672b4',
 '#5671b2',
 '#5671b1',
 '#5670b0',
 '#566fae',
 '#566ead',
 '#566dab',
 '#566caa',
 '#566ba9',
 '#556aa7',
 '#5569a6',
 '#5568a5',
 '#5567a3',
 '#5566a2',
 '#5565a0',
 '#55649f',
 '#55639e',
 '#55629c',
 '#55619b',
 '#55609a',
 '#556098',
 '#555f97',
 '#555e95',
 '#545d94',
 '#545c92',
 '#535b90',
 '#535a8e',
 '#52598d',
 '#52588b',
 '#515889',
 '#515787',
 '#505686',
 '#505584',
 '#4f5482',
 '#4f5381',
 '#4e527f',
 '#4e527d',
 '#4d517b',
 '#4d507a',
 '#4c4f78',
 '#4c4e76',
 '#4b4d74',
 '#4b4c73',
 '#4a4b71',
 '#4a4b6f',
 '#494a6d',
 '#49496c',
 '#48486a',
 '#6f4350',
 '#724351',
 '#754351',
 '#784352',
 '#7b4352',
 '#7e4353',
 '#814353',
 '#844354',
 '#874354',
 '#8a4355',
 '#8d4355',
 '#904356',
 '#934356',
 '#964357',
 '#994357',
 '#9c4358',
 '#a04358',
 '#a34359',
 '#a64359',
 '#a9435a',
 '#ac435a',
 '#af435b',
 '#b2435b',
 '#b5435c',
 '#b8435c',
 '#bb435d',
 '#bc445d',
 '#bd445d',
 '#be455d',
 '#bf465d',
 '#bf475c',
 '#c0485c',
 '#c1495c',
 '#c14a5c',
 '#c24b5c',
 '#c34c5c',
 '#c44d5c',
 '#c44e5c',
 '#c54e5c',
 '#c64f5b',
 '#c6505b',
 '#c7515b',
 '#c8525b',
 '#c8535b',
 '#c9545b',
 '#ca555b',
 '#cb565b',
 '#cb575a',
 '#cc575a',
 '#cd585a',
 '#cd595a',
 '#ce5a5a',
 '#ce5b5a',
 '#cf5c5a',
 '#cf5d5a',
 '#cf5e5a',
 '#cf605b',
 '#d0615b',
 '#d0625b',
 '#d0635b',
 '#d1645b',
 '#d1655b',
 '#d1665b',
 '#d1675b',
 '#d2685c',
 '#d2695c',
 '#d26a5c',
 '#d26b5c',
 '#d36c5c',
 '#d36d5c',
 '#d36e5c',
 '#d46f5c',
 '#d4715d',
 '#d4725d',
 '#d4735d',
 '#d5745d',
 '#d5755d',
 '#d6765d',
 '#d7775d',
 '#d8785d',
 '#d9785d',
 '#da795d',
 '#db7a5d',
 '#dc7b5d',
 '#dd7c5d',
 '#de7d5d',
 '#df7e5d',
 '#e07f5d',
 '#e1805d',
 '#e2815e',
 '#e3815e',
 '#e4825e',
 '#e5835e',
 '#e6845e',
 '#e7855e',
 '#e8865e',
 '#e8875e',
 '#e9885e',
 '#ea895e',
 '#eb8a5e',
 '#ec8b5e',
 '#ed8b5e',
 '#ee8c5e',
 '#ee8d5e',
 '#ef8e5d',
 '#ef8f5d',
 '#ef915d',
 '#ef925c',
 '#f0935c',
 '#f0945c',
 '#f0955b',
 '#f1965b',
 '#f1975b',
 '#f1985a',
 '#f1995a',
 '#f29a5a',
 '#f29b59',
 '#f29c59',
 '#f39d59',
 '#f39e59',
 '#f39f58',
 '#f3a058',
 '#f4a158',
 '#f4a257',
 '#f4a357',
 '#f4a457',
 '#f5a556',
 '#f5a656']

# # insert gray in the middle of palette
L = len(custom_palette)
custom_palette = custom_palette[:L//2] + ['gray'] + custom_palette[L//2:]

dark_palettes = {
    'domain': list(DOMAINS_TO_COLORS.values()),
    'trace': ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'continuous': cc.glasbey_dark,
    'params': custom_palette,
}

light_palettes = {
    'domain': ['orange', 'gold', '#32b499', '#1e90ff', "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'trace': ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'continuous': cc.glasbey_light,
    'params': custom_palette,
}

class Theme:
    def __init__(self, name, selected_sec, graph_edge_line, graph_fill, background_fill_color, frozen, palettes):
        self.name = name
        self.selected_sec = selected_sec
        self.graph_line = graph_edge_line
        self.graph_fill = graph_fill
        self.background_fill_color = background_fill_color
        self.palettes = palettes
        self.frozen = frozen
        self.domains_to_colors = DOMAINS_TO_COLORS

THEMES = {
    'dark_minimal': Theme('dark_minimal', '#f064ae', 'white', '#15191C', '#20262B', 'white', dark_palettes),
    # 'light_minimal': Theme('contrast', 'black', 'black', 'white', '#D8D2D0', light_palettes),
    'light_minimal': Theme('contrast', '#f064ae', 'black', 'white', 'white', 'black', light_palettes),
}


PARAMS_TO_UNITS = {
    'morph': {'domain': 'Section domain',
              'diam': 'Diameter (μm)',
              'area': 'Area (μm²)',
              'subtree_size': 'Subtree size',
              'dist': 'Distance from soma (μm)', 
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
            'recordings': 'Recordings',
            'voltage': 'Voltage',}
}

PARAMS = {
    'Topology': ['domain', 'subtree_size'],
    'Geometry': ['diam', 'area', 'distance'],
    'Stimuli': ['iclamps'],
    'Recordings': ['recordings'],
    'Synapses': ['AMPA', 'NMDA', 'AMPA_NMDA', 'GABAa']
}



class CellView():
    
    def __init__(self):
        self.theme = THEMES['dark_minimal']
        self.figures = {}
        self.sources = {}
        self.renderers = {}
        self.widgets = WidgetManager()
        self.DOM_elements = {}
        self.params = PARAMS
        self._add_theme_callbacks()
        self._file_content = None
        self._filename = None
        self.available_domains = list(DOMAINS_TO_COLORS.keys())


    def set_theme(self, theme_name):
        self.theme = THEMES[theme_name]
        
        curdoc().theme = self.theme.name

        for fig in self.figures.values():
            if fig.background_fill_color is not None:
                fig.background_fill_color = self.theme.background_fill_color

        if len(self.figures['graph'].renderers):
            renderer = self.figures['graph'].renderers[0]
            renderer.node_renderer.glyph.line_color = self.theme.graph_line
            renderer.node_renderer.selection_glyph.line_color = self.theme.graph_line
            renderer.node_renderer.nonselection_glyph.line_color = self.theme.graph_line
            renderer.edge_renderer.glyph.line_color = self.theme.graph_line

   

    def _add_theme_callbacks(self):

        self.widgets.selectors['theme'] = Select(title="Theme:", 
                                                value="dark_minimal", 
                                                options=list(THEMES.keys()),
                                                name='theme_select')
        
        def update_theme(attr, old, new):
            self.set_theme(new)

        self.widgets.selectors['theme'].on_change("value", update_theme)

        callback = CustomJS(code="""
            var theme = cb_obj.value;
            var appElement = document.querySelector('.app');
            var leftMenuElement = document.querySelector('.left-menu');
            var mainElement = document.querySelector('.main');
            var rightMenuElement = document.querySelector('.right-menu');
            var settingsPanelElement = document.querySelector('.settings-content');

            appElement.className = 'app ' + theme;
            leftMenuElement.className = 'left-menu ' + theme;
            mainElement.className = 'main ' + theme;
            rightMenuElement.className = 'right-menu ' + theme;
            settingsPanelElement.className = 'settings-content ' + theme;

            console.log('Theme changed to: ' + theme);
            """
        )

        self.widgets.selectors['theme'].js_on_change("value", callback)
from collections import defaultdict

from bokeh.models import ColumnDataSource, Select, Slider, Button

from bokeh.plotting import figure

from bokeh.models import Tabs, TabPanel

from dataclasses import dataclass, field

from bokeh.layouts import column, row

from bokeh.models import CustomJS

from bokeh.io import curdoc


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

import colorcet as cc

dark_palettes = {
    'sec_type': ['#E69F00', '#F0E442', '#019E73', '#0072B2'],
    'trace': ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'continuous': cc.glasbey_dark,
}

light_palettes = {
    'sec_type': ['orange', 'gold', '#32b499', '#1e90ff'],
    'trace': ["#fd7f6f", "#7eb0d5", "#b2e061", "#bd7ebe", "#ffb55a", "#ffee65", "#beb9db", "#fdcce5", "#8bd3c7"],
    'continuous': cc.glasbey_light,
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

THEMES = {
    'dark_minimal': Theme('dark_minimal', '#f064ae', 'white', 'black', '#20262B', 'white', dark_palettes),
    # 'light_minimal': Theme('contrast', 'black', 'black', 'white', '#D8D2D0', light_palettes),
    'light_minimal': Theme('contrast', '#f064ae', 'black', 'white', 'white', 'black', light_palettes),
}


PARAMS = {
    'morph': {'type': 'Section type',
              'diam': 'Diameter (μm)',
              'area': 'Area (μm²)',
              'dist': 'Distance from soma (μm)', 
              'Ra': 'Axial resistance (Ωcm)',
              },
    'ephys': {'cm': 'Capacitance (μF/cm²)'},
    'sim': {'iclamps': 'Injected current (nA)',
            'AMPA': 'Number of synapses',
            'NMDA': 'Number of synapses',
            'AMPA_NMDA': 'Number of synapses',
            'GABAa': 'Number of synapses',
            'recordings': 'Recordings',
            'voltage': 'Voltage',}
}



class CellView():
    
    def __init__(self):
        self.theme = THEMES['dark_minimal']
        self.figures = {}
        self.sources = {}
        self.renderers = {}
        self.widgets = WidgetManager()
        self.DOM_elements = {}
        self._params = PARAMS
        self._add_theme_callbacks()
        self._file_content = None
        self._filename = None

    @property
    def params(self):
        """Return as flattend dict"""
        return {k: v for d in self._params.values() for k, v in d.items()}

    @property
    def ephys_params(self):
        return self._params['ephys']

    def update_ephys_params(self, new_ephys_params):
        #self._params['ephys'].update(new_ephys_params)
        self._params['ephys'] = {**{'cm': 'Capacitance (μF/cm²)'}, **new_ephys_params}


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
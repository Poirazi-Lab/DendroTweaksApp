
from bokeh.models import ColumnDataSource
from bokeh.models import MultiLine, Select, Slider, WheelZoomTool, CustomJS

from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.transform import CategoricalColorMapper
from bokeh.models import Tabs, TabPanel
from bokeh.models import Div
from bokeh.models import Button
from bokeh.events import ButtonClick
from bokeh.models import HoverTool
from bokeh.models import Spinner
from bokeh.models import ColorBar
from bokeh.transform import linear_cmap
from bokeh.palettes import Viridis256
from bokeh.models import LinearColorMapper
from bokeh.models import Switch
from bokeh.models import Span
import colorcet as cc

class WorkspaceMixin():


    def __init__(self):
        super().__init__()

    # ==========================================================================
    # Cell Panel
    # ==========================================================================

    def _create_cell_figure(self):

        self.figures['cell'] = figure(
            title='Cell',
            width=400,
            height=460,
            match_aspect=True,
            tools='pan, box_zoom,reset, tap, wheel_zoom, save'
        )
        # self.figures['cell'].toolbar.active_scroll = self.figures['cell'].select_one(WheelZoomTool)
        self.sources['cell'] = ColumnDataSource(data={'xs': [], 'ys': [], 'line_color': [], 'line_width': [], 'label': [], 'line_alpha': []})
        self.sources['soma'] = ColumnDataSource(data={'x': [], 'y': [], 'rad': [], 'color': []})
        color_mapper = CategoricalColorMapper(palette=['#E69F00', '#F0E442', '#019E73', '#0072B2'], factors=['soma', 'axon', 'dend', 'apic'])
        glyph = MultiLine(
            xs='xs', 
            ys='ys', 
            line_color='line_color', 
            line_width='line_width', 
            line_alpha=1
        )
        self.figures['cell'].add_glyph(self.sources['cell'], glyph)

        # change nonselection glyph alpha
        self.figures['cell'].renderers[0].selection_glyph = MultiLine(line_alpha=0.8, line_width='line_width', line_color='line_color')
        self.figures['cell'].renderers[0].nonselection_glyph = MultiLine(line_alpha=0.3, line_width='line_width', line_color='line_color')

        self.figures['cell'].circle(x='x', y='y', radius='rad', color='color', source=self.sources['soma'], alpha=0.9)


    def _create_rotate_cell_slider(self):

        self.widgets.sliders['rotate_cell'] = Slider(
            start=0, 
            end=360, 
            value=1, 
            step=2, 
            title="Rotate", 
            width=370, 
        )
        self.widgets.sliders['rotate_cell'].on_change('value', self.p.rotate_cell_renderer_callback)

    ## Selectors
    def _create_section_selector(self):
        self.widgets.selectors['section'] = Select(
            options=[], 
            title='Section',
        ) 
        self.widgets.selectors['section'].on_change('value', self.p.select_section_callback)

    def _create_seg_x_selector(self):
        self.widgets.selectors['seg_x'] = Select(
            options=[], 
            title='Segment',
        )
        self.widgets.selectors['seg_x'].on_change('value', self.p.select_seg_x_callback)


    def _create_navigation_panel(self):
        
        self.widgets.buttons['child'] = Button(label='Child')
        self.widgets.buttons['child'].on_event(ButtonClick, self.p.button_child_callback)

        self.widgets.buttons['parent'] = Button(label='Parent', disabled=True)
        self.widgets.buttons['parent'].on_event(ButtonClick, self.p.button_parent_callback)

        self.widgets.buttons['sibling'] = Button(label='Sibling', disabled=True)
        self.widgets.buttons['sibling'].on_event(ButtonClick, self.p.button_sibling_callback)

        return row(
            [
                self.widgets.selectors['section'],
                self.widgets.selectors['seg_x'],
                row(
                    [
                        self.widgets.buttons['parent'], 
                        self.widgets.buttons['sibling'], 
                        self.widgets.buttons['child']
                    ],
                    styles={'padding-top': '20px'},
                )
            ],
            max_width=300,
            flow_mode='inline',
        )


    def create_cell_panel(self):

        self._create_cell_figure()
        self._create_rotate_cell_slider()
        self._create_section_selector()
        self._create_seg_x_selector()
        navigation = self._create_navigation_panel()

        panel_cell = column(
            [
                self.figures['cell'], 
                row(
                    self.widgets.sliders['rotate_cell'],
                    styles={'margin-right': '25px'}
                ),
                navigation
            ],
            name='panel_cell',
            styles={'padding-bottom': '20px'}
        )

        panel_cell.background = None

        return panel_cell

    # ============================================================================
    # Graph Panel
    # ============================================================================

    def _create_graph_figure(self):
        self.figures['graph'] = figure(title='Graph', 
                            width=700, 
                            height=460, 
                            tools='pan, box_zoom,reset, lasso_select, tap, wheel_zoom, save',  
                            match_aspect=True)

        # self.figures['graph'].toolbar.active_scroll = self.figures['graph'].select_one(WheelZoomTool)

        # Add hover tool to show all the node labels
        graph_hover_callback = CustomJS(args=dict(plot=self.figures['graph']), code="""
            // get the canvas element
            var canvas = plot.canvas_view.el;
            // change the cursor
            canvas.style.cursor = 'pointer';
        """)

        hover = HoverTool(callback=graph_hover_callback, tooltips=[("ID", "@index"), 
                                                                ("Sec ID", "@sec"),
                                                                ("x", "@x"),
                                                                ("Domain", "@domain"), 
                                                                ("Area", "@area"), 
                                                                ("Diam", "@diam"), 
                                                                ("Sec diam", "@section_diam"),
                                                                ("Distance", "@distance"), 
                                                                ("Domain dist", "@domain_distance"),
                                                                ("Length", "@length"),
                                                                ("cm", "@cm"),
                                                                ("Ra", "@Ra"), 
                                                                #    ('g na', '@gbar_na{0.000000}'), 
                                                                #    ('g kv', '@gbar_kv{0.000000}'), 
                                                                ("Recordings", "@rec_v"), 
                                                                ("AMPA", "@AMPA"), 
                                                                ("Weights", "@weights"), 
                                                                ("Iclamps", "@iclamps"), 
                                                                ("voltage", "@voltage"), 
                                                                ("cai", "@cai")])
        self.figures['graph'].add_tools(hover)

    # Add select widget                                                        

    def _create_graph_param_selector(self):

        self.widgets.selectors['graph_param'] = Select(
            title="Parameter:", 
            width=150,
            options = {**self.params},
            value='domain'
        )
        self.widgets.selectors['graph_param'].on_change('value', self.p.select_graph_param_callback)

        self.widgets.sliders['graph_param_high'] = Slider(
            start=0, 
            end=1,
            value=1,
            step=0.01,
            title="Colormap max",
            width=100,
            visible=True,
            format="0.00000",
            show_value=False
        )
        self.widgets.sliders['graph_param_high'].on_change('value_throttled', self.p.colormap_max_callback)

    def _create_time_slice_spinner(self):
        self.widgets.sliders['time_slice'] = Spinner(title="Time slice", low=0, high=1000, step=0.1, value=100, width=100, visible=False)
        self.widgets.sliders['time_slice'].on_change('value_throttled', self.p.update_time_slice_callback)

    
    def _create_update_graph_button(self):

        self.widgets.buttons['update_graph'] = Button(
            label='Update', 
            button_type='default',
            width=100,
            styles={'padding-top': '20px', 'padding-left': '10px'}
        )
        self.widgets.buttons['update_graph'].on_event(ButtonClick, self.p.update_graph_callback)

    def create_graph_panel(self):
        """
        Create the graph panel.
        """

        self._create_graph_figure()
        self._create_graph_param_selector()
        self._create_time_slice_spinner()
        self._create_update_graph_button()

        # Add the graph to the panel
        graph_layout = column(
            [
                self.figures['graph'], 
                row(
                    [
                        self.widgets.selectors['graph_param'], 
                        self.widgets.sliders['graph_param_high'],
                        self.widgets.sliders['time_slice'],
                        self.widgets.buttons['update_graph']
                    ]
                ),
            ],
            name='panel_graph',
        )

        return graph_layout

    # ============================================================================
    # Simulation Panel
    # ============================================================================


    def _create_voltage_figure(self):
        
        self.figures['sim'] = figure(
            width=1100, 
            height=250, 
            x_axis_label='Time (ms)',
            y_axis_label='Voltage (mV)',
            y_range=(-100, 50),
            tools="pan, xwheel_zoom, reset, save, ywheel_zoom, box_zoom, tap",
            output_backend="webgl"
        )

        self.figures['sim'].grid.grid_line_alpha = 0.1

        self.sources['sim'] = ColumnDataSource(data={'xs': [], 'ys': []})

        color_mapper = LinearColorMapper(palette=cc.rainbow4, low=0)  #rainbow4

        self.figures['sim'].multi_line(
            xs='xs', 
            ys='ys', 
            source=self.sources['sim'],
            line_width=2, 
            line_alpha=0.9,
        )
        self.figures['sim'].renderers[0].selection_glyph = MultiLine(line_width=2, line_alpha=1)
        self.figures['sim'].renderers[0].nonselection_glyph = MultiLine(line_width=2, line_alpha=0.3)

        from bokeh.models import Span
        self.renderers['span_v'] = Span(location=100, dimension='height', line_color='red', line_width=1, name='v_span')
        self.figures['sim'].add_layout(self.renderers['span_v'])
        # self.sources['span_v'] = ColumnDataSource(data={'x': [100, 100], 'y': [-90, 90]})
        # self.figures['sim'].line(x='x', y='y', color='red', source=self.sources['span_v'])


        self.sources['frozen_v'] = ColumnDataSource(data={'xs': [], 'ys': [], 'line_color': []})

        self.figures['sim'].multi_line(
            xs='xs', 
            ys='ys',
            source=self.sources['frozen_v'],
            line_width=1,
            line_color='line_color',
            line_alpha=0.5
        )

        hover_callback = CustomJS(args=dict(plot=self.figures['cell']), 
            code="""
                    // get the canvas element
                    var canvas = plot.canvas_self.el;
                    // change the cursor
                    canvas.style.cursor = 'pointer';
                """)

        sim_hover_tool = HoverTool(callback=hover_callback, renderers=[self.figures['sim'].renderers[0]], tooltips=[('Seg', '@labels')])
        self.figures['sim'].add_tools(sim_hover_tool)

    def _create_frozen_v_switch(self):
        
        self.widgets.switches['frozen_v'] = Switch(active=False)

        def frozen_v_callback(attr, old, new):
            if new:
                data = dict(self.sources['sim'].data)
                data.update({'line_color': [self.theme.frozen]})
                self.sources['frozen_v'].data = data
                
            else:
                self.sources['frozen_v'].data = {'xs': [], 'ys': []}

        self.widgets.switches['frozen_v'].on_change('active', frozen_v_callback)

        self.sources['detected_spikes'] = ColumnDataSource(data={'x': [], 'y': []})
        self.figures['sim'].circle(x='x', y='y', color='magenta', source=self.sources['detected_spikes'])


    def _create_current_figure(self):

        self.figures['curr'] = figure(width=1100, height=250,
                                    x_axis_label='Time (ms)',
                                    y_axis_label='Current (nA)',
                                    tools='pan, box_zoom, reset, save, tap')

        self.figures['curr'].grid.grid_line_alpha = 0.1

        self.sources['curr'] = ColumnDataSource(data={'xs': [], 'ys': []})

        self.figures['curr'].multi_line(xs='xs', ys='ys', 
            source=self.sources['curr'], line_width=2,
            name='multiline_curr',
            line_alpha=0.9
            )
        self.figures['curr'].renderers[0].selection_glyph = MultiLine(line_width=2, line_alpha=1)
        self.figures['curr'].renderers[0].nonselection_glyph = MultiLine(line_width=2, line_alpha=0.3)

        self.sources['frozen_I'] = ColumnDataSource(data={'xs': [], 'ys': [], 'line_color': []})

        self.figures['curr'].multi_line(xs='xs', ys='ys',
                                        source=self.sources['frozen_I'],
                                        line_width=1,
                                        line_alpha=0.5,
                                        name='multiline_curr_frozen')

        curr_hover_tool = HoverTool(renderers=[self.figures['curr'].renderers[0]], tooltips=[('Seg', '@labels'), ('Current', '@names')])
        self.figures['curr'].add_tools(curr_hover_tool)

    def _create_frozen_i_switch(self):

        self.widgets.switches['frozen_I'] = Switch(active=False)

        def frozen_I_callback(attr, old, new):
            if new:
                data = dict(self.sources['curr'].data)
                data.update({'line_color': [self.theme.frozen]})
                self.sources['frozen_I'].data = data
            else:
                self.sources['frozen_I'].data = {'xs': [], 'ys': []}

        self.widgets.switches['frozen_I'].on_change('active', frozen_I_callback)

        self.figures['curr'].add_layout(self.renderers['span_v'])


    def _create_spike_times_figure(self):

        from bokeh.models import FactorRange

        self.figures['spikes'] = figure(height=250, 
                        width=1100,
                        x_axis_label='Time (ms)',
                        x_range=(0, 300),
                        y_axis_label='Synapses',
                        y_range=FactorRange(factors=[]),
                        tools="pan, box_zoom, reset, save")

        self.figures['spikes'].toolbar.logo = None
        self.figures['spikes'].grid.grid_line_alpha = 0.1
        self.figures['spikes'].ygrid.visible = False

        self.sources['spikes'] = ColumnDataSource(data={'x': [], 'y': [], 'color': []})


        self.figures['spikes'].circle(x='x', y='y', color='color', source=self.sources['spikes'])


        # self.renderers['span_t'] = Span(location=100, dimension='height', line_color='red', line_width=1)
        self.figures['spikes'].add_layout(self.renderers['span_v'])

        self.figures['sim'].x_range = self.figures['spikes'].x_range = self.figures['curr'].x_range


    def _create_voltage_tab_panel(self):

        self._create_voltage_figure()
        self._create_frozen_v_switch()

        voltage_layout = column(
            [
                self.figures['sim'], 
                row([self.widgets.switches['frozen_v'], Div(text='Freeze traces')])
            ],
            width=1100,
            height=250,
        )

        self.widgets.tab_panels['voltage'] = TabPanel(
            child=voltage_layout, 
            title='Voltage'
        )


    def _create_current_tab_panel(self):

        self._create_current_figure()
        self._create_frozen_i_switch()

        current_layout = column(
            [
                self.figures['curr'],
                row([self.widgets.switches['frozen_I'],Div(text='Freeze traces')])
            ],
            width=1100,
            height=250,
        )

        self.widgets.tab_panels['current'] = TabPanel(
            child=current_layout, 
            title='Current'
        )


    def _create_spike_times_tab_panel(self):
        
        self._create_spike_times_figure()

        spike_times_layout = column(
            self.figures['spikes'], 
            width=1100, 
            height=250, 
        )

        self.widgets.tab_panels['spike_times'] = TabPanel(
            child=spike_times_layout, 
            title='Spike times'
        )


    def _create_simulation_tabs(self):

        self._create_voltage_tab_panel()
        self._create_current_tab_panel()
        self._create_spike_times_tab_panel()

        self.widgets.tabs['simulation'] = Tabs(
            tabs=[
                self.widgets.tab_panels['voltage'],
                self.widgets.tab_panels['current'],
                self.widgets.tab_panels['spike_times']
            ], 
            width=1100, 
            height=250,
        )

    def create_simulation_panel(self):

        self._create_simulation_tabs()

        return row(
            [
                self.widgets.tabs['simulation'], 
            ],
            name='panel_simulation'
        )


    def create_workspace(self):

        """
        Create the workspace layout.
        """
        cell_panel = self.create_cell_panel()
        section_panel = self.create_section_panel()
        graph_panel = self.create_graph_panel()
        simulation_panel = self.create_simulation_panel()

        workspace = column(
            [
                row(
                    cell_panel, 
                    graph_panel
                ),
                simulation_panel
            ],
            name='workspace',
            visible=False,
            styles={'padding': '10px'},
            width=1120,
            height=940,
        )

        return workspace
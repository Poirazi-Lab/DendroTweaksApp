
from bokeh.models import ColumnDataSource, Button, CustomJS, HoverTool, Patches
from bokeh.layouts import column, row
from bokeh.events import ButtonClick
from bokeh.plotting import figure

class AuxiliaryMixin():

    def __init__(self):
        super().__init__()

    # ==================================================================
    # Kinetics panel
    # ==================================================================
    
    def create_kinetics_panel(self):

        self.figures['inf'] = figure(width=300, height=300, title='Steady state',
                                x_axis_label='Voltage (mV)', y_axis_label='Inf, (1)',
                                visible=False)

        self.sources['inf_orig'] = ColumnDataSource(data={'xs': [], 'ys': [], })
        self.figures['inf'].multi_line(xs='xs',
                                    ys='ys',
                                    source=self.sources['inf_orig'],
                                    line_width=2,
                                    color='color')

        self.sources['inf_fit'] = ColumnDataSource(data={'xs': [], 'ys': [], })
        self.figures['inf'].multi_line(xs='xs',
                                    ys='ys',
                                    source=self.sources['inf_fit'],
                                    line_width=2,
                                    line_dash='dashed',
                                    color='color')

        from bokeh.models import LogScale
        self.figures['inf_log'] = figure(width=300, height=300, title='Steady state',
                                x_axis_label='Voltage (mV)', y_axis_label='Inf, (1)',
                                visible=False, x_axis_type='log')

        self.figures['inf_log'].multi_line(xs='xs',
                                        ys='ys',
                                        source=self.sources['inf_orig'],
                                        line_width=2,
                                        color='color')

        self.figures['tau'] = figure(width=300, height=300, title='Time constant',
                                x_axis_label='Voltage (mV)', y_axis_label='Tau, ms',
                                visible=False)

        self.sources['tau_orig'] = ColumnDataSource(data={'xs': [], 'ys': []})
        self.figures['tau'].multi_line(xs='xs',
                                    ys='ys',
                                    source=self.sources['tau_orig'],
                                    line_width=2,
                                    color='color')

        self.figures['tau_log'] = figure(width=300, height=300, title='Time constant',
                                x_axis_label='Voltage (mV)', y_axis_label='Tau, ms',
                                visible=False, x_axis_type='log')

        self.figures['tau_log'].multi_line(xs='xs',
                                        ys='ys',
                                        source=self.sources['tau_orig'],
                                        line_width=2,
                                        color='color')                        

        self.sources['tau_fit'] = ColumnDataSource(data={'xs': [], 'ys': []})
        self.figures['tau'].multi_line(xs='xs',
                                    ys='ys',
                                    source=self.sources['tau_fit'],
                                    line_width=2,
                                    line_dash='dashed',
                                    color='color')

    # ==================================================================
    # Section panel
    # ==================================================================

    def _create_section_diam_figure(self):
        ### Section diameters
        self.figures['section_diam'] = figure(title='Section diameters', x_axis_label='Length, μm',
                                            y_axis_label='Diameter, μm', 
                                            sizing_mode='fixed',
                                            width=350,
                                            height=200,
                                            tools='pan, box_zoom, reset, wheel_zoom, save')

        self.sources['section_diam'] = ColumnDataSource(data={'xs': [], 'ys': [], 'fill_color': []})

        glyph_diams = Patches(xs='xs', ys='ys', fill_color='#CC79A7', fill_alpha=0.5, line_alpha=0)
        self.figures['section_diam'].add_glyph(self.sources['section_diam'], glyph_diams)

        self.sources['section_nseg'] = ColumnDataSource(data={'x': [], 'y': [], 'marker': []})
        self.figures['section_diam'].scatter(y='y', x='x', marker='marker', source=self.sources['section_nseg'], size=10, color='white')


    ### Section parameters
    def _create_section_param_figure(self):

        self.figures['section_param'] = figure(title='Section', x_axis_label='Length, μm',
                                            y_axis_label='Param', 
                                            sizing_mode='fixed',
                                            width=350,                                     
                                            height=200,
                                            tools='pan, box_zoom, reset, wheel_zoom, save')

        self.sources['section_param'] = ColumnDataSource(data={'x': [], 'y': [], 'width': []})
        self.figures['section_param'].vbar(x='x', 
                                                                            top='y', 
                                                                            width='width', 
                                                                            source=self.sources['section_param'], 
                                                                            color='#CC79A7', 
                                                                            line_color='black', 
                                                                            fill_alpha=0.5)

        self.figures['section_param'].scatter(y='y', x='x', marker='marker', source=self.sources['section_nseg'], size=10, color='white')


    def _create_section_param_hist_figure(self):

        self.figures['section_param_hist'] = figure(title='Section', x_axis_label='Param', 
                                                    y_axis_label='Count', width=270, height=241,
                                                    # x_range=[0, 150],
                                                    # y_range=[0, 70],
                                                    tools='pan, box_zoom, reset, wheel_zoom, save',
                                                    visible=True)

        self.sources['section_param_hist'] = ColumnDataSource(data={'top':[], 'left':[], 'right':[]})
                                                            
        self.figures['section_param_hist'].quad(top='top', bottom=0, left='left', right='right', source=self.sources['section_param_hist'], color='#CC79A7', line_color='black', fill_alpha=0.5)


        self.figures['cell'].renderers[0].data_source.selected.on_change('indices', self.p.cell_tap_callback)


        hover_callback = CustomJS(args=dict(plot=self.figures['cell']), 
                                code="""
                                        // get the canvas element
                                        var canvas = plot.canvas_self.el;
                                        // change the cursor
                                        canvas.style.cursor = 'pointer';
                                    """)

        cell_hover_tool = HoverTool(callback=hover_callback, renderers=[self.figures['cell'].renderers[0]], tooltips=[('Sec', '@label')])
        self.figures['cell'].add_tools(cell_hover_tool)


    def _create_navigation_panel(self):
        
        self.widgets.buttons['child'] = Button(label='Child')
        self.widgets.buttons['child'].on_event(ButtonClick, self.p.button_child_callback)

        self.widgets.buttons['parent'] = Button(label='Parent', disabled=True)
        self.widgets.buttons['parent'].on_event(ButtonClick, self.p.button_parent_callback)

        self.widgets.buttons['sibling'] = Button(label='Sibling', disabled=True)
        self.widgets.buttons['sibling'].on_event(ButtonClick, self.p.button_sibling_callback)

        return column(
            [
                row(
                    [
                        self.widgets.selectors['section'],
                        self.widgets.selectors['seg_x']
                    ]
                ),
                row(
                    [
                        self.widgets.buttons['parent'], 
                        self.widgets.buttons['sibling'], 
                        self.widgets.buttons['child']
                    ]
                )
            ]
        )

    def create_section_panel(self):

        self._create_section_diam_figure()
        self._create_section_param_figure()
        self._create_section_param_hist_figure()
        navigation = self._create_navigation_panel()

        return column(
            [
                self.figures['section_diam'], 
                self.figures['section_param'], 
                navigation
            ], 
            name='panel_section',
            width=270, 
            height=350,
            sizing_mode='fixed'
        )
                                    
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


from view import CellView
view = CellView()

PATH_TO_DATA = 'app/static/data/'

import dendrotweaks as dd

model = dd.Model(PATH_TO_DATA + '/Test')
print(model.list_morphologies())

from presenter.presenter import Presenter
p = Presenter(path_to_data=PATH_TO_DATA, view=view, model=model)

AVAILABLE_DOMAINS = [
    'soma', 'perisomatic', 
    'axon', 
    'dend', 'basal', 
    'apic', 'trunk', 'tuft', 'oblique', 
    'custom_0', 'custom_1', 'custom_2', 'custom_3'
]

view.DOM_elements['status'] = Div(text='Select a model to start', width=242, styles={"color":"gold"})

def add_message(widget, message, callback_type='on_change'):
    callback = CustomJS(args=dict(status=view.DOM_elements['status']), 
                        code=f"status.text = '{message}';")
    if callback_type == 'on_change':
        widget.js_on_change('value', callback)
    elif callback_type == 'on_click':
        widget.js_on_click(callback)
# =================================================================
# FIGURES
# =================================================================

# -----------------------------------------------------------------
# CELL FIGURE
# -----------------------------------------------------------------

view.figures['cell'] = figure(title='Cell',
       width=400,
       height=500,
       match_aspect=True,
       tools='pan, box_zoom,reset, tap, wheel_zoom, save')

view.figures['cell'].toolbar.active_scroll = view.figures['cell'].select_one(WheelZoomTool)

view.sources['cell'] = ColumnDataSource(data={'xs': [], 'ys': [], 'color': [], 'line_width': [], 'label': [], 'line_alpha': []})
view.sources['soma'] = ColumnDataSource(data={'x': [], 'y': [], 'rad': [], 'color': ['red']})

color_mapper = CategoricalColorMapper(palette=['#E69F00', '#F0E442', '#019E73', '#0072B2'], factors=['soma', 'axon', 'dend', 'apic'])
glyph = MultiLine(xs='xs', ys='ys', line_color='color', line_width='line_width', line_alpha=1)

# glyph = MultiLine(xs='xs', ys='ys', line_color='color', line_width='line_width')
view.figures['cell'].add_glyph(view.sources['cell'], glyph)

# change nonselection glyph alpha
view.figures['cell'].renderers[0].selection_glyph = MultiLine(line_alpha=0.8, line_width='line_width', line_color='color')
view.figures['cell'].renderers[0].nonselection_glyph = MultiLine(line_alpha=0.3, line_width='line_width', line_color='color')

view.figures['cell'].circle(x='x', y='y', radius='rad', color='color', source=view.sources['soma'], alpha=0.9)
view.widgets.sliders['rotate_cell'] = Slider(start=0, end=360, value=1, step=2, title="Rotate", width=370)

view.widgets.sliders['rotate_cell'].on_change('value', p.rotate_cell_renderer_callback)

panel_cell = column(view.figures['cell'], view.widgets.sliders['rotate_cell'], name='panel_cell')
panel_cell.background = None
curdoc().add_root(panel_cell)



# -----------------------------------------------------------------
# SECTION FIGURE
# -----------------------------------------------------------------


### Section diameters
view.figures['section_diam'] = figure(title='Section diameters', x_axis_label='Length, μm',
                                     y_axis_label='Diameter, μm', width=270, height=241, 
                                     sizing_mode='fixed',
                                     tools='pan, box_zoom, reset, wheel_zoom, save')

view.sources['section_diam'] = ColumnDataSource(data={'xs': [], 'ys': [], 'fill_color': []})

glyph_diams = Patches(xs='xs', ys='ys', fill_color='#CC79A7', fill_alpha=0.5, line_alpha=0)
view.figures['section_diam'].add_glyph(view.sources['section_diam'], glyph_diams)

view.sources['section_nseg'] = ColumnDataSource(data={'x': [], 'y': [], 'marker': []})
view.figures['section_diam'].scatter(y='y', x='x', marker='marker', source=view.sources['section_nseg'], size=10, color='white')


### Section parameters
view.figures['section_param'] = figure(title='Section', x_axis_label='Length, μm',
                                      y_axis_label='Param', width=270, height=241, 
                                      sizing_mode='fixed',                                     
                                      tools='pan, box_zoom, reset, wheel_zoom, save')

view.sources['section_param'] = ColumnDataSource(data={'x': [], 'y': [], 'width': []})
view.figures['section_param'].vbar(x='x', 
                                                                    top='y', 
                                                                    width='width', 
                                                                    source=view.sources['section_param'], 
                                                                    color='#CC79A7', 
                                                                    line_color='black', 
                                                                    fill_alpha=0.5)

view.figures['section_param'].scatter(y='y', x='x', marker='marker', source=view.sources['section_nseg'], size=10, color='white')

view.figures['section_param_hist'] = figure(title='Section', x_axis_label='Param', 
                                            y_axis_label='Count', width=270, height=241,
                                            # x_range=[0, 150],
                                            # y_range=[0, 70],
                                            tools='pan, box_zoom, reset, wheel_zoom, save',
                                            visible=True)

view.sources['section_param_hist'] = ColumnDataSource(data={'top':[], 'left':[], 'right':[]})
                                                     
view.figures['section_param_hist'].quad(top='top', bottom=0, left='left', right='right', source=view.sources['section_param_hist'], color='#CC79A7', line_color='black', fill_alpha=0.5)

## Selectors
view.widgets.selectors['section'] = Select(options=[], title='Section')
view.widgets.selectors['section'].on_change('value', p.select_section_callback)

view.widgets.selectors['seg_x'] = Select(options=[], title='Segment')




view.figures['cell'].renderers[0].data_source.selected.on_change('indices', p.cell_tap_callback)


hover_callback = CustomJS(args=dict(plot=view.figures['cell']), 
                        code="""
                                // get the canvas element
                                var canvas = plot.canvas_view.el;
                                // change the cursor
                                canvas.style.cursor = 'pointer';
                            """)

cell_hover_tool = HoverTool(callback=hover_callback, renderers=[view.figures['cell'].renderers[0]], tooltips=[('Sec', '@label')])
view.figures['cell'].add_tools(cell_hover_tool)


## Buttons
view.widgets.buttons['child'] = Button(label='Child')
view.widgets.buttons['child'].on_event(ButtonClick, p.button_child_callback)

view.widgets.buttons['parent'] = Button(label='Parent', disabled=True)
view.widgets.buttons['parent'].on_event(ButtonClick, p.button_parent_callback)

view.widgets.buttons['sibling'] = Button(label='Sibling', disabled=True)
view.widgets.buttons['sibling'].on_event(ButtonClick, p.button_sibling_callback)

widgets_navigation =    column([
                        row([view.widgets.selectors['section'],
                            view.widgets.selectors['seg_x'],
                        ]),
                        row([
                          view.widgets.buttons['parent'], 
                          view.widgets.buttons['sibling'], 
                          view.widgets.buttons['child']]
                        )
                        ])


view.DOM_elements['section_plots'] = column(
    view.figures['section_diam'], 
    view.figures['section_param'], 
    widgets_navigation, name='panel_section',
    width=270, height=350,
    sizing_mode='fixed'
)









# -----------------------------------------------------------------
# GRAPH FIGURE
# -----------------------------------------------------------------


view.figures['graph'] = figure(title='Graph', 
                      width=700, 
                      height=500, 
                      tools='pan, box_zoom,reset, lasso_select, tap, wheel_zoom, save',  
                      match_aspect=True,
                      width_policy='fit',
                      sizing_mode='scale_both',)

view.figures['graph'].toolbar.active_scroll = view.figures['graph'].select_one(WheelZoomTool)

# Add hover tool to show all the node labels
graph_hover_callback = CustomJS(args=dict(plot=view.figures['graph']), code="""
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
                                                           ("Recordings", "@recordings"), 
                                                           ("AMPA", "@AMPA"), 
                                                           ("Weights", "@weights"), 
                                                           ("Iclamps", "@iclamps"), 
                                                        #    ("line_color", "@line_color"), 
                                                           ("voltage", "@voltage"), 
                                                           ("cai", "@cai")])
view.figures['graph'].add_tools(hover)

# Add select widget                                                        

view.widgets.selectors['graph_param'] = Select(title="Parameter:", 
                                              width=150,
                                              options = {**view.params},
                                              value='domain'
                                              )

view.widgets.sliders['graph_param_high'] = Slider(start=0, end=1, value=1, 
                                                 step=0.01, title="Colormap max", width=100, visible=True, format="0.00000", show_value=False)
view.widgets.sliders['time_slice'] = Spinner(title="Time slice", low=0, high=1000, step=0.1, value=100, width=100, visible=False)

view.widgets.sliders['time_slice'].on_change('value_throttled', p.update_time_slice_callback)

# Attach the callback to the dropdown selector
view.widgets.selectors['graph_param'].on_change('value', p.select_graph_param_callback)




view.widgets.sliders['graph_param_high'].on_change('value_throttled', p.colormap_max_callback)

view.widgets.buttons['update_graph'] = Button(label='Update', button_type='primary', width=100)

view.widgets.buttons['update_graph'].on_event(ButtonClick, p.update_graph_callback)

panel_graph = column(view.figures['graph'], 
                    row(
                        [view.widgets.selectors['graph_param'], 
                         view.widgets.sliders['graph_param_high'],
                        view.widgets.sliders['time_slice'],
                        view.widgets.buttons['update_graph']
                        ]
                         ), 
                    name='panel_graph',
                    width_policy='fit',
                    sizing_mode='scale_width',)

panel_graph = row(view.DOM_elements['section_plots'], panel_graph, name='panel_graph', width=800, height=560)

curdoc().add_root(panel_graph)










# -----------------------------------------------------------------
# SIMULATION FIGURE
# -----------------------------------------------------------------


view.figures['sim'] = figure(width=600, height=300, 
               width_policy='fit',
                sizing_mode='scale_width',
               x_axis_label='Time (ms)',
               y_axis_label='Voltage (mV)',
               y_range=(-100, 50),
               tools="pan, xwheel_zoom, reset, save, ywheel_zoom, box_zoom, tap",
               output_backend="webgl")

view.figures['sim'].grid.grid_line_alpha = 0.1

view.sources['sim'] = ColumnDataSource(data={'xs': [], 'ys': [], 'dist': []})

color_mapper = LinearColorMapper(palette=cc.rainbow4, low=0)  #rainbow4

view.figures['sim'].multi_line(xs='xs', ys='ys', 
                              source=view.sources['sim'],
                              line_width=2, 
                              color={'field': 'dist', 'transform': color_mapper})
view.figures['sim'].renderers[0].nonselection_glyph.line_alpha = 0.3

from bokeh.models import Span
view.renderers['span_v'] = Span(location=100, dimension='height', line_color='red', line_width=1)
view.figures['sim'].add_layout(view.renderers['span_v'])
# view.sources['span_v'] = ColumnDataSource(data={'x': [100, 100], 'y': [-90, 90]})
# view.figures['sim'].line(x='x', y='y', color='red', source=view.sources['span_v'])


view.sources['frozen_v'] = ColumnDataSource(data={'xs': [], 'ys': [], 'color': []})

view.figures['sim'].multi_line(xs='xs', ys='ys',
                                source=view.sources['frozen_v'],
                                line_width=1,
                                color='color',
                                line_alpha=0.5)

view.widgets.switches['frozen_v'] = Switch(active=False)

def frozen_v_callback(attr, old, new):
    if new:
        data = dict(view.sources['sim'].data)
        data.update({'color': [view.theme.frozen]})
        view.sources['frozen_v'].data = data
        
    else:
        view.sources['frozen_v'].data = {'xs': [], 'ys': []}

view.widgets.switches['frozen_v'].on_change('active', frozen_v_callback)

hover_callback = CustomJS(args=dict(plot=view.figures['cell']), 
                        code="""
                                // get the canvas element
                                var canvas = plot.canvas_view.el;
                                // change the cursor
                                canvas.style.cursor = 'pointer';
                            """)

sim_hover_tool = HoverTool(callback=hover_callback, renderers=[view.figures['sim'].renderers[0]], tooltips=[('Seg', '@label')])
view.figures['sim'].add_tools(sim_hover_tool)

view.sources['detected_spikes'] = ColumnDataSource(data={'x': [], 'y': []})
view.figures['sim'].circle(x='x', y='y', color='red', source=view.sources['detected_spikes'])

view.figures['curr'] = figure(width=600, height=300,
                             width_policy='fit',
                             sizing_mode='scale_width',
                             x_axis_label='Time (ms)',
                             y_axis_label='Current (nA)',
                             tools='pan, box_zoom, reset, save, tap')

view.figures['curr'].grid.grid_line_alpha = 0.1

view.sources['curr'] = ColumnDataSource(data={'xs': [], 'ys': [], 'color': []})

view.figures['curr'].multi_line(xs='xs', ys='ys', source=view.sources['curr'], line_width=2, color='red')

view.sources['frozen_I'] = ColumnDataSource(data={'xs': [], 'ys': []})

view.figures['curr'].multi_line(xs='xs', ys='ys',
                                source=view.sources['frozen_I'],
                                line_width=1,
                                color='color',
                                line_alpha=0.5)

view.widgets.switches['frozen_I'] = Switch(active=False)

def frozen_I_callback(attr, old, new):
    if new:
        data = dict(view.sources['curr'].data)
        data.update({'color': [view.theme.frozen]})
        view.sources['frozen_I'].data = data
    else:
        view.sources['frozen_I'].data = {'xs': [], 'ys': []}

view.widgets.switches['frozen_I'].on_change('active', frozen_I_callback)

view.figures['curr'].add_layout(view.renderers['span_v'])


from bokeh.models import FactorRange

view.figures['spikes'] = figure(height=300, 
                width_policy='fit',
                sizing_mode='scale_width',
                x_axis_label='Time (ms)',
                x_range=(0, 300),
                y_axis_label='Synapses',
                y_range=FactorRange(factors=[]),
                tools="pan, box_zoom, reset, save")

view.figures['spikes'].toolbar.logo = None
view.figures['spikes'].grid.grid_line_alpha = 0.1
view.figures['spikes'].ygrid.visible = False

view.sources['spikes'] = ColumnDataSource(data={'x': [], 'y': [], 'color': []})


view.figures['spikes'].circle(x='x', y='y', color='color', source=view.sources['spikes'])


# view.renderers['span_t'] = Span(location=100, dimension='height', line_color='red', line_width=1)
view.figures['spikes'].add_layout(view.renderers['span_v'])

view.figures['sim'].x_range = view.figures['spikes'].x_range = view.figures['curr'].x_range


view.figures['inf'] = figure(width=300, height=300, title='Steady state',
                        x_axis_label='Voltage (mV)', y_axis_label='Inf, (1)',
                        visible=False)

view.sources['inf_orig'] = ColumnDataSource(data={'xs': [], 'ys': [], })
view.figures['inf'].multi_line(xs='xs',
                               ys='ys',
                               source=view.sources['inf_orig'],
                               line_width=2,
                               color='color')

view.sources['inf_fit'] = ColumnDataSource(data={'xs': [], 'ys': [], })
view.figures['inf'].multi_line(xs='xs',
                               ys='ys',
                               source=view.sources['inf_fit'],
                               line_width=2,
                               line_dash='dashed',
                               color='color')

from bokeh.models import LogScale
view.figures['inf_log'] = figure(width=300, height=300, title='Steady state',
                        x_axis_label='Voltage (mV)', y_axis_label='Inf, (1)',
                        visible=False, x_axis_type='log')

view.figures['inf_log'].multi_line(xs='xs',
                                   ys='ys',
                                   source=view.sources['inf_orig'],
                                   line_width=2,
                                   color='color')

view.figures['tau'] = figure(width=300, height=300, title='Time constant',
                        x_axis_label='Voltage (mV)', y_axis_label='Tau, ms',
                        visible=False)

view.sources['tau_orig'] = ColumnDataSource(data={'xs': [], 'ys': []})
view.figures['tau'].multi_line(xs='xs',
                               ys='ys',
                               source=view.sources['tau_orig'],
                               line_width=2,
                               color='color')

view.figures['tau_log'] = figure(width=300, height=300, title='Time constant',
                        x_axis_label='Voltage (mV)', y_axis_label='Tau, ms',
                        visible=False, x_axis_type='log')

view.figures['tau_log'].multi_line(xs='xs',
                                   ys='ys',
                                   source=view.sources['tau_orig'],
                                   line_width=2,
                                   color='color')                        

view.sources['tau_fit'] = ColumnDataSource(data={'xs': [], 'ys': []})
view.figures['tau'].multi_line(xs='xs',
                               ys='ys',
                               source=view.sources['tau_fit'],
                               line_width=2,
                               line_dash='dashed',
                               color='color')

view.DOM_elements['runtime'] = Div(text='')

view.widgets.buttons['run'] = Button(label='Run', button_type='primary', width=242, height=50, disabled=True)


runtime_callback = CustomJS(args=dict(runtime=view.DOM_elements['runtime']), code="""
    runtime.text = '<img src="app/static/images/loading.gif" alt="Loading..." width="20" height="20">';
""")

view.widgets.buttons['run'].js_on_click(runtime_callback)    
    
view.widgets.buttons['run'].on_event(ButtonClick, p.voltage_callback_on_click)

voltage_panel = column(view.figures['sim'], 
                       row([view.widgets.switches['frozen_v'], Div(text='Freeze traces')]),
                        width=600, height=300,
                        width_policy='fit', sizing_mode='scale_width')

current_panel = column(view.figures['curr'],
                       row([view.widgets.switches['frozen_I'], Div(text='Freeze traces')]),
                       width=600, height=300,
                       width_policy='fit', sizing_mode='scale_width')


view.widgets.tabs['simulation'] = Tabs(tabs=[TabPanel(child=voltage_panel, title='Voltage'),
                                            TabPanel(child=current_panel, title='Current'),
                                            TabPanel(child=view.figures['spikes'],title='Synaptic inputs'),
                                            ], width=600, height=300, 
                                            width_policy='fit',)



# panel_simulation = row(view.figures['sim'], view.figures['inf'], view.figures['tau'], name='panel_simulation', width=1200)
panel_simulation = row(
                       view.widgets.tabs['simulation'], 
                       view.figures['inf'], 
                       view.figures['inf_log'],
                       view.figures['tau'], 
                       view.figures['tau_log'],
                       name='panel_simulation', width=1200)


curdoc().add_root(panel_simulation)










# ****************************************************************
# RIGHT MENU
# ****************************************************************

# =================================================================
# MORPHOLOGY TAB
# =================================================================

## Domains

view.widgets.selectors['domain'] = Select(options=[],
                                            value=None,
                                            title='Select domain',
                                            width=100)

view.widgets.selectors['domain'].on_change('value', p.select_domain_segments_callback)

view.widgets.selectors['set_domain'] = Select(title='Set domain',
                                        options=AVAILABLE_DOMAINS,
                                        value='soma',
                                        width=150)

view.widgets.selectors['set_domain'].on_change('value', p.define_domain_callback)

domain_panel = column([
    view.widgets.selectors['domain'],
    view.widgets.selectors['set_domain'],
])

## Sliders
view.widgets.sliders['n_seg'] = Slider(start=1, end=21, value=1, step=2, title='nseg')

view.widgets.sliders['n_seg'].on_change('value_throttled', p.nseg_callback)

view.widgets.buttons['reduce'] = Button(label='Reduce subtree', button_type='warning')

add_message(view.widgets.buttons['reduce'], 'Reducing the subtree. Please wait...', callback_type='on_click')
view.widgets.buttons['reduce'].on_event(ButtonClick, p.reduce_subtree_callback)
view.widgets.buttons['reduce'].on_event(ButtonClick, p.voltage_callback_on_event)


view.DOM_elements['stats'] = Div(text='Stats:')

view.widgets.buttons['stats'] = Button(label='Stats', button_type='default')
view.widgets.buttons['stats'].on_event(ButtonClick, p.stats_callback)


view.figures['diam_distribution'] = figure(width=400,
                                        height=150,
                                        match_aspect=False,
                                        tools='pan, box_zoom, hover, reset, save',)

view.figures['diam_distribution'].toolbar.autohide = True
view.figures['diam_distribution'].background_fill_color = None
view.figures['diam_distribution'].border_fill_color = None
view.sources['diam_distribution'] = ColumnDataSource(data={'x': [], 'y': []})

view.figures['diam_distribution'].circle(x='x', y='y', source=view.sources['diam_distribution'], line_width=2, color='color')
view.figures['diam_distribution'].y_range.start = 0

stats_panel = column([view.widgets.buttons['stats'], 
                     view.DOM_elements['stats'],
                     view.figures['section_param_hist'],
                     view.figures['diam_distribution']
                     ],
                     name='stats_panel')

delete_button = Button(label='Delete subtree', button_type='danger')
delete_button.on_event(ButtonClick, p.delete_subtree_callback)

widgets_section_vars = column([
                        domain_panel,
                        Div(text='<hr style="width:30em; margin-top:3em">'),
                        view.widgets.sliders['n_seg'],
                        view.widgets.buttons['reduce'],
                        delete_button,
                        stats_panel,
                        ], name='widgets_section_vars')


# =================================================================
# GROUP TAB
# =================================================================


def create_add_group_panel():


    view.widgets.text['group_name'] = TextInput(value='', 
                                                title='Group name', 
                                                placeholder='New group name',
                                                width=150)

    def check_name_exists_callback(attr, old, new):
        if new in view.widgets.selectors['group'].options:
            view.widgets.buttons['add_group'].disabled = True
        else:
            view.widgets.buttons['add_group'].disabled = False

    view.widgets.text['group_name'].on_change('value_input', check_name_exists_callback)

    view.widgets.buttons['add_group'] = Button(label='Add group', 
                                               button_type='primary', 
                                               disabled=False,
                                               width=100,
                                               styles={"padding-top":"20px"}
                                               )
                                               
    view.widgets.buttons['add_group'].on_event(ButtonClick, p.add_group_callback)

    view.widgets.multichoice['group_domains'] = MultiChoice(title='Domain',
                                                options=[],
                                                width=300)

    view.widgets.multichoice['group_domains'].on_change('value', p.select_group_segments_callback)

    view.widgets.selectors['select_by'] = Select(options=['distance', 'domain_distance', 'diam', 'section_diam'],
                                            value='distance',
                                            title='Select by',
                                            width=100)

    view.widgets.selectors['select_by'].on_change('value', p.select_group_segments_callback)                                            

    view.widgets.spinners['condition_min'] = NumericInput(value=None, title='Min', width=75, mode='float')
    view.widgets.spinners['condition_max'] = NumericInput(value=None, title='Max', width=75, mode='float')

    view.widgets.spinners['condition_min'].on_change('value', p.select_group_segments_callback)
    view.widgets.spinners['condition_max'].on_change('value', p.select_group_segments_callback)



    add_group_panel = column([
        row([view.widgets.text['group_name'],
             view.widgets.buttons['add_group'],
             ]),
        view.widgets.multichoice['group_domains'],
        row([
            view.widgets.selectors['select_by'],
            view.widgets.spinners['condition_min'],
            view.widgets.spinners['condition_max'],
        ])
        ])

    return add_group_panel



def create_select_group_panel():

    view.widgets.selectors['group'] = Select(title='Groups',
                                         options=[], 
                                         value=None,
                                         width=150,
                                         )

    view.widgets.selectors['group'].on_change('value', p.select_group_segs_callback)

    view.widgets.buttons['remove_group'] = Button(label='Remove group',
                                                    button_type='danger',
                                                    disabled=False,
                                                    width=100,
                                                    styles={"padding-top":"20px"}
                                                    )

    view.widgets.buttons['remove_group'].on_event(ButtonClick, p.remove_group_callback)


    return row([view.widgets.selectors['group'],
            view.widgets.buttons['remove_group'],
        ])



def create_groups_tab():

    panels = column([
        create_add_group_panel(),
        Div(text='<hr style="width:30em; margin-top:3em">'), 
        create_select_group_panel(),
        ])

    groups_tab = TabPanel(title='Groups', 
                        child=panels)
    
    return groups_tab

# =================================================================
# MECHANISMS TAB
# =================================================================

def create_mechanisms_tab():

    view.widgets.multichoice['mechanisms'] = MultiChoice(title='Added mechanisms',
                                                        options=[],
                                                        value=[],
                                                        visible=True,
                                                        width=300)
    view.widgets.multichoice['mechanisms'].on_change('value', p.add_mechanism_callback)

    view.widgets.switches['recompile'] = Switch(active=False, 
                                                name='recompile')
    view.widgets.buttons['add_default_mechanisms'] = Button(label='Add default mechanisms', button_type='primary', width=100)
    view.widgets.buttons['add_default_mechanisms'].on_event(ButtonClick, p.add_default_mechanisms_callback)

                    

    view.widgets.selectors['mechanism_to_insert'] = Select(
        title='Mechanism',
        options=['Leak'],
        value = 'Leak',
    )

    view.widgets.selectors['mechanism_to_insert'].on_change('value', p.select_mechanism_to_insert_callback)

    view.widgets.multichoice['domains'] = MultiChoice(title='Domains where to insert:',
                                                              options=[],
                                                              value=[],
                                                              visible=True,
                                                              width=300)

    view.widgets.multichoice['domains'].on_change('value', p.insert_mechanism_callback)

    insert_panel = column([
        row(view.widgets.switches['recompile'], Div(text='Recompile mod files')),
        view.widgets.multichoice['mechanisms'],
        view.widgets.buttons['add_default_mechanisms'],
        view.widgets.selectors['mechanism_to_insert'],
        view.widgets.multichoice['domains'],
    ])

    return TabPanel(title='Mechanisms',
                    child=insert_panel)

# =================================================================
# PARAMETERS TAB
# =================================================================


def create_distribution_plot():

    view.figures['distribution'] = figure(width=400,
                                          height=150,
                                          match_aspect=False,
                                          tools='pan, box_zoom, hover, reset, save',)

    view.figures['distribution'].toolbar.autohide = True
    view.figures['distribution'].background_fill_color = None
    view.figures['distribution'].border_fill_color = None

    view.sources['distribution'] = ColumnDataSource(data={'x': [], 'y': []})

    view.figures['distribution'].circle(x='x', y='y', source=view.sources['distribution'], line_width=2, color='color')
    hspan = Span(location=0, dimension='width', line_color='white', line_width=1)
    view.figures['distribution'].add_layout(hspan)
    vspan = Span(location=0, dimension='height', line_color='white', line_width=1)
    view.figures['distribution'].add_layout(vspan)


def create_group_panel():

    view.widgets.selectors['distribution_type'] = Select(
        title='Distribution type',
        value='constant',
        options=['constant', 'linear', 'exponential', 'sigmoid', 'sinusoidal', 'gaussian', 'step', 'inherit'],
        width=150,
        visible=True
    )

    view.widgets.selectors['distribution_type'].on_change('value', p.update_distribution_type_callback)


    create_distribution_plot()
    view.DOM_elements['distribution_widgets_panel'] = column(width=300)

    return column([
        view.widgets.selectors['distribution_type'],
        view.DOM_elements['distribution_widgets_panel'],
        view.figures['distribution'],
    ], visible=False)

def create_param_panel():


    view.widgets.selectors['assigned_group'] = Select(title='Groups',
                                         options=[], 
                                         value=None,
                                         width=150,
                                         )

    view.widgets.selectors['assigned_group'].on_change('value', p.select_group_callback)


    view.widgets.buttons['add_distribution'] = Button(label='Add distribution',
                                                    button_type='primary',
                                                    disabled=False,
                                                    visible=True,
                                                    width=150,
                                                    styles={"padding-top":"20px"}
                                                    )

    view.widgets.buttons['add_distribution'].on_event(ButtonClick, p.add_distribution_callback)

    view.widgets.buttons['remove_distribution'] = Button(label='Remove distribution',
                                                    button_type='danger',   
                                                    disabled=False,
                                                    visible=False,
                                                    width=150,
                                                    styles={"padding-top":"20px"}
                                                    )

    view.widgets.buttons['remove_distribution'].on_event(ButtonClick, p.remove_distribution_callback)

    view.DOM_elements['group_panel'] = create_group_panel()

    return column([
        row([
            view.widgets.selectors['assigned_group'],
            view.widgets.buttons['add_distribution'],
            view.widgets.buttons['remove_distribution'],
        ]),
        view.DOM_elements['group_panel'],
    ], visible=False)

def create_distribution_tab():

    view.widgets.selectors['mechanism'] = Select(title='Mechanism',
                                                options=['Independent'],
                                                value = 'Independent',
                                                )

    view.widgets.selectors['mechanism'].on_change('value', p.select_mechanism_callback)

    view.widgets.buttons['standardize'] = Button(label='Standardize',
                                                button_type='warning',
                                                visible=False,
                                                width=100,
                                                styles={"padding-top":"20px"}
                                                )

    add_message(view.widgets.buttons['standardize'], 'Standardizing. Please wait...', callback_type='on_click')
    
    view.widgets.buttons['standardize'].on_event(ButtonClick, p.standardize_callback)
    view.widgets.buttons['standardize'].on_event(ButtonClick, p.voltage_callback_on_event)
    
    view.widgets.selectors['param'] = Select(title='Parameter',
                                            options=[],
                                            value=None,
                                            width=150)

    view.widgets.selectors['param'].description = 'Select a parameter defined as a RANGE variable in the MOD file.'

    view.widgets.selectors['param'].on_change('value', p.select_param_callback)



    selection_panel = column([
        row([
            view.widgets.selectors['mechanism'],
            view.widgets.buttons['standardize']
        ]),
        view.widgets.selectors['param'],
    ])


    view.DOM_elements['param_panel'] = create_param_panel()
    

    distibution_panel = column([
        selection_panel,
        view.DOM_elements['param_panel'],
    ])

    distribution_tab = TabPanel(title='Parameters', 
                                child=distibution_panel)
    
    return distribution_tab



# -----------------------------------------------------------
# STIMULI TAB 
# -----------------------------------------------------------

# -----------------------------------------------------------
# RECORDINGS
# -----------------------------------------------------------

view.widgets.buttons['remove_all'] = Button(label='Remove all', button_type='danger')
view.widgets.buttons['remove_all'].on_event(ButtonClick, p.remove_all_callback)
view.widgets.buttons['remove_all'].on_event(ButtonClick, p.voltage_callback_on_event)

view.widgets.switches['record_from_all'] = Switch(active=False, disabled=True)
view.widgets.switches['record_from_all'].on_change('active', p.record_from_all_callback)
view.widgets.switches['record_from_all'].on_change('active', p.voltage_callback_on_change)

view.widgets.switches['record'] = Switch(active=False)
view.widgets.switches['record'].on_change('active', p.record_callback)
view.widgets.switches['record'].on_change('active', p.voltage_callback_on_change)


# -----------------------------------------------------------
# ICLAMPS
# -----------------------------------------------------------

view.widgets.switches['iclamp'] = Switch(active=False)
view.widgets.switches['iclamp'].on_change('active', p.toggle_iclamp_callback)
view.widgets.switches['iclamp'].on_change('active', p.voltage_callback_on_change)

view.widgets.sliders['iclamp_duration'] = RangeSlider(start=0, end=300, 
                                         value=(100,200), step=10, 
                                         title="Duration, ms", 
                                         visible=False)
view.widgets.sliders['iclamp_duration'].on_change('value_throttled', p.iclamp_duration_callback)
view.widgets.sliders['iclamp_duration'].on_change('value_throttled', p.voltage_callback_on_change)

view.widgets.sliders['iclamp_amp'] = AdjustableSpinner(title="Amp (pA)", value=0, step=1, visible=False)
view.widgets.sliders['iclamp_amp'].on_change('value_throttled', p.iclamp_amp_callback)
view.widgets.sliders['iclamp_amp'].on_change('value_throttled', p.voltage_callback_on_change)

# -----------------------------------------------------------
# SYNAPSES
# -----------------------------------------------------------

# ADD POPULATION

view.widgets.selectors['syn_type'] = Select(
    title='Synaptic type', 
    value='AMPA_NMDA', 
    options=['AMPA', 'NMDA', 'AMPA_NMDA', 'GABAa'], 
    width=150
)
view.widgets.selectors['syn_type'].on_change('value', p.select_synapse_type_callback)

view.widgets.spinners['N_syn'] = NumericInput(value=1, title='N syn', width=100)

view.widgets.buttons['add_population'] = Button(label='Add population', 
                                                button_type='primary', 
                                                disabled=False)
view.widgets.buttons['add_population'].on_event(ButtonClick, 
                                                p.add_population_callback)
view.widgets.buttons['add_population'].on_event(ButtonClick, 
                                                p.voltage_callback_on_event)

# SELECT / REMOVE POPULATION

view.widgets.selectors['population'] = Select(options=[], title='Population', width=150)
view.widgets.selectors['population'].on_change('value', p.select_population_callback)

view.widgets.buttons['remove_population'] = Button(label='Remove population', button_type='danger', disabled=False, styles={"padding-top":"20px"})
view.widgets.buttons['remove_population'].on_event(ButtonClick, p.remove_population_callback)
view.widgets.buttons['remove_population'].on_event(ButtonClick, p.voltage_callback_on_event)

view.DOM_elements['population_panel'] = column(width=300)

widgets_stimuli = column([
    view.widgets.buttons['remove_all'],
    row([view.widgets.selectors['section'],
    view.widgets.selectors['seg_x']]),
    row([view.widgets.switches['iclamp'], Div(text='Inject current')]),
    view.widgets.sliders['iclamp_duration'], 
    view.widgets.sliders['iclamp_amp'].get_widget(),
    Div(text='<hr style="width:30em">'),
    row([view.widgets.selectors['syn_type'], view.widgets.spinners['N_syn']]),
    view.widgets.buttons['add_population'],
    Div(text='<hr style="width:30em">'),
    row([view.widgets.selectors['population'], view.widgets.buttons['remove_population']]),
    view.DOM_elements['population_panel'],
])

widgets_recordings = column([
    row([view.widgets.selectors['section'],
    view.widgets.selectors['seg_x']]),
    row([view.widgets.switches['record_from_all'], Div(text='Record from all')]),
    row([view.widgets.switches['record'], Div(text='Record voltage')]),
])

# -----------------------------------------------------------
# TABS
# -----------------------------------------------------------


tab_section_vars = TabPanel(title='Morphology', 
                            child=widgets_section_vars)

tab_recordings = TabPanel(title='Recordings',
                            child=widgets_recordings)

tab_stimuli = TabPanel(title='Stimuli', 
                       child=widgets_stimuli)

view.widgets.tabs['section'] = Tabs(tabs=[tab_section_vars, 
                                          create_mechanisms_tab(),
                                          create_groups_tab(),
                                          create_distribution_tab(),
                                          tab_recordings,
                                          tab_stimuli])
# view.widgets.tabs['section'].disabled = True                                          

view.widgets.tabs['section'].on_change('active', p.switch_tab_callback)


view.widgets.buttons['record_current'] = Button(label='Record current', button_type='primary', visible=False)
view.widgets.buttons['record_current'].on_event(ButtonClick, p.record_current_callback)

view.DOM_elements['channel_panel'] = column([Div(text='Select a channel')], width=300)


right_menu = column(
    view.widgets.tabs['section'], 
    align='center',
    name='right_menu_section'
)

curdoc().add_root(right_menu)









# ====================================================================================
# LEFT MENU
# ====================================================================================

# ------------------------------------------------------------------------------------
## I/O TAB
# ------------------------------------------------------------------------------------


# Loading a model from JSON
available_models = p.list_models()
view.widgets.selectors['model'] = Select(value='Select a model to load',
                                options=['Select a model to load'] + available_models,
                                title='Model',
                                width=242)

view.widgets.selectors['model'].on_change('value', p.select_model_callback)
view.widgets.selectors['model'].description = 'Select a neuronal model to load. To select another model, reload the page.'

view.widgets.selectors['morphology'] = Select(value='Select morphology',
                                options=['Select a morphology'],
                                title='Morphology',
                                width=242)

add_message(view.widgets.selectors['morphology'], 'Loading morphology. Please wait...', callback_type='on_change')
view.widgets.selectors['morphology'].on_change('value', p.load_morphology_callback)

view.widgets.selectors['membrane'] = Select(value='Select membrane config.',
                                options=['Select membrane config.'],
                                title='Membrane config.',
                                width=242)

add_message(view.widgets.selectors['membrane'], 'Loading membrane config. Please wait...', callback_type='on_change')
view.widgets.selectors['membrane'].on_change('value', p.load_membrane_callback)

view.widgets.selectors['stimuli'] = Select(value='Select stimuli',
                                options=['Select stimuli'],
                                title='Stimuli',
                                width=242)

add_message(view.widgets.selectors['stimuli'], 'Loading stimuli. Please wait...', callback_type='on_change')
view.widgets.selectors['stimuli'].on_change('value', p.load_stimuli_callback)



# Export model
view.widgets.text['file_name'] = TextInput(value='', title='File name', width=242)

view.widgets.buttons['export_model'] = Dropdown(label='Export model',
                                                width=242,
                                                button_type='default',
                                                menu=[('Export morphology', 'morphology'), 
                                                      ('Export membrane config', 'membrane'),
                                                      ('Export stimuli', 'stimuli')])
view.widgets.buttons['export_model'].on_event("menu_item_click", p.export_model_callback)

view.widgets.buttons['download_model'] = Button(label='Download model as .zip', button_type='primary', width=242)
view.widgets.buttons['download_model'].on_event(ButtonClick, p.download_model_callback)

# File import
view.widgets.file_input['all'] = FileInput(accept='.swc, .asc, .mod', name='file', visible=True, width=242, disabled=False)
view.widgets.file_input['all'].on_change('filename', p.import_file_callback)
view.widgets.file_input['all'].on_change('value', p.import_file_callback)


tab_io = TabPanel(title='I/O', 
                child=column(
                    # view.DOM_elements['status'],
                    view.widgets.selectors['model'],
                    view.widgets.selectors['morphology'],
                    view.widgets.selectors['membrane'],
                    view.widgets.selectors['stimuli'],
                    Div(text='<hr style="width:18.5em; margin-top:3em">'), 
                    # view.widgets.file_input['all'],
                    view.widgets.text['file_name'],
                    view.widgets.buttons['export_model'],
                    view.widgets.buttons['download_model'],
                    Div(text='<hr style="width:18.5em; margin-top:3em">')
                    )
                )

# ------------------------------------------------------------------------------------
## Simulation tab                                
# ------------------------------------------------------------------------------------

# Segmentation
view.widgets.sliders['d_lambda'] = Slider(start=0, end=0.2, value=0.1, step=0.01, title="d_lambda", width=242)

view.widgets.buttons['set_segmentation'] = Button(label='Set segmentation', button_type='primary', disabled=False, width=242)
view.widgets.buttons['set_segmentation'].on_event(ButtonClick, p.build_seg_tree_callback)

view.widgets.sliders['duration'] = Slider(value=300, start=100, end=1000, step=100, title='Duration, ms', width=200, format='0[.]0')
view.widgets.sliders['duration'].js_link('value', view.widgets.sliders['iclamp_duration'], 'end')
view.widgets.sliders['dt'] = Slider(value=0.025, start=0.025, end=0.1, step=0.025, title='dt, ms', width=200, format='0[.]000')
view.widgets.sliders['temperature'] = Slider(value=37, start=0, end=45, step=0.1, title='Temperature, °C', width=200, format='0[.]0')
view.widgets.sliders['v_init'] = Slider(value=-70, start=-100, end=100, step=0.5, title='V init, mV', width=200, format='0[.]0')

view.widgets.sliders['dt'].on_change('value_throttled', p.update_dt_callback)
view.widgets.sliders['temperature'].on_change('value_throttled', p.update_temperature_callback)
view.widgets.sliders['v_init'].on_change('value_throttled', p.update_v_init_callback)

view.widgets.sliders['duration'].on_change('value_throttled', p.voltage_callback_on_change)
view.widgets.sliders['dt'].on_change('value_throttled', p.voltage_callback_on_change)
view.widgets.sliders['temperature'].on_change('value_throttled', p.voltage_callback_on_change)
view.widgets.sliders['v_init'].on_change('value_throttled', p.voltage_callback_on_change)


view.widgets.switches['real_time'] = Switch(active=True)
def enable_run_button(attr, old, new):
    view.widgets.buttons['run'].disabled = new
view.widgets.switches['real_time'].on_change('active', enable_run_button)

tab_sim = TabPanel(
    title='Simulation',
    child=column(
        view.widgets.sliders['d_lambda'],
        view.widgets.buttons['set_segmentation'],
        Div(text='<hr style="width:18.5em; margin-top:3em">'), 
        view.widgets.sliders['duration'],
        view.widgets.sliders['dt'],
        view.widgets.sliders['temperature'],
        view.widgets.sliders['v_init'],
        row(view.widgets.switches['real_time'], Div(text='Real-time update')),
        view.widgets.buttons['run'],
        view.DOM_elements['runtime'],
        )
)

# ------------------------------------------------------------------------------------
## Validation tab
# ------------------------------------------------------------------------------------

view.DOM_elements['stats_ephys'] = Div(text='Validation results:')

# view.widgets.buttons['stats_ephys'] = Button(label='Stats Ephys', button_type='default')
view.widgets.buttons['stats_ephys'] = Dropdown(label='Validate', 
                                               button_type='default', 
                                               menu=[('Detect spikes', 'spikes'), 
                                                     ('Input resistance and time constant', 'R_in'), 
                                                     ('Atttenuation', 'attenuation'), 
                                                     ('Sag ratio', 'sag_ratio'), 
                                                     ('f-I curve', 'fI_curve'), 
                                                     ('I-V curve', 'iv_curve'),
                                                     ('Dendritic nonlinearity', 'nonlinearity'),
                                                     ])
view.widgets.buttons['stats_ephys'].on_event("menu_item_click", p.stats_ephys_callback)

# view.widgets.buttons['iterate'] = Button(label='Iterate', 
#                                          button_type='default', 
#                                          visible=False)

# view.widgets.buttons['iterate'].on_event(ButtonClick, p.iterate_validation_callback)

view.figures['stats_ephys'] = figure(width=300, height=200,
                                    x_axis_label='Current (nA)',
                                    y_axis_label='Frequency (Hz)',
                                    tools='pan, box_zoom, reset, save',
                                    visible=False)

view.sources['stats_ephys'] = ColumnDataSource(data={'x': [], 'y': []})   

view.figures['stats_ephys'].circle(x='x', y='y', source=view.sources['stats_ephys'], color='red', size=5)

view.widgets.buttons['clear_validation'] = Button(label='Clear', button_type='danger')

def clear_validation_callback():
    view.sources['stats_ephys'].data = {'x': [], 'y': []}
    view.sources['detected_spikes'].data = {'x': [], 'y': []}
    view.sources['frozen_v'].data = {'xs': [], 'ys': []}
    view.widgets.switches['frozen_v'].active = False
    view.figures['stats_ephys'].visible = False

view.widgets.buttons['clear_validation'].on_event(ButtonClick, clear_validation_callback)

tab_validation = TabPanel(title='Validation',
                    child=column(view.widgets.buttons['stats_ephys'],
                                  view.DOM_elements['stats_ephys'],
                                #   view.widgets.buttons['iterate'],
                                  view.figures['stats_ephys'],
                                  view.widgets.buttons['clear_validation'],
                                  )
                    )

view.widgets.tabs['simulation'] = Tabs(tabs=[tab_io, 
                                            tab_sim,
                                            tab_validation,
                                            ], 
                                        visible=True)
        
# left_menu = column(view.widgets.selectors['cell'],
#                    view.widgets.sliders['d_lambda'],
#                    view.widgets.file_input['all'],
#                    json_panel,
#                    view.widgets.multichoice['mod_files'],
#                    view.widgets.multichoice['mod_files_std'],
#                    view.widgets.sliders['duration'],
#                    view.widgets.sliders['dt'],
#                    view.widgets.sliders['temperature'],
#                    view.widgets.sliders['v_init'],
#                    name='left_menu')

left_menu = column([
    view.DOM_elements['status'],
    view.widgets.tabs['simulation']
    ], name='left_menu')

curdoc().add_root(left_menu)




# curdoc().add_root(status_bar)









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
view.widgets.sliders['voltage_plot_y_range'] = RangeSlider(start=-200, end=200, value=(-100, 100), step=1, title='Voltage plot y range', width=200)

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
    value='twopi',
)

settings_panel = column(view.widgets.selectors['theme'],
                        # view.widgets.selectors['output_format'],
                        # view.widgets.color_pickers['color_picker'],
                        view.widgets.switches['show_kinetics'],
                        view.widgets.sliders['voltage_plot_x_range'],
                        view.widgets.sliders['voltage_plot_y_range'],
                        row(view.widgets.switches['enable_record_from_all'], Div(text='Enable record from all')),
                        view.widgets.selectors['graph_layout'],
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

curdoc().theme = 'dark_minimal'




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
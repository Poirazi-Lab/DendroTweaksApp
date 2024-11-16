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



from view import CellView
view = CellView()

from model.model import CellModel
model = CellModel(path_to_model='app/model/')

from presenter.presenter import Presenter
p = Presenter(view=view, model=model)



# MAIN WORKSPACE


## CELL PANEL
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

view.widgets.sliders['rotate_cell'].on_change('value', p.update_3D_callback)

panel_cell = column(view.figures['cell'], view.widgets.sliders['rotate_cell'], name='panel_cell')
panel_cell.background = None
curdoc().add_root(panel_cell)



## SECTION PANEL

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

view.widgets.selectors['seg_x'].on_change('value', p.select_seg_x_callback)


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


panel_section = column(view.figures['section_diam'], 
                       view.figures['section_param'], 
                       widgets_navigation, name='panel_section',
                       width=270, height=350,
                       sizing_mode='fixed')










## GRAPH PANEL

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

hover = HoverTool(callback=graph_hover_callback, tooltips=[("ID", "@index"), ("Name", "@name"), ("Type", "@type"), ("Area", "@area"), ("Diam", "@diam"), ("Dist", "@dist"), ("Ra", "@Ra"), ('g leak', '@gbar_leak{0.000000}'), ('g na', '@gbar_na{0.000000}'), ('g kv', '@gbar_kv{0.000000}'), ("Recordings", "@recordings"), ("AMPA", "@AMPA"), ("Weights", "@weights"), ("Iclamps", "@iclamps"), ("line_color", "@line_color"), ("voltage", "@voltage"), ("cai", "@cai")])
view.figures['graph'].add_tools(hover)

# Add select widget
view.widgets.selectors['mechanism'] = Select(title='Mechanism:')

view.widgets.selectors['graph_param'] = Select(title="Parameter:")

view.widgets.sliders['graph_param_high'] = Slider(start=0, end=1, value=1, 
                                                 step=0.01, title="High", width=200, visible=True)
view.widgets.sliders['time_slice'] = Spinner(title="Time slice", low=0, high=1000, step=0.1, value=100, width=100, visible=False)

view.widgets.sliders['time_slice'].on_change('value_throttled', p.update_time_slice_callback)

# Attach the callback to the dropdown selector
view.widgets.selectors['graph_param'].on_change('value', p.update_graph_colors_callback)


def update_high(attr, old, new):
    param = view.widgets.selectors['graph_param'].value
    if param == 'type':
        pass
    else:
        graph_renderer = view.figures['graph'].renderers[0]
        palette = graph_renderer.node_renderer.glyph.fill_color.transform.palette
        new_color_mapper = LinearColorMapper(palette=palette, low=0, high=new)
        param = graph_renderer.node_renderer.glyph.fill_color.field
        graph_renderer.node_renderer.glyph.fill_color = {'field': param, 'transform': new_color_mapper}
        # graph_renderer.node_renderer.selection_glyph.fill_color = {'field': param, 'transform': new_color_mapper}
        # graph_renderer.node_renderer.nonselection_glyph.fill_color = {'field': param, 'transform': new_color_mapper}
        view.figures['graph'].renderers[0] = graph_renderer

view.widgets.sliders['graph_param_high'].on_change('value', update_high)

panel_graph = column(view.figures['graph'], 
                    row(
                        # view.widgets.selectors['section'],
                        # view.widgets.selectors['seg_x'],
                        view.widgets.selectors['graph_param'], 
                         view.widgets.sliders['graph_param_high'],
                        view.widgets.sliders['time_slice'],
                         ), 
                    name='panel_graph',
                    width_policy='fit',
                    sizing_mode='scale_width',)

panel_graph = row(panel_section, panel_graph, name='panel_graph', width=800, height=560)

curdoc().add_root(panel_graph)










## SIMULATION PANEL

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










# RIGHT HAND MENU

## Sliders
view.widgets.sliders['n_seg'] = Slider(start=1, end=21, value=1, step=2, title='nseg')

view.widgets.sliders['n_seg'].on_change('value_throttled', p.nseg_callback)

view.widgets.sliders['length'] = Slider(start=1, end=200, 
                           value=1, 
                           step=1, title='Length (μm)', visible=False)

    
view.widgets.sliders['length'].on_change('value_throttled', p.length_callback)

view.widgets.sliders['Ra'] = Slider(start=1, end=200,
                          value=100,
                            step=1, title='Ra, Ω*cm', visible=False)

# view.widgets.sliders['Ra'].on_change('value_throttled', p.Ra_callback)

view.widgets.spinners['Ra'] = Spinner(value=100, title='Ra', width=60, step=1, visible=True)
view.widgets.spinners['Ra'].on_change('value', p.update_Ra_callback)
view.widgets.spinners['Ra'].on_change('value', p.voltage_callback_on_change)

view.widgets.buttons['reduce'] = Button(label='Reduce subtree', button_type='warning')

view.widgets.buttons['reduce'].on_event(ButtonClick, p.reduce_subtree_callback)
view.widgets.buttons['reduce'].on_event(ButtonClick, p.voltage_callback_on_event)

view.widgets.buttons['to_swc'] = Button(label='Export to SWC', button_type='default')
view.widgets.buttons['to_swc'].on_event(ButtonClick, p.export_to_swc_callback)

view.DOM_elements['stats'] = Div(text='Stats:')

view.widgets.buttons['stats'] = Button(label='Stats', button_type='default')
view.widgets.buttons['stats'].on_event(ButtonClick, p.stats_callback)


stats_panel = column([view.widgets.buttons['stats'], 
                     view.DOM_elements['stats'],
                     view.figures['section_param_hist'],
                     ],
                     name='stats_panel')

delete_button = Button(label='Delete subtree', button_type='danger')
delete_button.on_event(ButtonClick, p.delete_subtree_callback)

widgets_section_vars = column([
                        # row([selectors['root'], selectors['section']]),
                        # row([buttons['parent'], buttons['sibling'], buttons['child']]),
                        # column([Div(text='Parameter:'), view.widgets.selectors['graph_param']]),
                        view.widgets.sliders['length'],
                        view.widgets.sliders['Ra'],
                        view.widgets.sliders['n_seg'],
                        view.widgets.spinners['Ra'],
                        # panel_section,
                        row([view.widgets.buttons['reduce'], view.widgets.buttons['to_swc']]),
                        delete_button,
                        stats_panel,
                        ], name='widgets_section_vars')


### Distribution selector
view.widgets.selectors['sec_type'] = MultiChoice(title='Section type', 
                                                options=['soma', 'axon', 'dend', 'apic'],
                                                width=242)

view.widgets.selectors['sec_type'].on_change('value', p.select_type_callback)

view.widgets.spinners['e_leak'] = Spinner(value=-70, title='e_leak', width=60, step=1, visible=False)
view.widgets.spinners['ena'] = Spinner(value=50, title='ena', width=60, step=1, visible=False)
view.widgets.spinners['ek'] = Spinner(value=-77, title='ek', width=60, step=1, visible=False)
view.widgets.spinners['eca'] = Spinner(value=140, title='eca', width=60, step=1, visible=False)

view.widgets.spinners['ena'].on_change('value', p.update_ena_callback)
view.widgets.spinners['ek'].on_change('value', p.update_ek_callback)
view.widgets.spinners['eca'].on_change('value', p.update_eca_callback)
view.widgets.spinners['e_leak'].on_change('value', p.update_e_leak_callback)

view.widgets.spinners['e_leak'].on_change('value', p.voltage_callback_on_change)
view.widgets.spinners['ena'].on_change('value', p.voltage_callback_on_change)
view.widgets.spinners['ek'].on_change('value', p.voltage_callback_on_change)
view.widgets.spinners['eca'].on_change('value', p.voltage_callback_on_change)



equilibrium_panel = row([view.widgets.spinners['e_leak'],
                            view.widgets.spinners['ena'],
                            view.widgets.spinners['ek'],
                            view.widgets.spinners['eca'],
                            ])


view.widgets.selectors['graph_param'].on_change('value', p.update_distribution_selector_options_callback)

view.widgets.selectors['distribution_type'] = Select(value='uniform',
                               options=['uniform', 'linear', 'exponential', 'sigmoid', 'gaussian', 'step'],
                               title='Distribution type')


view.widgets.buttons['add_group'] = Button(label='Add distribution', button_type='primary', disabled=False)
view.widgets.buttons['add_group'].on_event(ButtonClick, p.add_group_callback)



add_panel = column(row(view.widgets.selectors['graph_param'], 
                        ),
                row(view.widgets.selectors['distribution_type'], 
                    ),
                    view.widgets.buttons['add_group'],
                    )
                

view.widgets.selectors['distribution'] = Select(options=[], title='Distributions')
view.widgets.buttons['remove_distribution'] = Button(label='Remove', button_type='danger')


view.widgets.buttons['remove_distribution'].on_event(ButtonClick, p.remove_group_callback)
view.widgets.buttons['remove_distribution'].on_event(ButtonClick, p.update_plots_on_param_change_callback)
view.widgets.buttons['remove_distribution'].on_event(ButtonClick, p.voltage_callback_on_event)

remove_panel = column(view.widgets.selectors['distribution'], 
                      view.widgets.buttons['remove_distribution'])

view.figures['distribution'] = figure(width=400,
                                    height=150,
                                    match_aspect=False,
                                    tools='pan, box_zoom, hover, reset, save',)

from bokeh.models import NumeralTickFormatter
# view.figures['distribution'].yaxis[0].formatter = NumeralTickFormatter(format="0.0000000")

# hide toolbar and show only on hover
view.figures['distribution'].toolbar.autohide = True
view.figures['distribution'].background_fill_color = None
view.figures['distribution'].border_fill_color = None

view.sources['distribution'] = ColumnDataSource(data={'x': [], 'y': []})

view.figures['distribution'].circle(x='x', y='y', source=view.sources['distribution'], line_width=2, color='color')
hspan = Span(location=0, dimension='width', line_color='white', line_width=1)
view.figures['distribution'].add_layout(hspan)
vspan = Span(location=0, dimension='height', line_color='white', line_width=1)
view.figures['distribution'].add_layout(vspan)


view.widgets.selectors['distribution'].on_change('value', p.select_group_callback)


view.DOM_elements['distribution_panel'] = column(width=300)




widgets_range_vars = column([view.widgets.selectors['sec_type'],
                             equilibrium_panel,
                             add_panel, 
                             remove_panel, 
                             view.figures['distribution'], 
                             view.DOM_elements['distribution_panel'],
                             ]
                             )


view.widgets.switches['iclamp'] = Switch(active=False)


        

view.widgets.switches['iclamp'].on_change('active', p.toggle_iclamp_callback)

view.widgets.sliders['iclamp_duration'] = RangeSlider(start=0, end=300, 
                                         value=(100,200), step=10, 
                                         title="Duration, ms", 
                                         visible=False)



view.widgets.sliders['iclamp_duration'].on_change('value_throttled', p.iclamp_duration_callback)

from bokeh_utils import AdjustableSpinner
# view.widgets.sliders['iclamp_amp'] = Slider(start=-1000, end=1000, value=0,
#                     step=1, title="Amp", format='0[.]00000', 
#                     width=200, 
#                     visible=False)
view.widgets.sliders['iclamp_amp'] = AdjustableSpinner(title="Amp (pA)", value=0, step=1, visible=False)
# view.widgets.selectors['iclamp_amp_unit'] = Select(value='pA', options=['pA', 'nA', 'uA'], title='Units', width=50, visible=False)
# view.widgets.selectors['iclamp_amp_unit'].on_change('value', p.iclamp_amp_callback)

view.widgets.sliders['iclamp_amp'].on_change('value_throttled', p.iclamp_amp_callback)

view.widgets.switches['record'] = Switch(active=False)
view.widgets.switches['record_from_all'] = Switch(active=False, disabled=True)

view.widgets.switches['record_from_all'].on_change('active', p.record_from_all_callback)
view.widgets.switches['record_from_all'].on_change('active', p.voltage_callback_on_change)

view.widgets.switches['record'].on_change('active', p.record_callback)
view.widgets.switches['record'].on_change('active', p.voltage_callback_on_change)
view.widgets.switches['iclamp'].on_change('active', p.voltage_callback_on_change)
view.widgets.sliders['iclamp_amp'].on_change('value_throttled', p.voltage_callback_on_change)
# view.widgets.selectors['iclamp_amp_unit'].on_change('value', p.voltage_callback_on_change)
view.widgets.sliders['iclamp_duration'].on_change('value_throttled', p.voltage_callback_on_change)

remove_all_button = Button(label='Remove all', button_type='danger')

remove_all_button.on_event(ButtonClick, p.remove_all_callback)
remove_all_button.on_event(ButtonClick, p.voltage_callback_on_event)

view.widgets.selectors['syn_type'] = Select(value='AMPA_NMDA', options=['AMPA', 'NMDA', 'AMPA_NMDA', 'GABAa'], title='Synaptic type', width=150)

view.widgets.selectors['syn_type'].on_change('value', p.select_synapse_type_callback)

view.widgets.spinners['N_syn'] = NumericInput(value=1, title='N syn', width=100)
view.widgets.selectors['syn_group'] = Select(options=[], title='Syn group')
view.widgets.selectors['syn_group'].on_change('value', p.select_synapse_group_callback)

view.DOM_elements['syn_group_panel'] = column(width=300)
# view.widgets.sliders['syn rate'] = Slider(start=0, end=100, value=0, step=1, title="Rate, Hz", width=200)
# view.widgets.sliders['noise'] = Slider(start=0, end=1, value=0, step=0.1, title="Noise", width=200)

view.widgets.buttons['add_synapse_group'] = Button(label='Add synapse group', button_type='primary', disabled=False)
view.widgets.buttons['remove_synapse_group'] = Button(label='Remove synapse group', button_type='danger', disabled=False)


view.widgets.buttons['add_synapse_group'].on_event(ButtonClick, p.add_synapse_group_callback)
view.widgets.buttons['add_synapse_group'].on_event(ButtonClick, p.voltage_callback_on_event)
view.widgets.buttons['remove_synapse_group'].on_event(ButtonClick, p.remove_synapse_group_callback)
view.widgets.buttons['remove_synapse_group'].on_event(ButtonClick, p.voltage_callback_on_event)

widgets_point_processes = column([remove_all_button,
                          row([view.widgets.selectors['section'],
                          view.widgets.selectors['seg_x']]),
                          row([view.widgets.switches['record_from_all'], Div(text='Record from all')]),
                          row([view.widgets.switches['record'], Div(text='Record voltage')]),
                          row([view.widgets.switches['iclamp'], Div(text='Inject current')]),
                          view.widgets.sliders['iclamp_duration'], 
                        #   row(view.widgets.sliders['iclamp_amp'], view.widgets.selectors['iclamp_amp_unit']),
                          view.widgets.sliders['iclamp_amp'].get_widget(),
                          Div(text='<hr style="width:30em">'),
                          row([view.widgets.selectors['syn_type'], view.widgets.spinners['N_syn']]),
                        #   view.widgets.sliders['syn rate'],
                        #     view.widgets.sliders['noise'],
                          view.widgets.buttons['add_synapse_group'],
                          view.widgets.selectors['syn_group'],
                          view.widgets.buttons['remove_synapse_group'],
                          view.DOM_elements['syn_group_panel'],
                          ])

tab_section_vars = TabPanel(title='Morphology', 
                             child=widgets_section_vars)
tab_rabge_vars = TabPanel(title='Membrane', 
                             child=widgets_range_vars)
tab_point_processes = TabPanel(title='Stimuli', 
                       child=widgets_point_processes)

view.widgets.tabs['section'] = Tabs(tabs=[tab_section_vars, tab_rabge_vars, tab_point_processes])

def tab_section_callback(attr, old, new):
    if p.model.cell is None:
        return
    if new in [0, 2]:
        view.widgets.selectors['graph_param'].options = list(view.params)
        view.widgets.selectors['graph_param'].value = 'type' if new == 0 else 'recordings'
        view.widgets.selectors['section'].value = 'soma[0]'
    elif new == 1:
        view.widgets.selectors['graph_param'].options = list(view.ephys_params)
        view.widgets.selectors['graph_param'].value = 'cm'
        
    
    panel_section.visible = True if new in [0] else False
    
    # disable lasso tool
    lasso_tool = view.figures['graph'].select_one(LassoSelectTool)
    if new == 0:
        if view.figures['graph'].toolbar.active_drag is lasso_tool:
            view.figures['graph'].toolbar.active_drag = None
    else:
        view.figures['graph'].toolbar.active_drag = lasso_tool


view.widgets.tabs['section'].on_change('active', tab_section_callback)


view.widgets.selectors['channel'] = Select(title='Channel', options=[], visible=False)
view.widgets.selectors['channel'].on_change('value', p.select_channel_callback)
view.widgets.selectors['channel'].on_change('value', p.states_callback)
view.widgets.buttons['record_current'] = Button(label='Record current', button_type='primary', visible=False)
view.widgets.buttons['record_current'].on_event(ButtonClick, p.record_current_callback)

view.DOM_elements['channel_panel'] = column([Div(text='Select a channel')], width=300)

view.widgets.buttons['toggle_activation_curves'] = RadioButtonGroup(labels=['Cell', 'Channels'], active=0, margin=(5, 5, 20, 80))

def toggle_activation_curves_callback(attr, old, new):
    if new == 0:
        view.widgets.selectors['channel'].visible = False
        view.widgets.buttons['record_current'].visible = False
        view.DOM_elements['channel_panel'].visible = False
        view.widgets.tabs['section'].visible = True
        view.figures['inf'].visible = False
        view.figures['inf_log'].visible = False
        view.figures['tau'].visible = False
        view.figures['tau_log'].visible = False
        if view.widgets.tabs['section'].active == 0: panel_section.visible = True
    elif new == 1:
        view.widgets.tabs['section'].visible = False
        view.widgets.selectors['channel'].visible = True
        view.widgets.buttons['record_current'].visible = True
        view.DOM_elements['channel_panel'].visible = True
        panel_section.visible = False
        view.figures['inf'].visible = True
        view.figures['tau'].visible = True

view.widgets.buttons['toggle_activation_curves'].on_change('active', toggle_activation_curves_callback)

view.DOM_elements['channel_menu'] = column([row([view.widgets.selectors['channel'], 
                                                 view.widgets.buttons['record_current']]),
                                            view.DOM_elements['channel_panel']])

right_menu = column(view.widgets.buttons['toggle_activation_curves'],
                    row(view.widgets.tabs['section'], 
                        view.DOM_elements['channel_menu']
                        ), 
                    align='center',
                    name='right_menu_section')

curdoc().add_root(right_menu)










# LEFT HAND MENU

view.widgets.selectors['cell'] = Select(value='Select a cell to begin',
                       options=['Select a cell to begin'] + [f for f in os.listdir('app/model/swc') if f.endswith('.swc') or f.endswith('.asc')], 
                       title='Cell:', 
                       width=242)
view.widgets.selectors['cell'].description = 'Select an SWC file to load. To select another cell, reload the page.\nIt is recommended to choose d_lambda before loading a cell.'

view.widgets.selectors['cell'].on_change('value', p.selector_cell_callback)

view.widgets.sliders['d_lambda'] = Slider(start=0, end=0.2, value=0.1, step=0.01, title="d_lambda", width=200)

view.widgets.sliders['d_lambda'].on_change('value_throttled', p.selector_cell_callback)

view.widgets.buttons['to_json'] = Button(label='Export biophys', button_type='primary', disabled=True)
view.widgets.buttons['to_json'].on_event(ButtonClick, p.to_json_callback)




view.widgets.buttons['from_json'] = Button(label='Import biophys', button_type='primary')
view.widgets.buttons['from_json'].on_event(ButtonClick, p.from_json_callback)
view.widgets.buttons['from_json'].on_event(ButtonClick, p.voltage_callback_on_event)


json_panel = row(view.widgets.buttons['to_json'], 
                view.widgets.buttons['from_json'])

view.widgets.file_input['all'] = FileInput(accept='.swc, .asc, .mod', name='file', visible=True, width=242, disabled=False)
view.widgets.file_input['all'].on_change('filename', p.import_file_callback)
view.widgets.file_input['all'].on_change('value', p.import_file_callback)

view.widgets.multichoice['mod_files'] = MultiChoice(title='Mechanisms', 
                                    value=['Leak'],
                                    options = p.model.list_mod_files(),
                                    width=242)

view.widgets.multichoice['mod_files_std'] = MultiChoice(title='Mechanisms standard', 
                                    options = p.model.list_mod_files(mod_folder='mod_standard'),
                                    width=242)

view.widgets.selectors['mod_files_cadyn'] = Select(title='Ca dynamics',
                                    options = p.model.list_mod_files(mod_folder='mod_cadyn') + [''],
                                    value = '',
                                    width=242)


view.widgets.multichoice['mod_files'].on_change('value', p.mod_files_callback)
view.widgets.multichoice['mod_files'].on_change('value', p.voltage_callback_on_change)
view.widgets.multichoice['mod_files_std'].on_change('value', p.mod_files_callback)
view.widgets.multichoice['mod_files_std'].on_change('value', p.voltage_callback_on_change)
view.widgets.selectors['mod_files_cadyn'].on_change('value', p.cadyn_files_callback)
view.widgets.selectors['mod_files_cadyn'].on_change('value', p.voltage_callback_on_change)

view.widgets.sliders['duration'] = Slider(value=300, start=100, end=1000, step=100, title='Duration, ms', width=200, format='0[.]0')
view.widgets.sliders['duration'].js_link('value', view.widgets.sliders['iclamp_duration'], 'end')
view.widgets.sliders['dt'] = Slider(value=0.025, start=0.025, end=0.1, step=0.025, title='dt, ms', width=200, format='0[.]000')
view.widgets.sliders['celsius'] = Slider(value=37, start=0, end=45, step=0.1, title='Temperature, °C', width=200, format='0[.]0')
view.widgets.sliders['v_init'] = Slider(value=-70, start=-100, end=100, step=0.5, title='V init, mV', width=200, format='0[.]0')

view.widgets.sliders['dt'].on_change('value_throttled', p.update_dt_callback)
view.widgets.sliders['celsius'].on_change('value_throttled', p.update_celsius_callback)
view.widgets.sliders['v_init'].on_change('value_throttled', p.update_v_init_callback)

view.widgets.sliders['duration'].on_change('value_throttled', p.voltage_callback_on_change)
view.widgets.sliders['dt'].on_change('value_throttled', p.voltage_callback_on_change)
view.widgets.sliders['celsius'].on_change('value_throttled', p.voltage_callback_on_change)
view.widgets.sliders['v_init'].on_change('value_throttled', p.voltage_callback_on_change)

tab_io = TabPanel(title='Input/Output', 
                             child=column(view.widgets.selectors['cell'],
                                          view.widgets.sliders['d_lambda'],
                                            view.widgets.file_input['all'],
                                            json_panel,
                                            view.widgets.multichoice['mod_files'],
                                            view.widgets.multichoice['mod_files_std'],
                                            view.widgets.selectors['mod_files_cadyn'],
                             )
                                )

view.widgets.switches['real_time'] = Switch(active=True)
def enable_run_button(attr, old, new):
    view.widgets.buttons['run'].disabled = new
view.widgets.switches['real_time'].on_change('active', enable_run_button)

tab_sim = TabPanel(title='Simulation',
                    child=column(view.widgets.sliders['duration'],
                                  view.widgets.sliders['dt'],
                                  view.widgets.sliders['celsius'],
                                  view.widgets.sliders['v_init'],
                                  row(view.widgets.switches['real_time'], Div(text='Real-time update')),
                                  view.widgets.buttons['run'],
                                  view.DOM_elements['runtime'],
                                  )
                    )

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
#                    view.widgets.sliders['celsius'],
#                    view.widgets.sliders['v_init'],
#                    name='left_menu')

left_menu = column(view.widgets.tabs['simulation'], name='left_menu')

curdoc().add_root(left_menu)




# curdoc().add_root(status_bar)










### Settings panel

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

view.widgets.switches['recompile'] = Switch(active=True, name='recompile')                                             

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

view.widgets.sliders['voltage_plot_x_range'].on_change('value_throttled', update_voltage_plot_x_range)
view.widgets.sliders['voltage_plot_y_range'].on_change('value_throttled', update_voltage_plot_y_range)



settings_panel = column(view.widgets.selectors['theme'],
                        # view.widgets.selectors['output_format'],
                        # view.widgets.color_pickers['color_picker'],
                        view.widgets.sliders['voltage_plot_x_range'],
                        view.widgets.sliders['voltage_plot_y_range'],
                        row(view.widgets.switches['recompile'], Div(text='Recompile mod files')),
                        row(view.widgets.switches['enable_record_from_all'], Div(text='Enable record from all')),
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




custom_js = CustomJS(args=dict(), code="""
    console.log('Before');
    
    const columnElement = document.querySelector('.bk-Column');
    const TabsElement = columnElement.shadowRoot.querySelector('.bk-Tabs');
    const columnElement2 = TabsElement.shadowRoot.querySelector('.bk-Column');
    const MultiChoiceElement = columnElement2.shadowRoot.querySelector('.bk-MultiChoice');
    const choicesInner = MultiChoiceElement.shadowRoot.querySelector('.choices__inner');

    choicesInner.style.height = '100px';
    choicesInner.style.overflow = 'auto';

    console.log('After');
""")

view.widgets.buttons['from_json'].js_on_event(ButtonClick, custom_js)
import numpy as np

from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

import networkx as nx
import colorcet as cc

from bokeh.plotting import from_networkx
from bokeh.models import Circle, MultiLine
from bokeh.models import CategoricalColorMapper, LinearColorMapper

from utils import timeit
from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout 
import numpy as np
from neuron import h

from logger import logger

from bokeh.palettes import Spectral11

# DOMAIN_TO_COLOR = {'soma': '#E69F00', 'axon': '#F0E442', 'dend': '#019E73', 'apic': '#0072B2'}


class GraphMixin():

    def __init__(self):
        logger.debug('GraphMixin init')
        super().__init__()
        self.G = None

    # ========================================================================================================
    # CREATE GRAPH
    # ========================================================================================================

    # CREATE NX

    @log
    @timeit
    def _create_seg_graph_nx(self):

        # self.G = neuron_to_seg_graph(self.model.cell)
        self.G = nx.Graph()
        total_nseg = len(self.model.seg_tree)
        for seg in self.model.seg_tree:
            radius = int(200/np.sqrt(total_nseg)) if seg._section.domain == 'soma' else int(150/np.sqrt(total_nseg))
            self.G.add_node(seg.idx, 
                            sec = seg._section.idx,
                            x = round(seg.x, 3),
                            domain=seg._section.domain,
                            cm = seg._ref.cm,
                            Ra = seg._section._ref.Ra,
                            diam = seg.diam,
                            section_diam = seg._section.diam,
                            area = seg.area,
                            subtree_size = seg.subtree_size,
                            distance = seg.path_distance(),
                            domain_distance = seg.path_distance(within_domain=True),
                            length=seg._section.length,
                            rec_v='None',
                            iclamps=0,
                            radius=radius*0.0015,
                            fill_color=self.view.get_domain_color(seg._section.domain),
                            )
            if seg.parent is not None:
                self.G.add_edge(seg.parent.idx, seg.idx)

        # pos = nx.kamada_kawai_layout(self.G, scale=1, center=(0, 0), dim=2)
        pos = self._calculate_positions()
        nx.set_node_attributes(self.G, pos, 'pos')
        # self._rotate_graph()

    @log
    @timeit
    def _calculate_positions(self):        
        # pos = {seg.idx: (seg._section.xs[0] + seg.x * (seg._section.xs[-1] - seg._section.xs[0]),
        #          seg._section.ys[0] + seg.x * (seg._section.ys[-1] - seg._section.ys[0]))
        #        for seg in self.model.seg_tree}
        graph_layout = self.view.widgets.selectors['graph_layout'].value
        logger.info('Using layout: ' + graph_layout)
        if graph_layout == 'kamada-kawai':
            pos = nx.kamada_kawai_layout(self.G, scale=1, center=(0, 0), dim=2)
        elif graph_layout in ['dot', 'neato', 'twopi']:
            pos = graphviz_layout(self.G, 
                prog=graph_layout,
                root=0)
        
        return pos

    # CREATE GRAPH RENDERER


    def _create_graph_renderer(self):

        self.selected_secs = set()
        self.selected_segs = []
        
        # REMOVE OLD GRAPH RENDERER
        self.view.figures['graph'].renderers = []
        
        # CREATE NEW GRAPH RENDERER
        self._create_seg_graph_nx()

        graph_renderer = from_networkx(
            graph=self.G,
            layout_function=nx.layout.spring_layout,
            pos=nx.get_node_attributes(self.G, 'pos'),
            iterations=0
        )

        # UPDATE GLYPH
        self._update_glyph(graph_renderer)

        # UPDATE SELECTION GLYPH
        self._update_selection_glyph(graph_renderer)

        # UPDATE NONSELECTION GLYPH
        self._update_nonselection_glyph(graph_renderer)

        # ADD RENDEER TO FIGURE
        self.view.figures['graph'].renderers.append(graph_renderer)

        # UPDATE PARAM OPTIONS
        self.view.params.update({'Recordings': [f'rec_{var}' for var in self.avaliable_vars_to_record]})
        self.view.widgets.selectors['graph_param'].options = {**self.view.params, **self.model.mechs_to_params}

        self.add_lasso_callback()


    def _update_glyph(self, graph_renderer):

        graph_renderer.node_renderer.glyph = Circle(radius='radius',
                                                    radius_units='data',
                                                    fill_color='fill_color',
                                                    line_color='line_color',
                                                    line_alpha='line_alpha',
                                                    line_width='line_width')
        graph_renderer.node_renderer.glyph.line_alpha = 0.3  # 0.3
        graph_renderer.node_renderer.glyph.line_width = 0.5
        graph_renderer.node_renderer.glyph.fill_alpha = 1
        color_mapper = CategoricalColorMapper(palette=[self.view.get_domain_color(domain) for domain in self.model.domains],
                                              factors=[domain for domain in self.model.domains])
        graph_renderer.node_renderer.glyph.fill_color = {'field': 'domain', 'transform': color_mapper}

        graph_renderer.edge_renderer.glyph = MultiLine(line_color=self.view.theme.graph_colors['edge'],
                                                       line_alpha=0.5, 
                                                       line_width=1)

        # graph_renderer.selection_policy

    def _update_selection_glyph(self, graph_renderer):
        graph_renderer.node_renderer.selection_glyph = Circle(radius='radius',
                                                              radius_units='data',
                                                              fill_color='fill_color',
                                                              line_color='line_color',
                                                              line_alpha='line_alpha',
                                                              line_width='line_width')
        # graph_renderer.node_renderer.selection_glyph = graph_renderer.node_renderer.glyph
        # graph_renderer.node_renderer.selection_glyph.line_alpha = 0.8
        graph_renderer.node_renderer.selection_glyph.fill_alpha = 1  # 1
        graph_renderer.node_renderer.selection_glyph.line_width = 1
        color_mapper = CategoricalColorMapper(palette=[self.view.get_domain_color(domain) for domain in self.model.domains],
                                              factors=[domain for domain in self.model.domains])
        graph_renderer.node_renderer.selection_glyph.fill_color = {'field': 'domain', 'transform': color_mapper}
        # graph_renderer.node_renderer.selection_glyph.line_width = int(G.nodes[1]['size']) * 0.1
        # graph_renderer.node_renderer.selection_glyph.line_color = view.theme.graph_line

    def _update_nonselection_glyph(self, graph_renderer):
        graph_renderer.node_renderer.nonselection_glyph = Circle(radius='radius', 
                                                            radius_units='data',
                                                            fill_color='fill_color', 
                                                            line_color=self.view.theme.graph_colors['edge'], 
                                                            line_alpha='line_alpha', 
                                                            line_width='line_width')
        # graph_renderer.node_renderer.nonselection_glyph = graph_renderer.node_renderer.glyph
        # graph_renderer.node_renderer.nonselection_glyph = graph_renderer.node_renderer.glyph
        graph_renderer.node_renderer.nonselection_glyph.fill_alpha = 0.3
        color_mapper = CategoricalColorMapper(palette=[self.view.get_domain_color(domain) for domain in self.model.domains],
                                              factors=[domain for domain in self.model.domains])
        graph_renderer.node_renderer.nonselection_glyph.fill_color = {'field': 'domain', 'transform': color_mapper}
        graph_renderer.node_renderer.nonselection_glyph.line_width = 0.3
        # graph_renderer.node_renderer.nonselection_glyph.fill_alpha = 0.5 #0.7
        graph_renderer.node_renderer.nonselection_glyph.line_alpha = 0.3 #0.7
    
    # ========================================================================================================
    # UPDATE GRAPH
    # ========================================================================================================

    # --------------------------------------------------------------------------------------------
    # UPDATE PARAMS
    # --------------------------------------------------------------------------------------------

    def select_graph_param_callback(self, attr, old, new):
        """
        Callback for the selectors['graph_param'] widget.
        Toggles the panel with widgets for the selected parameter.
        """
        param_name = new
        self._update_graph_param(param_name, update_colors=True)


    def update_graph_callback(self, event):
        param_name = self.view.widgets.selectors['graph_param'].value
        self._update_graph_param(param_name, update_colors=True)
    

    @log
    def _update_graph_param(self, param_name, update_colors=True):
        """
        Updates the parameter values of the graph extracting the values
        from the model.
        Also updates the colors of the graph based on the parameter values.
        """
        logger.info(f'Updating graph parameter {param_name}')

        self.view.figures['graph'].renderers[0].node_renderer.data_source.data[param_name] = \
            [self._get_param_value(seg, param_name) for seg in self.model.seg_tree]
        # self.view.figures['graph'].renderers[0].node_renderer.data_source.data[param_name] = [self.G.nodes[n][param_name][0] for n in self.G.nodes]

        if update_colors: self._update_graph_colors(param_name)
        
        self.update_section_param_data(param_name)


    def _get_param_value(self, seg, param_name):
        """
        Retrieves the value of the specified parameter for the given segment.
        """

        # RECORDINGS
        if param_name.startswith('rec_'):
            param_name = param_name.replace('rec_', '')
            return str(seg.idx) if self.model.recordings.get(param_name, {}).get(seg) is not None else np.nan

        # elif param_name == 'voltage':
        #     self.model.simulator.recordings['v'][seg].to_python() if param_name == 'voltage' else 0,

        # STIMULI
        elif param_name == 'iclamps':
            return 1 if self.model.iclamps.get(seg) is not None else np.nan

        elif param_name in ['AMPA', 'NMDA', 'GABAa', 'AMPA_NMDA']:
            relevant_populations = self.model.populations[param_name]
            if not relevant_populations:
                return np.nan
            if not any(seg in pop.segments for pop in relevant_populations.values()):
                return np.nan
            return sum(pop.n_per_seg[seg] 
                       for pop in relevant_populations.values()
                       if seg in pop.segments)

        elif param_name == 'weights':
            if self.model.synapses.get(seg) is not None:
                weights = sum(con.weight[0] * (1 if syn.e >= 0 else -1) for con, syn in zip(self.cell.synapses[seg][2], self.cell.synapses[seg][0]))
                return weights
            return 0
        
        # NORMAL PARAMS
        elif param_name == 'Ra':
            return seg._section._ref.Ra
        elif param_name == 'domain_distance':
            return seg.path_distance(within_domain=True)
        elif param_name == 'distance':
            return seg.path_distance()
        elif param_name == 'section_diam':
            return seg._section._ref.diam
        else:
            return seg.get_param_value(param_name)



    # --------------------------------------------------------------------------------------------
    # UPDATE COLORS
    # --------------------------------------------------------------------------------------------


    # def update_graph_colors_callback(self, attr, old, new):
    #     """
    #     Updates graph colors without updating the parameters.
    #     Needed to visualize the distribution on selecting a parameter.
    #     """
    #     param_name = new
    #     if new == 'voltage':
    #         self._update_graph_param('voltage')
    #     else:
    #         self._update_graph_param(param_name)
    #         # self._update_graph_colors(param_name)
    #         # self.update_section_param_data(param_name)


    @log
    def _update_graph_colors(self, param):

        # GET VIEW
        graph_renderer = self.view.figures['graph'].renderers[0]
        self.view.widgets.sliders['time_slice'].visible = False
        self.view.widgets.sliders['graph_param_high'].visible = False

        if param == 'domain': 
            color_mapper = CategoricalColorMapper(
                palette=[self.view.get_domain_color(domain) for domain in self.model.domains], 
                factors=[domain for domain in self.model.domains]
            )
            self.view.widgets.sliders['graph_param_high'].visible = False
        elif param.startswith('rec_'):
            labels = [str(seg.idx) for seg in self._recorded_segments]
            color_mapper = CategoricalColorMapper(
                palette=cc.glasbey_light, 
                factors=labels, 
                nan_color=self.view.theme.graph_colors['node_fill']
            )
            self.view.widgets.sliders['graph_param_high'].visible = False
        # elif param == 'voltage':
        #     color_mapper = LinearColorMapper(palette=cc.bmy, low=-70, high=40)
        #     self.view.widgets.sliders['time_slice'].visible = True
        else:
            if param == 'iclamps':
                color_mapper = LinearColorMapper(palette=['red'], high=1, nan_color=self.view.theme.graph_colors['node_fill'])
            elif param == 'AMPA':
                color_mapper = LinearColorMapper(palette=['gray'] + cc.kr[100:-10], low=0, nan_color=self.view.theme.graph_colors['node_fill'])
            elif param == 'GABAa':
                color_mapper = LinearColorMapper(palette=['gray'] + cc.kb[100:-10], low=0, nan_color=self.view.theme.graph_colors['node_fill'])
            elif param == 'NMDA':
                color_mapper = LinearColorMapper(palette=['gray'] + cc.kg[100:-10], low=0, nan_color=self.view.theme.graph_colors['node_fill'])
            elif param == 'AMPA_NMDA':
                color_mapper = LinearColorMapper(palette=['gray'] + cc.fire[100:-10], low=0, nan_color=self.view.theme.graph_colors['node_fill'])
            elif param == 'weights':
                low = min(graph_renderer.node_renderer.data_source.data[param])
                high = max(graph_renderer.node_renderer.data_source.data[param])
                v = max(abs(low), abs(high))
                color_mapper = LinearColorMapper(palette=cc.bjy, low=-v, high=v)
            else:
                values = [v for v in graph_renderer.node_renderer.data_source.data[param]
                          if v is not np.nan]
                null_color = ['gray'] if sum(values) == 0 else []
                if not values:
                    values = [0]
                low, high = min(values), max(values)
                if low >= 0: low = 0
                if high <= 0: high = 0
                val = max(abs(low), abs(high))
                color_mapper = LinearColorMapper(
                    palette=self.view.theme.palettes['params'] + null_color,
                    low=-val, 
                    high=val, 
                    nan_color=self.view.theme.graph_colors['node_fill']
                    )  #rainbow4

                self._update_colormap_max_widget(values)

        # APPLY COLOR MAPPER
        graph_renderer.node_renderer.glyph.fill_color = {'field': param, 'transform': color_mapper}
        graph_renderer.node_renderer.selection_glyph.fill_color = {'field': param, 'transform': color_mapper}
        graph_renderer.node_renderer.nonselection_glyph.fill_color = {'field': param, 'transform': color_mapper}
        self.view.figures['graph'].renderers[0] = graph_renderer

        self.view.figures['graph'].title.text = f'Seg graph: {param}'


    def _update_colormap_max_widget(self, values):

        self.view.widgets.sliders['graph_param_high'].visible = True
        max_val = max(
            value for value in values
            if value is not None
        )
        self.view.widgets.sliders['graph_param_high'].end = max_val
        self.view.widgets.sliders['graph_param_high'].step = max_val / 100
        self.view.widgets.sliders['graph_param_high'].value = max_val
    
    def colormap_max_callback(self, attr, old, new):
        param_name = self.view.widgets.selectors['graph_param'].value
        if param_name == 'domain':
            return
        graph_renderer = self.view.figures['graph'].renderers[0]
        palette = graph_renderer.node_renderer.glyph.fill_color.transform.palette
        new_color_mapper = LinearColorMapper(palette=palette, low=-new, high=new)
        param_name = graph_renderer.node_renderer.glyph.fill_color.field
        graph_renderer.node_renderer.glyph.fill_color = {'field': param_name, 'transform': new_color_mapper}
        graph_renderer.node_renderer.selection_glyph.fill_color = {'field': param_name, 'transform': new_color_mapper}
        graph_renderer.node_renderer.nonselection_glyph.fill_color = {'field': param_name, 'transform': new_color_mapper}
        self.view.figures['graph'].renderers[0] = graph_renderer

    @log
    @timeit
    def update_time_slice_callback(self, attr, old, new):
        t = self.view.widgets.sliders['time_slice'].value
        logger.debug(f'Updating time slice to {t}')
        
        self.view.renderers['span_v'].location = t
        # self.view.sources['span_v'].data = {'x': [t, t], 'y': [-90, 90]}
        # if any([len(s.groups) for s in self.model.synapses.values()]):
        # self.view.renderers['span_t'].location = t
        dt = self.model.simulator.dt
        time_stemp = int(t / dt)
            
        # self.view.figures['graph'].renderers[0].node_renderer.data_source.data['voltage'] = [self.G.nodes[n]['voltage'][time_stemp] for n in self.G.nodes]


    # ========================================================================================================
    # TRANSFORM GRAPH
    # ========================================================================================================

    def _rotate_graph(self):
        # Get the positions of the nodes
        pos = nx.get_node_attributes(self.G, 'pos')
        pos_array = np.array(list(pos.values()))

        # If the graph has less than two nodes, or all nodes have the same position,
        # return the original graph
        if len(pos) < 2 or np.all(pos_array == pos_array[0]):
            return

        # Center the data
        pos_centered = pos_array - np.mean(pos_array, axis=0)

        # Compute the covariance matrix
        cov_matrix = np.cov(pos_centered.T)

        # Compute the eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)

        # Sort the eigenvectors based on the eigenvalues
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # The first principal component is now the last column in eigenvectors
        # We want this to be the y-axis, so we swap the columns if necessary.
        if eigenvalues[0] > eigenvalues[1]:
            eigenvectors = eigenvectors[:, ::-1]

        # Transform the centered data
        pos_pca = np.dot(pos_centered, eigenvectors)

        # Get the types of the nodes
        # types = nx.get_node_attributes(self.G, 'type')

        # Find the highest node id of type 'apic'
        # apic_ids = [node for node, _type in types.items() if _type == 'apic']
        # highest_apic_id = max(apic_ids) if apic_ids else None

        # Find the nodes of type 'soma'
        # soma_ids = [node for node, _type in types.items() if _type == 'soma']

        # If 'apic' and 'soma' nodes exist and the y-coordinate of the highest 'apic' node is not higher than any 'soma' node,
        # flip the graph by negating the y-coordinates
        # if highest_apic_id is not None and soma_ids and not all(pos_pca[highest_apic_id, 1] > pos_pca[soma_id, 1] for soma_id in soma_ids):
        
        # pos_pca[:, 1] = -pos_pca[:, 1]

        # Update the positions in the graph
        for i, node in enumerate(self.G.nodes):
            self.G.nodes[node]['pos'] = pos_pca[i]
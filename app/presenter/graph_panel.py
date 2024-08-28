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
import numpy as np
from neuron import h

from logger import logger

def neuron_to_seg_graph(cell):
    logger.info('START')
    G = nx.Graph()
    soma = cell.soma[0]
    total_nseg = sum([sec.nseg for sec in cell.all])
    logger.debug(f'Total nseg: {total_nseg}')
    add_sec_to_graph(G, soma, 0, cell, total_nseg)
    return G

def get_gbars(sec):
    return [f'gbar_{mech}'
            for mech, params in sec.psection()['density_mechs'].items() 
            if 'gbar' in params]

def get_sec_area(sec):
    return sum([seg.area() for seg in sec])

def add_sec_to_graph(G, sec, parent_id, cell, total_nseg):
    # color_map = {'soma': 'red', 'dend': 'lawngreen', 'axon': 'pink', 'apic': 'dodgerblue'}
    color_map = {'soma': 'orange', 'axon': 'magenta', 'dend': 'lawngreen', 'apic': 'dodgerblue'}
    color_map = {'soma': '#E69F00', 'axon': '#F0E442', 'dend': '#019E73', 'apic': '#0072B2'}
    nodes = {seg: idx + len(G.nodes) + 1 for idx, seg in enumerate(sec)}
    if parent_id != 0:
        G.add_edge(parent_id, len(G.nodes) + 1)
    for seg, idx in nodes.items():
        seg_params = {param: getattr(seg, param) for param in ['diam', 'cm', ]}
        radius = int(200/np.sqrt(total_nseg)) if get_sec_type(sec) == 'soma' else int(150/np.sqrt(total_nseg))
        gbars = {gb: getattr(seg, gb) for gb in get_gbars(sec)}
        # logger.debug(f'gbars: {gbars}')
        G.add_node(int(idx), 
                   name=f'{get_sec_name(seg.sec)}({round(seg.x, 5)})', 
                   type=get_sec_type(seg.sec), 
                   sec=get_sec_name(seg.sec),
                   radius=radius*0.002, 
                   color=color_map[get_sec_type(seg.sec)],
                   line_color='white',
                   line_width=1,
                   line_alpha=0.5,
                   area=seg.area(), 
                   Ra=seg.sec.Ra,
                   dist=h.distance(seg, cell.soma[0](0.5)),
                #    g_pas=seg.g_pas,
                #    gbar_na=seg.gbar_na,
                #    gbar_kv=seg.gbar_kv,
                    cai = seg.cai if hasattr(seg, 'cai') else 0,
                   recordings='None',
                   iclamps=0,
                   AMPA=0,
                   NMDA=0,
                   AMPA_NMDA=0,
                   GABAa=0,
                   weights=0,
                   voltage=0,
                   **gbars,
                   **seg_params)
        # print(h.distance(seg, cell.soma[0](0.5)))
        if idx + 1 in nodes.values():
            G.add_edge(idx, idx + 1)
    for child in sec.children():
        if child.parentseg().x == 1:
            new_parent_id = list(nodes.values())[-1]
        elif child.parentseg().x == 0:
            new_parent_id = list(nodes.values())[0]
        else:
            new_parent_id = nodes[child.parentseg()]
        add_sec_to_graph(G, child, new_parent_id, cell, total_nseg)

# def neuron_to_sec_graph(cell):
#     color_map = {'soma': 'red', 'dend': 'lawngreen', 'axon': 'pink', 'apic': 'dodgerblue'}
#     G = nx.Graph()
#     nodes = {sec: idx + 1 for idx, sec in enumerate(cell.all)}
#     for sec, idx in nodes.items():
#         size = int(300/np.sqrt(len(cell.all))) if get_sec_type(sec) == 'soma' else int(150/np.sqrt(len(cell.all)))
#         G.add_node(idx, name=get_sec_name(sec), type=get_sec_type(sec), size=size, color=color_map[get_sec_type(sec)], area=get_sec_area(sec), length=sec.L, diam=sec.diam)
#         for child in sec.children():
#             G.add_edge(idx, nodes[child])
#     return G

class GraphMixin():

    def __init__(self):
        logger.debug('GraphMixin init')
        super().__init__()
        self.G = None

    def create_graph_nx(self):

        self.G = neuron_to_seg_graph(self.model.cell)

        for n in self.G.nodes:
            self.G.nodes[n]['(unset)'] = 0

        pos = nx.kamada_kawai_layout(self.G, scale=1, center=(0, 0), dim=2)
        nx.set_node_attributes(self.G, pos, 'pos')
        self.rotate_graph()

    @log
    def create_graph_renderer(self):
        # remove old graph
        self.view.figures['graph'].renderers = []
        # self.clear_segments()
        # add new graph
        self.create_graph_nx()
        graph_renderer = from_networkx(graph=self.G,
                                       layout_function=nx.layout.spring_layout,
                                       pos=nx.get_node_attributes(self.G,
                                                                  'pos'),
                                       iterations=0)

        # Change glyph
        graph_renderer.node_renderer.glyph = Circle(radius='radius',
                                                    radius_units='data',
                                                    fill_color='color',
                                                    line_color='line_color',
                                                    line_alpha='line_alpha',
                                                    line_width='line_width')
        graph_renderer.node_renderer.glyph.line_alpha = 0.3  # 0.3
        graph_renderer.node_renderer.glyph.line_width = 0.5
        graph_renderer.node_renderer.glyph.fill_alpha = 1
        color_mapper = CategoricalColorMapper(palette=['#E69F00', '#F0E442', '#019E73', '#0072B2'],
                                              factors=['soma', 'axon', 'dend', 'apic'])
        graph_renderer.node_renderer.glyph.fill_color = {'field': 'type', 'transform': color_mapper}

        graph_renderer.edge_renderer.glyph = MultiLine(line_color=self.view.theme.graph_line,
                                                       line_alpha=0.5, 
                                                       line_width=1)

        # graph_renderer.selection_policy

        # Change selection glyph
        graph_renderer.node_renderer.selection_glyph = Circle(radius='radius',
                                                              radius_units='data',
                                                              fill_color='color',
                                                              line_color='line_color',
                                                              line_alpha='line_alpha',
                                                              line_width='line_width')
        # graph_renderer.node_renderer.selection_glyph = graph_renderer.node_renderer.glyph
        # graph_renderer.node_renderer.selection_glyph.line_alpha = 0.8
        graph_renderer.node_renderer.selection_glyph.fill_alpha = 1  # 1
        graph_renderer.node_renderer.selection_glyph.line_width = 1
        # graph_renderer.node_renderer.selection_glyph.line_width = int(G.nodes[1]['size']) * 0.1
        # graph_renderer.node_renderer.selection_glyph.line_color = view.theme.graph_line

        # Change nonselection glyph
        graph_renderer.node_renderer.nonselection_glyph = Circle(radius='radius', 
                                                                 radius_units='data',
                                                                 fill_color='color', 
                                                                 line_color=self.view.theme.graph_line, 
                                                                 line_alpha='line_alpha', 
                                                                 line_width='line_width')
        # graph_renderer.node_renderer.nonselection_glyph = graph_renderer.node_renderer.glyph
        # graph_renderer.node_renderer.nonselection_glyph = graph_renderer.node_renderer.glyph
        graph_renderer.node_renderer.nonselection_glyph.fill_alpha = 0.3
        color_mapper = CategoricalColorMapper(palette=['#E69F00', '#F0E442', '#019E73', '#0072B2'], factors=['soma', 'axon', 'dend', 'apic'])
        graph_renderer.node_renderer.nonselection_glyph.fill_color = {'field': 'type', 'transform': color_mapper}
        graph_renderer.node_renderer.nonselection_glyph.line_width = 0.3
        # graph_renderer.node_renderer.nonselection_glyph.fill_alpha = 0.5 #0.7
        graph_renderer.node_renderer.nonselection_glyph.line_alpha = 0.3 #0.7

        self.view.figures['graph'].renderers.append(graph_renderer)


    def rotate_graph(self):
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
        pos_pca[:, 1] = -pos_pca[:, 1]

        # Update the positions in the graph
        for i, node in enumerate(self.G.nodes):
            self.G.nodes[node]['pos'] = pos_pca[i]

    
    
    
    @log
    @timeit
    def update_graph_param(self, param_name):
        logger.info(f'Updating graph parameter {param_name}')
        self.update_node_params_from_segments(param_name)
        if not param_name == 'voltage':
            self.view.figures['graph'].renderers[0].node_renderer.data_source.data[param_name] = [self.G.nodes[n][param_name] for n in self.G.nodes]
        else:
            self.view.figures['graph'].renderers[0].node_renderer.data_source.data[param_name] = [self.G.nodes[n][param_name][0] for n in self.G.nodes]
        self.update_graph_colors()


    def update_node_params_from_segments(self, param_name):
        """Updates the specified parameter of each node in the graph 
           with the corresponding value from the cell segment."""
        for n in self.G.nodes:
            seg_name = self.G.nodes[n]['name']
            seg = self.model.cell.segments[seg_name]
            if not self.G.nodes[n]["name"] == get_seg_name(seg):
                raise Exception(f'Node name {self.G.nodes[n]["name"]} does not match segment name {get_seg_name(seg)}')
            self.G.nodes[n][param_name] = self.get_param_value(seg, param_name)
            # logger.debug(f'Updated {param_name} for {get_seg_name(seg)} to {self.G.nodes[n][param_name]}')


    def get_param_value(self, seg, param_name):
        if param_name == 'type':
            return get_sec_type(seg.sec)
        elif param_name == 'area':
            return seg.area()
        elif param_name == 'Ra':
            return seg.sec.Ra
        elif param_name == 'dist':
            return self.model.cell.distance_from_soma(seg)
        elif param_name == 'recordings':
            return get_seg_name(seg) if self.model.simulator.recordings.get(seg) is not None else 'None'
        elif param_name == 'iclamps':
            return 1 if self.model.iclamps.get(seg) is not None else 0
        elif param_name in ['AMPA', 'NMDA', 'GABAa', 'AMPA_NMDA']:
            if len(self.model.synapses[param_name].groups):
                return sum([group.n_per_seg[seg] for group in self.model.synapses[param_name].groups if seg in group.segments])
            return 0
        elif param_name == 'weights':
            logger.debug(f'Updating weights for {get_seg_name(seg)}')
            if self.model.synapses.get(seg) is not None:
        
                logger.debug(f'weights: {sum([con.weight[0] * (1 if syn.e >=0 else -1) for con, syn in zip(self.cell.synapses[seg][2], self.cell.synapses[seg][0])])}')

                return sum([con.weight[0] * (1 if syn.e >=0 else -1) for con, syn in zip(self.cell.synapses[seg][2], self.cell.synapses[seg][0])])
            logger.debug('weights: 0')
            return 0
        elif param_name == '(unset)':
            return 0
        elif param_name == 'voltage':
            return self.model.simulator.recordings[seg].to_python()
        else:
            return getattr(seg, param_name)


    def update_graph_colors_callback(self, attr, old, new):
        if new == 'voltage':
            self.update_graph_param('voltage')
        else:
            self.update_graph_colors()
            self.update_section_param_data()


    @log
    def update_graph_colors(self):

        param = self.view.widgets.selectors['graph_param'].value
        graph_renderer = self.view.figures['graph'].renderers[0]
        self.view.widgets.sliders['time_slice'].visible = False

        if param == 'type': 
            color_mapper = CategoricalColorMapper(palette=self.view.theme.palettes['sec_type'], factors=['soma', 'axon', 'dend', 'apic'])
            graph_renderer.node_renderer.glyph.fill_color = {'field': param, 'transform': color_mapper}
            # color_mapper2 = CategoricalColorMapper(palette=DesaturatedSecTypePalette, factors=['soma', 'axon', 'dend', 'apic'])
            # graph_renderer.node_renderer.nonselection_glyph.fill_color = {'field': param, 'transform': color_mapper2}
            self.view.widgets.sliders['graph_param_high'].visible = False
        elif param == 'recordings':
            factors = ['None'] + [get_seg_name(seg) for seg in self.recorded_segments] + [get_seg_name(seg) for seg in self.model.simulator.recordings.keys() if seg not in self.recorded_segments]
            # color_mapper = CategoricalColorMapper(palette=[self.view.theme.graph_fill] + self.view.theme.palettes['trace'], factors=factors)
            color_mapper = CategoricalColorMapper(palette=[self.view.theme.graph_fill] + cc.glasbey_cool[:len(self.recorded_segments)], factors=factors)
            graph_renderer.node_renderer.glyph.fill_color = {'field': param, 'transform': color_mapper}
            self.view.widgets.sliders['graph_param_high'].visible = False
        elif param == 'voltage':
            color_mapper = LinearColorMapper(palette=cc.bmy, low=-70, high=40)
            graph_renderer.node_renderer.glyph.fill_color = {'field': param, 'transform': color_mapper}
            self.view.widgets.sliders['time_slice'].visible = True
        else:
            if param == 'iclamps':
                color_mapper = LinearColorMapper(palette=[self.view.theme.graph_fill, 'red'], low=0, high=1)
            elif param == 'AMPA':
                color_mapper = LinearColorMapper(palette=[self.view.theme.graph_fill] + cc.kr[50:-50], low=0)
            elif param == 'GABAa':
                color_mapper = LinearColorMapper(palette=[self.view.theme.graph_fill] + cc.kb[50:-50], low=0)
            elif param == 'NMDA':
                color_mapper = LinearColorMapper(palette=[self.view.theme.graph_fill] + cc.kg[50:-50], low=0)
            elif param == 'AMPA_NMDA':
                color_mapper = LinearColorMapper(palette=[self.view.theme.graph_fill] + cc.fire[50:-50], low=0)
            elif param == 'weights':
                low = min(graph_renderer.node_renderer.data_source.data[param])
                high = max(graph_renderer.node_renderer.data_source.data[param])
                v = max(abs(low), abs(high))
                color_mapper = LinearColorMapper(palette=cc.bjy, low=-v, high=v)
            else:
                # color_mapper = LinearColorMapper(palette=cc.rainbow4, low=0)  #rainbow4
                color_mapper = LinearColorMapper(palette=cc.rainbow4, low=0)  #rainbow4

            graph_renderer.node_renderer.glyph.fill_color = {'field': param, 'transform': color_mapper}

            # Update the slider
            self.view.widgets.sliders['graph_param_high'].visible = True
            max_val = max(graph_renderer.node_renderer.data_source.data[param])

            self.view.widgets.sliders['graph_param_high'].end = max_val
            self.view.widgets.sliders['graph_param_high'].value = max_val
        graph_renderer.node_renderer.glyph.fill_color = {'field': param, 'transform': color_mapper}
        graph_renderer.node_renderer.selection_glyph.fill_color = {'field': param, 'transform': color_mapper}
        graph_renderer.node_renderer.nonselection_glyph.fill_color = {'field': param, 'transform': color_mapper}

        self.view.figures['graph'].title.text = f'Seg graph: {param}'

        if all(value == 0 for value in graph_renderer.node_renderer.data_source.data[param]):
            graph_renderer.node_renderer.glyph.fill_color = self.view.theme.graph_fill #'#0d0887'  #'#440154'
            graph_renderer.node_renderer.selection_glyph.fill_color = self.view.theme.graph_fill #'#0d0887'  #'#440154'
            graph_renderer.node_renderer.nonselection_glyph.fill_color = self.view.theme.graph_fill #'#0d0887'  #'#440154'

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
            
        self.view.figures['graph'].renderers[0].node_renderer.data_source.data['voltage'] = [self.G.nodes[n]['voltage'][time_stemp] for n in self.G.nodes]

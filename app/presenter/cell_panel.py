import numpy as np
import pprint

from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

class CellMixin():

    def __init__(self):
        logger.debug('CellMixin init')
        super().__init__()
        self.selected_secs = set()
        self.selected_segs = []
        self.points = None
        

    def create_cell(self, path_to_swc):
        self.model.create_cell(path_to_swc)
        # self.cell = cell
        # self.sections = {get_sec_name(sec):sec for sec in self.cell.all}
        self.selected_secs = set()
        self.selected_segs = []
        # self.points = [sec.pts3d for sec in self.model.cell.sections.values()]
        self.points = self.get_pts3d()

    @log
    def create_cell_renderer(self):
        self.view.sources['cell'].data = self.get_cell_data()
        self.view.sources['soma'].data = self.get_soma_data()
        

    def update_3D_callback(self, attr, old, new):
        self.rotate_points(new - old)
        self.view.sources['cell'].data = self.get_cell_data()

    def get_pts3d(self):
        """
        Retrieves the 3D coordinates of all points in each section of the cell.

        Returns:
            list: A list of sections, each represented as a list of tuples containing 
            the 3D coordinates (x, y, z) of each point in the section.
        """
        pts3d = []
        for sec in self.model.cell.all:
            sec_pts3d = [(sec.x3d(i), sec.y3d(i), sec.z3d(i)) for i in range(sec.n3d())]
            pts3d.append(sec_pts3d)
        return pts3d


    @property
    def selected_sec(self):
        return list(self.selected_secs)[0] if len(self.selected_secs) == 1 else None

    ### Rotation methods ###         

    def get_rotation_point(self):
        soma = self.model.cell.soma[0]
        x = np.mean([soma.x3d(i) for i in range(soma.n3d())])
        y = np.mean([soma.y3d(i) for i in range(soma.n3d())])
        z = np.mean([soma.z3d(i) for i in range(soma.n3d())])
        return (x, y, z)

    def rotate_points(self, angle_deg):
        """Rotate a point cloud around the y-axis at a specific point"""

        rotation_point = self.get_rotation_point()

        angle = np.radians(angle_deg)
        rotation_matrix = np.array([
            [np.cos(angle), 0, np.sin(angle)],
            [0, 1, 0],
            [-np.sin(angle), 0, np.cos(angle)]
        ])

        rotated_points = []
        for point_set in self.points:
            rotated_set = []
            for point in point_set:
                # Translate the point so that the rotation point is at the origin
                translated_point = np.subtract(point, rotation_point)
                # Rotate the point
                rotated_point = np.dot(translated_point, rotation_matrix)
                # Translate the point back
                final_point = np.add(rotated_point, rotation_point)
                rotated_set.append(final_point)
            rotated_points.append(rotated_set)
        
        self.points = rotated_points

    

    ### CELL methods ###

    

    def update_cell_panel(self):  
        self.update_cell_selection()

    def update_cell_selection(self):
        with remove_callbacks(self.view.figures['cell'].renderers[0].data_source.selected):
            sec_names = [get_sec_name(sec) for sec in self.selected_secs]
            indices = [i for i, lbl in enumerate(self.labels) if lbl in sec_names]
            self.view.figures['cell'].renderers[0].data_source.selected.indices = indices

    def update_section_panel(self):
        self.update_section_data()
        self.update_section_widgets()
        self.update_status_message()

    def update_section_widgets(self):

        self.update_sec_selector()
        self.update_seg_x_selector()

        if len(self.selected_secs) == 1:
            self.view.widgets.sliders['n_seg'].value = self.selected_sec.nseg
            # self.view.widgets.sliders['length'].value = self.selected_sec.L
            self.view.widgets.sliders['Ra'].value = self.selected_sec.Ra

        self.update_navigation_buttons_on_reaching_terminal_branch()

    def update_sec_selector(self):
        with remove_callbacks(self.view.widgets.selectors['section']):
            if len(self.selected_secs) == 1:
                    self.view.widgets.selectors['section'].value = get_sec_name(self.selected_sec)
            else:
                self.view.widgets.selectors['section'].value = ''
            logger.debug(f"Updated section selector value: {self.view.widgets.selectors['section'].value}")
        logger.debug('END\n')


    def update_seg_x_selector(self):
        with remove_callbacks(self.view.widgets.selectors['seg_x']):
            if len(self.selected_secs) == 1:
                self.view.widgets.selectors['seg_x'].options = [str(round(seg.x, 5)) for seg in self.selected_segs[0].sec]
                self.view.widgets.selectors['seg_x'].value = str(round(self.selected_segs[0].x, 5))
            else:
                self.view.widgets.selectors['seg_x'].options = ['']
                self.view.widgets.selectors['seg_x'].value = ''
            logger.debug(f"Updated seg_x options: {self.view.widgets.selectors['seg_x'].options} and value: {self.view.widgets.selectors['seg_x'].value}")
        logger.debug('END\n')

    def update_navigation_buttons_on_reaching_terminal_branch(self):
        """
        Update navigation buttons when reaching leaf or root sections
        """

        if len(self.selected_secs) == 1:

            if self.selected_sec.children():
                self.view.widgets.buttons['child'].disabled = False
            else:
                self.view.widgets.buttons['child'].disabled = True

            if self.selected_sec.parentseg() is None:
                self.view.widgets.buttons['parent'].disabled = True
                self.view.widgets.buttons['sibling'].disabled = True
            else:
                self.view.widgets.buttons['parent'].disabled = False
                self.view.widgets.buttons['sibling'].disabled = False
        else:
            self.view.widgets.buttons['child'].disabled = True
            self.view.widgets.buttons['parent'].disabled = True
            self.view.widgets.buttons['sibling'].disabled = True

    def update_status_message(self):
        if len(self.selected_secs) == 1:
            preformatted_string = pprint.pformat(self.selected_sec.psection(), 
                                                    indent=4,
                                                    sort_dicts=False)
            spoiler = f'<details><summary>Toggle psection</summary><pre>{preformatted_string}</pre></details>'
            self.view.DOM_elements['status_bar'].text = spoiler
        elif len(self.selected_secs) > 1:
            self.view.DOM_elements['status_bar'].text = 'More than one section selected'
        else:
            self.view.DOM_elements['status_bar'].text = 'No section selected'

    @property
    def xs(self):
        return [[point[0] for point in point_set] for point_set in self.points]

    @property
    def ys(self):
        return [[point[1] for point in point_set] for point_set in self.points]
            
    @property
    def colors(self):
        color_map = {k:v for k,v in zip(['soma', 'axon', 'dend', 'apic'], self.view.theme.palettes['sec_type'])}
        # dimmed_color_map = self.dimmed_color_map
        selected_secs_set = set(self.selected_secs)
        # return [color_map[get_sec_type(sec)] if not sec in selected_secs_set else self.view.theme.selected_sec for sec in self.cell.all]
        return [color_map[get_sec_type(sec)] for sec in self.model.cell]
        # return [color_map[get_sec_type(sec)] if sec in self.selected_secs else dimmed_color_map[get_sec_type(sec)] for sec in self.cell.all]

    # @property
    # def alphas(self):
    #     return [1 if sec in self.selected_secs else 0.5 for sec in self.model.cell.all]

    @property
    def line_widths(self):
        """Returns the diameters as line_widths normalized to the range [1, 10]"""
        widths = np.array([sec.diam for sec in self.model.cell])
        widths = 1 + (widths - np.min(widths)) * (9 / (np.max(widths) - np.min(widths)))
        widths *= 1.5
        widths = widths.tolist()
        return widths

    @property
    def labels(self):
        return [get_sec_name(sec) for sec in self.model.cell]

    def get_cell_data(self):
        return {'xs': self.xs, 
                'ys': self.ys, 
                'color': self.colors, 
                'line_width': self.line_widths, 
                'label': self.labels}

    def get_soma_data(self):
        return {'x': [np.mean([self.model.cell.soma[0].x3d(i) for i in range(self.model.cell.soma[0].n3d())])], 
                'y': [np.mean([self.model.cell.soma[0].y3d(i) for i in range(self.model.cell.soma[0].n3d())])], 
                'color': [self.view.theme.palettes['sec_type'][0]], 
                'rad': [self.model.cell.soma[0].diam / 2]}


    ### SECTION methods ###

    def update_section_data(self):
        self.update_section_nseg_data()
        self.update_section_diam_data()
        self.update_section_param_data()

    def update_section_nseg_data(self):
        self.view.sources['section_nseg'].data = self.get_nsegs_data()

    def update_section_diam_data(self):
        sec_name = self.view.widgets.selectors['section'].value
        self.view.sources['section_diam'].data = self.get_diams_data()
        self.view.figures['section_diam'].title.text = f'{sec_name}: diam (pts3d)'

    def update_section_param_data(self):
        param_name = self.view.widgets.selectors['graph_param'].value
        if param_name in ['type', 'Ra', 'recordings', 'AMPA', 'NMDA', 'GABAa', 'AMPA_NMDA', 'weights', 'iclamps']:
            param_name = 'diam'
        sec_name = self.view.widgets.selectors['section'].value
        self.view.sources['section_param'].data = self.get_param_data(param_name)
        self.view.figures['section_param'].title.text = f'{sec_name}: {param_name}'
        self.view.figures['section_param'].yaxis.axis_label = self.view.params.get(param_name)
    
    def get_diam_lengths(self, sec):
        x = np.diff([sec.x3d(i) for i in range(sec.n3d())])
        y = np.diff([sec.y3d(i) for i in range(sec.n3d())])
        z = np.diff([sec.z3d(i) for i in range(sec.n3d())])
        lengths = np.sqrt(x**2 + y**2 + z**2)
        levels = [0]
        for i in range(len(lengths)):
            levels.append(levels[i] + lengths[i])
        # print('levels: ', levels)
        return np.array(levels)
    
    def get_diams_data(self):
        if len(self.selected_secs) == 1:
            
            selected_sec = self.selected_sec
            lengths = self.get_diam_lengths(selected_sec)
            diams = [selected_sec.diam3d(i) for i in range(selected_sec.n3d())]
            # print('diams: ', diams)
            xs = [[lengths[i], lengths[i], lengths[i+1], lengths[i+1]] for i in range(len(lengths)-1)]
            # print('xs: ', xs)
            ys = [[0, diams[i], diams[i+1], 0] for i in range(len(diams) - 1)]
            # print('ys: ', ys)
            return {'xs': xs, 'ys': ys}
        logger.debug(f'There is {len(self.selected_secs)} selected sections')
        return {'xs': [], 'ys': []}

    def get_nsegs_data(self):
        if len(self.selected_secs) == 1:
            selected_sec = self.selected_sec
            x = (np.array([(2*i - 1) / (2 * selected_sec.nseg) for i in range(1, selected_sec.nseg + 1)])*selected_sec.L).tolist()
            y = [0] * selected_sec.nseg
            return {'x': x, 'y': y, 'marker': ['circle']*selected_sec.nseg}
        return {'x': [], 'y': [], 'marker': []}

    def get_param_data(self, param_name='diam'):
        # if param_name.startswith('gbar_') or param_name in ['cm', 'g_pas']:
        if len(self.selected_secs) == 1:
            selected_sec = self.selected_sec
            if param_name == 'area':
                yp = [seg.area() for seg in selected_sec]
            elif param_name == 'dist':
                yp = [self.model.cell.distance_from_soma(seg) for seg in selected_sec]
            elif param_name == '(unset)':
                yp = [0 for seg in selected_sec]
            elif param_name == 'voltage':
                yp = [0 for seg in selected_sec]
            else:
                yp = [getattr(seg, param_name) for seg in selected_sec]
            # print('yp: ', yp)
            x = (np.array([(2*i - 1) / (2 * selected_sec.nseg) for i in range(1, selected_sec.nseg + 1)])*selected_sec.L).tolist()
            # print('x: ', x)
            
            bar_width = [selected_sec.L / selected_sec.nseg] * selected_sec.nseg
            return {'x': x, 'y': yp, 'width': bar_width}
        return {'x': [], 'y': [], 'width': []}

    def get_seg_dist(self, sec, x=0.5):
        return h.distance(sec(x), self.cell.soma[0](0.5))

    def get_sec_dist(self):
        return [self.get_sec_dist(sec, x=0.5) for sec in self.cell.all]

    def get_seg_type(self, sec, x=0.5):
        return get_sec_type(sec)
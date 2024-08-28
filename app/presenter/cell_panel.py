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



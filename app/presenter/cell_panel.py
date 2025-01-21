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

    @property
    def selected_sec(self):
        return list(self.selected_secs)[0] if len(self.selected_secs) == 1 else None

    @property
    def xs(self):
        return [[pt.x for pt in sec.pts3d] for sec in self.model.sec_tree]

    @property
    def ys(self):
        return [[pt.y for pt in sec.pts3d] for sec in self.model.sec_tree]
            
    @property
    def colors(self):
        color_map = {k:v for k,v in zip(self.view.available_domains,
                                        self.view.theme.palettes['domain'])}
        return [color_map[sec.domain] for sec in self.model.sec_tree]
        
    @property
    def line_widths(self):
        """Returns the diameters as line_widths normalized to the range [1, 10]"""
        widths = np.array([np.mean(sec.radii) for sec in self.model.sec_tree])
        widths = 1 + (widths - np.min(widths)) * (9 / (np.max(widths) - np.min(widths)))
        widths *= 1.5
        widths = widths.tolist()
        return widths

    @property
    def labels(self):
        return [str(sec.idx) for sec in self.model.sec_tree]
        
    
    def _create_cell_renderer(self):
        """
        Create the cell renderer.
        """
        self.view.sources['cell'].data = self.get_cell_data()
        # self.view.sources['soma'].data = self.get_soma_data()

    def get_cell_data(self):
        return {'xs': self.xs, 
                'ys': self.ys, 
                'color': self.colors, 
                'line_width': self.line_widths, 
                'label': self.labels}

    def get_soma_data(self):
        x, y, z = self.model.sec_tree.soma_center
        return {'x': [x],
                'y': [y],
                'color': [self.view.theme.palettes['sec_type'][0]], 
                'rad': [self.model.sec_tree.soma._ref.diam / 2]}

    @log
    def update_cell_renderer_selection(self):
        """
        Update the selected sections in the cell renderer.
        """
        with remove_callbacks(self.view.figures['cell'].renderers[0].data_source.selected):
            sec_ids = [sec.idx for sec in self.selected_secs]
            indices = [i for i, sec in enumerate(self.model.sec_tree) if sec.idx in sec_ids]
            logger.debug(f'Sec ids: {sec_ids}')
            logger.debug(f'Indices: {indices}')
            self.view.figures['cell'].renderers[0].data_source.selected.indices = indices

    def rotate_cell_renderer_callback(self, attr, old, new):
        """
        Rotate the cell renderer around the XY axis. Attaches to the rotation slider.
        """
        self.model.swc_tree.rotate(new - old)
        self.view.sources['cell'].data = self.get_cell_data()

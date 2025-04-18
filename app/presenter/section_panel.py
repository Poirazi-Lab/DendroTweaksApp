import numpy as np
import pprint

from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

class SectionMixin():

    def __init__(self):
        logger.debug('SectionMixin init')
        super().__init__()

    # MODEL TO VIEW

    def update_section_panel(self):
        self.update_section_data()
        self.update_section_widgets()
        self.update_section_message()

    def update_section_data(self):
        self.update_section_nseg_data()
        self.update_section_diam_data()
        self.update_section_param_data()

    def update_section_nseg_data(self):
        self.view.sources['section_nseg'].data = self.get_nsegs_data()

    def get_nsegs_data(self):
        if len(self.selected_secs) == 1:
            selected_sec = self.selected_sec
            # x = (np.array([(2*i - 1) / (2 * selected_sec.nseg) for i in range(1, selected_sec.nseg + 1)])*selected_sec.L).tolist()
            x = selected_sec.seg_centers
            y = [0] * selected_sec.nseg
            return {'x': x, 'y': y, 'marker': ['circle']*selected_sec.nseg}
        return {'x': [], 'y': [], 'marker': []}

    def update_section_diam_data(self):
        sec_name = self.view.widgets.selectors['section'].value
        self.view.sources['section_diam'].data = self.get_radii_data()
        self.view.figures['section_diam'].title.text = f'{sec_name}: diam (points)'

    def get_radii_data(self):
        if len(self.selected_secs) == 1:
            
            selected_sec = self.selected_sec
            lengths = selected_sec.distances
            radii = selected_sec.radii
            
            xs = [[lengths[i], lengths[i], lengths[i+1], lengths[i+1]] for i in range(len(lengths)-1)]
            
            ys = [[0, radii[i], radii[i+1], 0] for i in range(len(radii) - 1)]
            
            return {'xs': xs, 'ys': ys}
            
        return {'xs': [], 'ys': []}

    # def get_diam_lengths(self, sec):
    #     x = np.diff([sec.x3d(i) for i in range(sec.n3d())])
    #     y = np.diff([sec.y3d(i) for i in range(sec.n3d())])
    #     z = np.diff([sec.z3d(i) for i in range(sec.n3d())])
    #     lengths = np.sqrt(x**2 + y**2 + z**2)
    #     levels = [0]
    #     for i in range(len(lengths)):
    #         levels.append(levels[i] + lengths[i])
    #     # print('levels: ', levels)
    #     return np.array(levels)

    def update_section_param_data(self, param_name: str = None) -> None:
        param_name = param_name or self.view.widgets.selectors['graph_param'].value
        if param_name in ['', 'domain', 'rec_v', 'AMPA', 'NMDA', 'GABAa', 'AMPA_NMDA', 'weights', 'iclamps']:
            param_name = 'diam'
        sec_name = self.view.widgets.selectors['section'].value
        self.view.sources['section_param'].data = self.get_param_data(param_name)
        self.view.figures['section_param'].title.text = f'{sec_name}: {param_name}'
        self.view.figures['section_param'].yaxis.axis_label = self.view.params.get(param_name)

    def get_param_data(self, param_name='diam'):
        # if param_name.startswith('gbar_') or param_name in ['cm', 'g_pas']:
        if len(self.selected_secs) == 1:
            selected_sec = self.selected_sec
            if param_name == 'distance':
                yp = [seg.path_distance() for seg in selected_sec.segments]
            elif param_name == 'domain_distance':
                yp = [seg.path_distance(within_domain=True) for seg in selected_sec.segments]
            elif param_name == 'subtree_size':
                yp = [seg.subtree_size for seg in selected_sec.segments]
            elif param_name == 'section_diam':
                yp = [seg._section.diam for seg in selected_sec.segments]
            elif param_name == 'Ra':
                yp = [seg.Ra for seg in selected_sec.segments]
            elif param_name == 'area':
                yp = [seg._ref.area() for seg in selected_sec.segments]
            elif param_name == 'voltage':
                yp = [0 for seg in selected_sec]
            else:
                if hasattr(selected_sec._ref, param_name):
                    yp = [seg.get_param_value(param_name) for seg in selected_sec.segments]
                else:
                    yp = [0 for seg in selected_sec]
            
            x = selected_sec.seg_centers
            
            bar_width = [selected_sec._ref.L / selected_sec._ref.nseg] * selected_sec._ref.nseg
            return {'x': x, 'y': yp, 'width': bar_width}
        return {'x': [], 'y': [], 'width': []}

    def update_section_widgets(self):

        self.update_sec_selector()
        self.update_seg_x_selector()

        if len(self.selected_secs) == 1:
            if list(self.selected_secs)[0].parent is None:
                self.view.widgets.spinners['nseg'].visible = False
            else:
                self.view.widgets.spinners['nseg'].visible = True
            with remove_callbacks(self.view.widgets.spinners['nseg']):
                self.view.widgets.spinners['nseg'].value = self.selected_sec.nseg

        self.update_navigation_buttons_on_reaching_terminal_branch()

    def update_sec_selector(self):
        with remove_callbacks(self.view.widgets.selectors['section']):
            if len(self.selected_secs) == 1:
                    self.view.widgets.selectors['section'].value = str(self.selected_sec.idx)
            else:
                self.view.widgets.selectors['section'].value = ''

    def update_seg_x_selector(self):
        with remove_callbacks(self.view.widgets.selectors['seg_x']):
            if len(self.selected_secs) == 1:
                self.view.widgets.selectors['seg_x'].options = [str(round(seg.x, 5)) for seg in self.selected_segs[0]._section]
                self.view.widgets.selectors['seg_x'].value = str(round(self.selected_segs[0].x, 5))
            else:
                self.view.widgets.selectors['seg_x'].options = ['']
                self.view.widgets.selectors['seg_x'].value = ''
            
        logger.debug('END\n')

    def update_navigation_buttons_on_reaching_terminal_branch(self):
        """
        Update navigation buttons when reaching leaf or root sections
        """

        if len(self.selected_secs) == 1:

            if self.selected_sec.children:
                self.view.widgets.buttons['child'].disabled = False
            else:
                self.view.widgets.buttons['child'].disabled = True

            if self.selected_sec.parent is None:
                self.view.widgets.buttons['parent'].disabled = True
                self.view.widgets.buttons['sibling'].disabled = True
            else:
                self.view.widgets.buttons['parent'].disabled = False
                self.view.widgets.buttons['sibling'].disabled = False
        else:
            self.view.widgets.buttons['child'].disabled = True
            self.view.widgets.buttons['parent'].disabled = True
            self.view.widgets.buttons['sibling'].disabled = True

    def update_section_message(self):
        if len(self.selected_secs) == 1:
            preformatted_string = pprint.pformat(self.selected_sec._ref.psection(), 
                                                    indent=4,
                                                    sort_dicts=False)
            spoiler = f'<details><summary>Toggle psection</summary><pre style="font-size:x-small">{preformatted_string}</pre></details>'
            self.view.DOM_elements['psection'].text = spoiler
        elif len(self.selected_secs) > 1:
            self.view.DOM_elements['psection'].text = 'More than one section selected'
        else:
            self.view.DOM_elements['psection'].text = 'No section selected'
        

    # def get_seg_dist(self, sec, x=0.5):
    #     return h.distance(sec(x), self.cell.soma[0](0.5))

    # def get_sec_dist(self):
    #     return [self.get_sec_dist(sec, x=0.5) for sec in self.cell.all]

    # def get_seg_type(self, sec, x=0.5):
    #     return get_sec_type(sec)

    
    # VIEW TO MODEL

    def nseg_callback(self, attr, old, new):
        if new is None: return
        if not self.selected_secs: 
            logger.debug('No section selected')
            return
        selected_secs = self.selected_secs
        for sec in selected_secs:
            sec.nseg = new
            
        self._create_graph_renderer()
        self.update_section_panel()

    def length_callback(self, attr, old, new):
        logger.debug('Not implemented yet...')
        # for sec in self.selected_secs:
        #     sec.L = new
        # self.update_cell_renderer()
        # self.update_section_panel()

    def update_plots_on_param_change_callback(self, event):
        logger.debug('Not implemented yet...')


   
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
        self.update_status_message()

    def update_section_data(self):
        self.update_section_nseg_data()
        self.update_section_diam_data()
        self.update_section_param_data()

    def update_section_nseg_data(self):
        self.view.sources['section_nseg'].data = self.get_nsegs_data()

    def get_nsegs_data(self):
        if len(self.selected_secs) == 1:
            selected_sec = self.selected_sec
            x = (np.array([(2*i - 1) / (2 * selected_sec.nseg) for i in range(1, selected_sec.nseg + 1)])*selected_sec.L).tolist()
            y = [0] * selected_sec.nseg
            return {'x': x, 'y': y, 'marker': ['circle']*selected_sec.nseg}
        return {'x': [], 'y': [], 'marker': []}

    def update_section_diam_data(self):
        sec_name = self.view.widgets.selectors['section'].value
        self.view.sources['section_diam'].data = self.get_diams_data()
        self.view.figures['section_diam'].title.text = f'{sec_name}: diam (pts3d)'

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

    def update_section_param_data(self):
        param_name = self.view.widgets.selectors['graph_param'].value
        if param_name in ['type', 'Ra', 'recordings', 'AMPA', 'NMDA', 'GABAa', 'AMPA_NMDA', 'weights', 'iclamps']:
            param_name = 'diam'
        sec_name = self.view.widgets.selectors['section'].value
        self.view.sources['section_param'].data = self.get_param_data(param_name)
        self.view.figures['section_param'].title.text = f'{sec_name}: {param_name}'
        self.view.figures['section_param'].yaxis.axis_label = self.view.params.get(param_name)

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
            spoiler = f'<div style="height: 200px; overflow: auto;"><details><summary>Toggle psection</summary><pre>{preformatted_string}</pre></details></div>'
            self.view.DOM_elements['status_bar'].text = spoiler
        elif len(self.selected_secs) > 1:
            self.view.DOM_elements['status_bar'].text = 'More than one section selected'
        else:
            self.view.DOM_elements['status_bar'].text = 'No section selected'
        

    # def get_seg_dist(self, sec, x=0.5):
    #     return h.distance(sec(x), self.cell.soma[0](0.5))

    # def get_sec_dist(self):
    #     return [self.get_sec_dist(sec, x=0.5) for sec in self.cell.all]

    # def get_seg_type(self, sec, x=0.5):
    #     return get_sec_type(sec)

    
    # VIEW TO MODEL

    def nseg_callback(self, attr, old, new):
        del self.model.cell.segments
        selected_secs = self.selected_secs
        self.view.widgets.selectors['section'].value = ''
        for sec in selected_secs:
            sec.nseg = new
        self.create_graph_renderer()
        self.add_lasso_callback()
        self.update_section_panel()

    def length_callback(self, attr, old, new):
        logger.debug('Not implemented yet...')
        # for sec in self.selected_secs:
        #     sec.L = new
        # self.update_cell_renderer()
        # self.update_section_panel()

    def update_plots_on_param_change_callback(self, event):
        logger.debug('Not implemented yet...')


   
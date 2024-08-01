import re
import random

from bokeh_utils import remove_callbacks
from bokeh_utils import log
from logger import logger

from utils import get_seg_name, get_sec_type, get_sec_name, get_sec_id

from bokeh.models import LassoSelectTool

class NavigationMixin(): 

    def __init__(self):
        logger.debug('NavigationMixin init')
        super().__init__()   

    @log
    def add_lasso_callback(self):

        graph_lasso_tool = self.view.figures['graph'].select(type=LassoSelectTool)
        graph_lasso_tool.renderers = [self.view.figures['graph'].renderers[0].node_renderer]

        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.on_change('indices', self.graph_lasso_callback)

        self.view.figures['graph'].toolbar.active_drag = graph_lasso_tool[0]

    @log
    def graph_lasso_callback(self, attr, old, new):

        # update selected segments
        self.update_selected_segments(old, new)

        # update cell selection
        self.update_cell_panel()
        
        self.update_section_panel()
        
        # update switches
        self.update_iclamp_switch()
        self.update_record_switch()

        if self.view.widgets.tabs['section'].visible:
            if self.view.widgets.tabs['section'].active == 1:
                self.update_distribution_plot()

    @log
    def update_selected_segments(self, old, new):
        old_set = set(old)
        new_set = set(new)
        add_set = new_set - old_set
        remove_set = old_set - new_set

        data = self.view.figures['graph'].renderers[0].node_renderer.data_source.data['name']
        seg_names_to_add = [data[i] for i in add_set]
        seg_names_to_remove = [data[i] for i in remove_set]

        if seg_names_to_remove:
            self.remove_segments(seg_names_to_remove)
        if seg_names_to_add:
            self.add_segments(seg_names_to_add)

        

    def add_segments(self, seg_names):
        self.selected_segs += [self.model.cell.sections[re.split(r'\(|\)', seg_name)[0]](float(re.split(r'\(|\)', seg_name)[1])) for seg_name in seg_names]
        self.selected_secs.update({self.model.cell.sections[re.split(r'\(|\)', seg_name)[0]] for seg_name in seg_names})

    def remove_segments(self, seg_names):
        self.selected_segs = [seg for seg in self.selected_segs if get_seg_name(seg) not in seg_names]
        self.selected_secs = set([seg.sec for seg in self.selected_segs])

    def clear_segments(self):
        self.selected_secs = set()
        self.selected_segs = []

    @log
    def cell_tap_callback(self, attr, old, new):
        
        if new:
            logger.debug(f'New: {new}')
            # sec_name = self.labels[new[0]]
            sec_names = [self.labels[i] for i in new]
            logger.debug(f'Sec name: {sec_names}')
            # sec = self.model.cell.sections[sec_name]
            secs = [self.model.cell.sections[sec_name] for sec_name in sec_names]
            # seg_names = [get_seg_name(seg)for seg in sec]
            seg_names = [get_seg_name(seg) for sec in secs for seg in sec]
        else: 
            seg_names = []

        self.select_seg_x(seg_names)

        with remove_callbacks(self.view.widgets.selectors['section']):
            self.view.widgets.selectors['section'].value = sec_names[0] if new else ''


    def select_seg_x(self, seg_names):
        """
        When a segment is selected from a dropdown menu (as opposite to tap or lasso selection), 
        update the graph selection. Setting the selection will trigger the graph selection callback
        """

        logger.debug(f'Selecting segments: {seg_names}')    
        indices = [i for i, name in enumerate(self.view.figures['graph'].renderers[0].node_renderer.data_source.data['name']) if name in seg_names]
        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = indices
        

    def select_seg_x_callback(self, attr, old, new):

        seg_names = [self.view.widgets.selectors['section'].value + '(' + self.view.widgets.selectors['seg_x'].value + ')']
        self.select_seg_x(seg_names)


    def select_section_callback(self, attr, old, new):
        
        sec_name = self.view.widgets.selectors['section'].value        
        indices = [i for i, lbl in enumerate(self.labels) if lbl == sec_name]
        self.view.figures['cell'].renderers[0].data_source.selected.indices = indices

    def select_type_callback(self, attr, old, new):
        logger.debug(f'New type: {new}')
        logger.debug(f'Labels: {self.labels}')
        logger.debug(f'Sections:{self.model.cell.sections.keys()}')
        logger.debug(f'Cell: {[get_sec_type(self.model.cell.sections[lbl]) for lbl in self.labels]}')
        indices = [i for i, lbl in enumerate(self.labels) if get_sec_type(self.model.cell.sections[lbl]) in new]
        logger.debug(f'Indices: {indices}')
        self.view.figures['cell'].renderers[0].data_source.selected.indices = indices

    def button_child_callback(self, event):
        """
        Selects a child by updating the section selector
        """
        children = self.selected_sec.children()
        try:
            child_name = get_sec_name(children[1])
        except IndexError:
            child_name = get_sec_name(children[0])
        self.view.widgets.selectors['section'].value = child_name
            

    def button_parent_callback(self, event):
        """
        Selects a parent by updating the section selector
        """
        parent = self.selected_sec.parentseg().sec
        parent_name = get_sec_name(parent)
        self.view.widgets.selectors['section'].value = parent_name


    def button_sibling_callback(self, event):
        sigblings = [sec for sec in self.selected_sec.parentseg().sec.children() if sec != self.selected_sec]
        logger.debug(f"Sigblings of {get_sec_name(self.selected_sec)}: {sigblings}")
        if len(sigblings) == 1:
            sigbling_name = get_sec_name(sigblings[0])
        elif len(sigblings) > 1:
            sigbling_name = get_sec_name(random.choice(sigblings))
        else:
            sigbling_name = get_sec_name(self.selected_sec)
            logger.warning('No sigblings found, returning to current section')

        self.view.widgets.selectors['section'].value = sigbling_name

    @log
    def update_record_switch(self):
        if len(self.selected_segs) == 1:
            with remove_callbacks(self.view.widgets.switches['record']):
                self.view.widgets.switches['record'].disabled = False
                seg = self.selected_segs[0]               
                self.view.widgets.switches['record'].active = seg in self.recorded_segments# self.model.simulator.recordings.get(seg) is not None
        else:
            with remove_callbacks(self.view.widgets.switches['record']):
                self.view.widgets.switches['record'].active = False
                self.view.widgets.switches['record'].disabled = True

    @log
    def update_iclamp_switch(self):
        if len(self.selected_segs) == 1:
            self.view.widgets.switches['iclamp'].disabled = False
            seg = self.selected_segs[0]
            with remove_callbacks(self.view.widgets.switches['iclamp']):
                self.view.widgets.switches['iclamp'].active = bool(self.model.iclamps.get(seg))
                if self.view.widgets.switches['iclamp'].active:
                    self.view.widgets.sliders['iclamp_amp'].visible = True
                    logger.debug(f'Amplitude: {self.model.iclamps[seg].amp}')
                    self.view.widgets.sliders['iclamp_amp'].value = self.model.iclamps[seg].amp
                    
                    self.view.widgets.sliders['iclamp_duration'].visible = True
                    self.view.widgets.sliders['iclamp_duration'].value = [self.model.iclamps[seg].delay, self.model.iclamps[seg].delay + self.model.iclamps[seg].dur]
                else:
                    self.view.widgets.sliders['iclamp_amp'].visible = False
                    self.view.widgets.sliders['iclamp_duration'].visible = False
        else:
            with remove_callbacks(self.view.widgets.switches['iclamp']):
                self.view.widgets.sliders['iclamp_amp'].visible = False
                self.view.widgets.sliders['iclamp_duration'].visible = False
                self.view.widgets.switches['iclamp'].active = False
                self.view.widgets.switches['iclamp'].disabled = True

    def remove_all_callback(self, event):
        self.view.widgets.switches['record'].active = False
        self.view.widgets.switches['iclamp'].active = False
        self.recorded_segments = []
        self.model.simulator.remove_all_recordings()
        self.model.remove_all_iclamps()
        self.model.remove_all_synapses()
        self.view.DOM_elements['syn_group_panel'].children = []
        self.update_graph_param('iclamps')
        self.update_graph_param('recordings')
        for name in self.model.synapses:
            self.update_graph_param(name)
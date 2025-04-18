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
        self.update_cell_renderer_selection()
        
        self.update_section_panel()
        
        # update switches
        self.update_iclamp_switch()
        self.update_record_switch()

        if self.view.widgets.buttons['switch_right_menu'].active == 1:
            if self.view.widgets.tabs['biophys'].active == 2:
                logger.debug('Updating distribution plot')
                self._update_distribution_plot()
        

    @log
    def update_selected_segments(self, old, new):
        old_set = set(old)
        new_set = set(new)
        add_set = new_set - old_set
        remove_set = old_set - new_set

        indices = self.view.figures['graph'].renderers[0].node_renderer.data_source.data['index']
        seg_ids_to_add = [indices[i] for i in add_set]
        logger.debug(f'Add set: {add_set}')
        logger.debug(f'Seg ids to add: {seg_ids_to_add}')
        seg_ids_to_remove = [indices[i] for i in remove_set]

        if seg_ids_to_remove:
            self.remove_segments(seg_ids_to_remove)
        if seg_ids_to_add:
            self.add_segments(seg_ids_to_add)
        

    def add_segments(self, seg_ids):
        self.selected_segs += [self.model.seg_tree[seg_id] for seg_id in seg_ids]
        self.selected_secs = set([seg._section for seg in self.selected_segs])

    def remove_segments(self, seg_ids):
        self.selected_segs = [seg for seg in self.selected_segs if seg.idx not in seg_ids]
        self.selected_secs = set([seg._section for seg in self.selected_segs])


    @log
    def cell_tap_callback(self, attr, old, new):
        
        logger.debug(f'Cell tap callback: {new}')
        
        if new:
            # secs = [sec for sec in self.model.sec_tree if sec.idx in new]
            secs = [self.model.sec_tree[sec_id] for sec_id in new]
            logger.debug(f'Secs: {secs}')
            seg_ids = [seg.idx for sec in secs for seg in sec.segments]
        else: 
            secs = []
            seg_ids = []

        self.select_seg_x(seg_ids)

        with remove_callbacks(self.view.widgets.selectors['section']):
            self.view.widgets.selectors['section'].value = str(secs[0].idx) if secs else ''

    @log
    def select_seg_x(self, seg_ids):
        """
        When a segment is selected from a dropdown menu (as opposite to tap or lasso selection), 
        update the graph selection. Setting the selection will trigger the graph selection callback
        """
        # self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = seg_ids
        indices = self.view.figures['graph'].renderers[0].node_renderer.data_source.data['index']
        filtered_indices = [
            i for i, index in enumerate(indices) 
            if index in seg_ids]
        logger.debug(f'Indices: {seg_ids}') 
        logger.debug(f'Filtered indices: {filtered_indices}')
        self.view.figures['graph'].renderers[0].node_renderer.data_source.selected.indices = filtered_indices
        

    def select_seg_x_callback(self, attr, old, new):

        seg_ids = [sec(float(new)).idx for sec in self.selected_secs]
        self.select_seg_x(seg_ids)

    @log
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
        children = self.selected_sec.children
        try:
            child = children[1]
        except IndexError:
            child = children[0]
        self.view.widgets.selectors['section'].value = str(child.idx)
            

    def button_parent_callback(self, event):
        """
        Selects a parent by updating the section selector
        """
        parent = self.selected_sec.parent
        self.view.widgets.selectors['section'].value = str(parent.idx)


    def button_sibling_callback(self, event):
        sigblings = [sec for sec in self.selected_sec.parent.children if sec != self.selected_sec]

        if len(sigblings) == 1:
            sigbling = sigblings[0]
        elif len(sigblings) > 1:
            sigbling = random.choice(sigblings)
        else:
            sigbling = self.selected_sec
            logger.warning('No sigblings found, returning to current section')

        self.view.widgets.selectors['section'].value = str(sigbling.idx)

    def recording_variable_callback(self, attr, old, new):
        """ Callback for the recording variable selector. """
        self.update_record_switch()
        self.view.widgets.selectors['graph_param'].value = f'rec_{new}'

    @log
    def update_record_switch(self):
        if len(self.selected_segs) == 1:
            with remove_callbacks(self.view.widgets.switches['record']):
                var = self.view.widgets.selectors['recording_variable'].value
                self.view.widgets.switches['record'].disabled = False
                seg = self.selected_segs[0]
                self.view.widgets.switches['record'].active = seg in self.model.recordings.get(var, [])
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
                    self.view.widgets.sliders['iclamp_amp'].value = self.model.iclamps[seg].amp * 1e3 # convert to pA
                    
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


    def remove_all_iclamps_callback(self, event):
        self.model.remove_all_iclamps()
        self.update_iclamp_switch()
        self._update_graph_param('iclamps')

    def remove_all_recordings_callback(self, event):
        var = self.view.widgets.selectors['recording_variable'].value
        self.model.simulator.remove_all_recordings(var=var)
        self.update_record_switch()
        self._update_graph_param('v')

    def remove_all_populations_callback(self, event):
        self.model.remove_all_populations()
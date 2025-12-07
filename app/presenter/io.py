# SPDX-FileCopyrightText: 2025 Poirazi Lab <dendrotweaks@dendrites.gr>
# SPDX-License-Identifier: MPL-2.0

from logger import logger
from bokeh_utils import remove_callbacks
from bokeh_utils import log

# from model.mechanisms.distributions import Distribution

from bokeh.models.callbacks import CustomJS

import dendrotweaks as dd

import os
import json

class IOMixin():

    def __init__(self):
        logger.debug('IOMixin init')
        super().__init__()

    def list_models(self):
        path_to_data = self.path_to_data
        return [f for f in os.listdir(path_to_data) if os.path.isdir(os.path.join(path_to_data, f)) and f not in ['Default', 'Templates']]

    # =========================================================================
    # INPUT METHODS
    # =========================================================================

    def select_model_callback(self, attr, old, new):
        """
        Callback for the selectors['model'] widget.
        """
        path_to_model = os.path.join(self.path_to_data, new)
        self.model = dd.Model(path_to_model=path_to_model, simulator_name=self._simulator)

        self.view.widgets.selectors['model'].options = self.list_models()
        morphologies = self.model.path_manager.list_morphologies()
        self.view.widgets.selectors['morphology'].options = ['Select a morphology'] + morphologies
        biophys = self.model.path_manager.list_biophys()
        self.view.widgets.selectors['biophys'].options = ['Select biophys'] + biophys
        stimuli = self.model.path_manager.list_stimuli()
        self.view.widgets.selectors['stimuli'].options = ['Select stimuli'] + stimuli

        self.view.widgets.multichoice['mechanisms'].options = self.model.list_mechanisms()
        
        if self.config['dev_tools']['allow_file_io']:
            self.view.widgets.text['file_name'].value = self.model.name + '_modified'
        self.view.widgets.selectors['model'].disabled = True
        self.view.widgets.switches['cvode'].disabled = False

        self._attach_download_js()

        self.view.DOM_elements['status'].text = 'Select morphology, membrane mechanisms, and stimuli.'
        

        
    def load_biophys_callback(self, attr, old, new):
        """
        Callback for the selectors['biophys'] widget.
        """
        if self.model.sec_tree is None:
            with remove_callbacks(self.view.widgets.selectors['biophys']):
                self.view.widgets.selectors['biophys'].value = 'Select biophys'
            self.update_status_message('Please load a morphology first.', status='warning')
            return

        try:
            self.model.load_biophys(new, recompile=self.view.widgets.switches['recompile'].active)
        except Exception as e:
            logger.error(f'Error loading biophys: {e}')
            with remove_callbacks(self.view.widgets.selectors['biophys']):
                self.view.widgets.selectors['biophys'].value = 'Select biophys'
            self.update_status_message('Error loading biophys.', status='error')
            return

        d_lambda = self.model.d_lambda
        with remove_callbacks(self.view.widgets.sliders['d_lambda']):
            self.view.widgets.sliders['d_lambda'].value = d_lambda 
        self.build_seg_tree(d_lambda)
        self._update_group_selector_widget()
        self._update_graph_param_widget()

        # TODO: Maybe the following is not necessary, see above
        for param_name in self.model.params:
            self._update_graph_param(param_name, update_colors=False)

        self._update_mechs_to_insert_widget()
        self._update_multichoice_domain_widget()
        self._update_multichoice_mechanisms_widget()
        self._update_mechanism_selector_widget('Independent')
        self._update_recording_variable_selector_widget()
        

        self.view.widgets.buttons['add_default_mechanisms'].disabled = True
        self.view.widgets.selectors['biophys'].options = self.model.list_biophys()

        self.update_status_message('Biophysical configuration loaded.', status='success')
        
        

    def load_stimuli_callback(self, attr, old, new):
        """
        Callback for the selectors['stimuli'] widget.
        """
        if self.model.sec_tree is None:
            with remove_callbacks(self.view.widgets.selectors['stimuli']):
                self.view.widgets.selectors['stimuli'].value = 'Select stimuli'
            self.update_status_message('Please load a morphology first.', status='warning')
            return

        try:
            self.model.load_stimuli(new)
            logger.debug(f'Recordings loaded: {self.model.recordings}')
        except Exception as e:
            logger.error(f'Error loading stimuli: {e}')
            with remove_callbacks(self.view.widgets.selectors['stimuli']):
                self.view.widgets.selectors['stimuli'].value = 'Select stimuli'
            self.update_status_message('Error loading stimuli.', status='error')
            return

        self.update_simulation_widgets()

        # MISC --------------------------------------------------------
        # self._attach_download_js() # needed to update the names of the files to download

        self._recorded_segments = self.get_recorded_segments()
        self._update_traces_renderers()        
        self.update_voltage()

        # UPDATE GRAPH PARAM ----------------------------------------------
        self.view.params.update({'Synapses': list(self.model.populations.keys())})
        self.view.widgets.selectors['graph_param'].options = {**self.view.params}

        for param_name in ['iclamps', 'rec_v'] + list(self.model.populations.keys()):
            self._update_graph_param(param_name, update_colors=False)

        # UPDATE POPULATION OPTIONS ----------------------------------------
        with remove_callbacks(self.view.widgets.selectors['population']):
            options = list(self.model.populations.keys())
            self.view.widgets.selectors['population'].options = options

        # UPDATE STIMULI OPTIONS ------------------------------------------------
        self.view.widgets.selectors['stimuli'].options = self.model.list_stimuli()
        self.update_status_message('Stimuli loaded.', status='success')
        

    def update_simulation_widgets(self):
        """
        Updates the simulation panel based on the loaded stimuli.
        """
        with remove_callbacks(self.view.widgets.sliders['duration']):
            self.view.widgets.sliders['duration'].value = self.model.simulator._duration
        with remove_callbacks(self.view.widgets.sliders['dt']):
            self.view.widgets.sliders['dt'].value = self.model.simulator.dt
        with remove_callbacks(self.view.widgets.sliders['temperature']):
            self.view.widgets.sliders['temperature'].value = self.model.simulator.temperature
        with remove_callbacks(self.view.widgets.sliders['v_init']):
            self.view.widgets.sliders['v_init'].value = self.model.simulator.v_init
        


    # =========================================================================
    # MORPHOLOGY
    # =========================================================================


    def load_morphology_callback(self, attr, old, new):
        """
        Creates the cell and the renderers.
        """
        try:     
            self.load_morphology(new)
        except Exception as e:
            logger.error(f'Error loading morphology: {e}')
            with remove_callbacks(self.view.widgets.selectors['morphology']):
                self.view.widgets.selectors['morphology'].value = 'Select a morphology'
            self.update_status_message('Error loading morphology.', status='error')
            return

        self.view.layout_elements['workspace'].visible = True
        self.view.layout_elements['right_menu'].visible = True
        self.update_status_message('Morphology loaded.', status='success')
        


    @log
    def load_morphology(self, file_name):
        """
        Creates the cell and the renderers.
        """

        # MORPHOLOGY --------------------------------------------
        
        self.model.load_morphology(file_name)

        self._create_cell_renderer()
        self._init_cell_widgets()

        # LOAD MECHANISMS -----------------------------------------
        # self.model.add_default_mechanisms()
        # self._update_mechs_to_insert_widget()
     
        
        # GRAPH ------ --------------------------------------------
        self._create_graph_renderer()
        self._update_group_selector_widget()
        self._update_graph_param_widget()
        self._update_mechanism_selector_widget('Independent')
        
        
        # MISC ---------------------------------------------------
        # self._attach_download_js()

        self.view.widgets.multichoice['domains'].options = list(self.model.domains.keys())
        self.view.widgets.multichoice['group_domains'].options = list(self.model.domains.keys())
        self.view.widgets.selectors['morphology'].options = self.model.list_morphologies()
        


    def _init_cell_widgets(self):
        """
        Configures the widgets after the cell is loaded.
        """
        domains_to_sec_ids = {domain.name: sorted([str(sec.idx) for sec in domain.sections], key=lambda x: int(x)) 
                             for domain in self.model.domains.values()}
        self.view.widgets.selectors['section'].options = domains_to_sec_ids

        with remove_callbacks(self.view.widgets.selectors['domain']):
            available_domains = list(self.model.domains.keys())
            self.view.widgets.selectors['domain'].options = available_domains
            self.view.widgets.selectors['domain'].value = available_domains[0]

        self.view.widgets.buttons['child'].disabled = False
        self.view.widgets.buttons['parent'].disabled = True
        self.view.widgets.buttons['sibling'].disabled = True

    def _update_mechs_to_insert_widget(self):
        available_mechs = list(self.model.mechanisms.keys())
        with remove_callbacks(self.view.widgets.selectors['mechanism_to_insert']):
            self.view.widgets.selectors['mechanism_to_insert'].options = available_mechs
            self.view.widgets.selectors['mechanism_to_insert'].value = available_mechs[0]


    # =========================================================================
    # MECHANISMS
    # =========================================================================

    def add_mechanism_callback(self, attr, old, new):
        """
        """
        recompile = self.view.widgets.switches['recompile'].active

        mechs_to_add = list(set(new).difference(set(old)))
        mechs_to_remove = list(set(old).difference(set(new)))
        
        if mechs_to_add:
            mech_name = mechs_to_add[0]
            self.model.add_mechanism(mech_name, load=True, recompile=recompile)
            self.update_status_message(f'Mechanism "{mech_name}" added.', status='success')
        if mechs_to_remove:
            self.update_status_message(f'Mechanisms cannot be removed from NEURON.', status='warning')
            with remove_callbacks(self.view.widgets.multichoice['mechanisms']):
                self.view.widgets.multichoice['mechanisms'].value = old
            return

        self._update_mechs_to_insert_widget()
        self._update_multichoice_domain_widget()

        


    def add_default_mechanisms_callback(self, event):
        """
        Creates the cell and the renderers.
        """     
        recompile = self.view.widgets.switches['recompile'].active
        self.model.add_default_mechanisms(recompile=recompile)

        self.view.widgets.buttons['add_default_mechanisms'].disabled = True

        self._update_mechs_to_insert_widget()
        self._update_multichoice_domain_widget()

        self.update_status_message('Default mechanisms added.', status='success')


    # -------------------------------------------------------------------------
    # SEGMENTATION
    # -------------------------------------------------------------------------

    @log
    def build_seg_tree_callback(self, event):

        d_lambda = self.view.widgets.sliders['d_lambda'].value
        self.build_seg_tree(d_lambda)
        self._recorded_segments = self.get_recorded_segments()
        self._update_traces_renderers()
        self.update_status_message(f'Segmentation resulted in {len(self.model.seg_tree)} segments.', status='success')
        
    @log
    def build_seg_tree(self, d_lambda):
        """
        Updates the segmentation based on the current d_lambda
        and builds the seg tree.
        """
        # if not 'cm' in self.model.parameters_to_groups:
        #     raise ValueError('Capacitance is not set for any group.')
        logger.info(f'Aimed for {1/d_lambda} segments per length constant at {100} Hz')
        self.model.set_segmentation(d_lambda=d_lambda, f=100)
        logger.info(f'Total nseg: {len(self.model.seg_tree)}')

        self._create_graph_renderer()
        

    def _update_group_selector_widget(self):
        with remove_callbacks(self.view.widgets.selectors['group']):
            self.view.widgets.selectors['group'].options = list(self.model.groups.keys())
            self.view.widgets.selectors['group'].value = 'all'

    def _update_graph_param_widget(self):
        with remove_callbacks(self.view.widgets.selectors['graph_param']):
            self.view.widgets.selectors['graph_param'].value = 'domain'


    # =========================================================================
    # FILE IMPORT
    # =========================================================================

    def import_file_callback(self, attr, old, new):
        import base64
        import os
        import io

        if attr == 'value':
            self.view._file_content = base64.b64decode(new)
        elif attr == 'filename':
            self.view._filename = new

        if self.view._file_content is not None and self.view._filename is not None:

            file_content = self.view._file_content
            self.view._file_content = None
            filename = self.view._filename
            self.view._filename = None

            logger.info(f'Importing file {filename}')

            if filename.endswith('.swc') or filename.endswith('.asc'):
                with open(f'app/model/swc/{filename}', 'wb') as file:
                    file.write(file_content)
                logger.info(f'File {filename} saved to app/model/swc')
                self.view.widgets.selectors['swc'].options = [f for f in os.listdir('app/model/swc') if f.endswith('.swc') or f.endswith('.asc')]

            elif filename.endswith('.mod'):
                mod_folder = 'mod_cadyn' if 'cadyn' in filename else 'mod'
                widget_name = 'mod_files_cadyn' if 'cadyn' in filename else 'mod_files'
                os.makedirs(f'app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}', exist_ok=True)
                with open(f'app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}/{filename}', 'wb') as file:
                    file.write(file_content)
                logger.info(f'File {filename} saved to app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}')
                self.view.widgets.multichoice[widget_name].options = self.model.list_mod_files(mod_folder=mod_folder)

    # =========================================================================
    # EXPORT METHODS
    # =========================================================================

    @log
    def export_model_callback(self, event):        
        file_name = self.view.widgets.text['file_name'].value
        if file_name == '':
            self.update_status_message('Please provide a file name.', status='warning')
            return
        if file_name == self.model.name:
            self.update_status_message('Cannot overwrite the original model.', status='warning')
            return
        if event.item == 'morphology':
            self.model.export_morphology(file_name)
            self.update_status_message('Morphology exported.', status='success')
        elif event.item == 'biophys':
            self.model.export_biophys(file_name)
            self.update_status_message('Biophys exported.', status='success')
        elif event.item == 'stimuli':
            self.model.export_stimuli(file_name)
            self.update_status_message('Stimuli exported.', status='success')

    def download_model_callback(self, event):
        """
        """
        pass
        self.update_status_message('Downloaded.', status='success')

    # MISC

    def _attach_download_js(self):
        """
        Attaches a JS callback to the download buttons.
        A workaround for the inability to download files from bokeh.
        """

        def attach_download_js(button, file_path):

            js_code = f"""
            var filename = '{file_path}';
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/' + filename, true);  // Ensure the path is absolute
            xhr.responseType = 'blob';
            xhr.onload = function(e) {{
                if (this.status == 200) {{
                    var blob = this.response;
                    var link = document.createElement('a');
                    link.href = window.URL.createObjectURL(blob);
                    link.download = filename.split('/').pop();
                    link.click();
                }} else {{
                    console.error('Failed to download file:', filename);
                }}
            }};
            xhr.onerror = function() {{
                console.error('Error occurred while trying to download:', filename);
            }};
            xhr.send();
            console.log('Download initiated for', filename);
            """
            
            button.js_on_event('button_click', CustomJS(code=js_code))

        if self.config['dev_tools']['allow_file_io']:
            attach_download_js(self.view.widgets.buttons['download_model'], 
                            f'app/static/data/{self.model.name}/{self.model.name}.zip')
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

    # =========================================================================
    # INPUT METHODS
    # =========================================================================

    def select_model_callback(self, attr, old, new):
        """
        Callback for the selectors['model'] widget.
        """
        self.model.name = new
        self.view.widgets.selectors['model'].options = self.model.path_manager.list_models()
        morphologies = self.model.path_manager.list_morphologies()
        self.view.widgets.selectors['morphology'].options = ['Select a morphology'] + morphologies
        membrane = self.model.path_manager.list_membrane()
        self.view.widgets.selectors['membrane'].options = ['Select a membrane'] + membrane
        stimuli = self.model.path_manager.list_stimuli()
        self.view.widgets.selectors['stimuli'].options = ['Select a stimuli'] + stimuli
        
        self.view.DOM_elements['status'].text = 'Select morphology, membrane mechanisms, and stimuli.'
        

        
    def load_membrane_callback(self, attr, old, new):
        """
        Callback for the selectors['membrane'] widget.
        """
        self.model.load_membrane(new, recompile=self.view.widgets.switches['recompile'].active)
        d_lambda = self.model.d_lambda
        with remove_callbacks(self.view.widgets.sliders['d_lambda']):
            self.view.widgets.sliders['d_lambda'].value = d_lambda 
        self.build_seg_tree(d_lambda)

        # TODO: Maybe the following is not necessary, see above
        for param_name in self.model.params:
            self._update_graph_param(param_name, update_colors=False)

        self._update_mechs_to_insert_widget()
        self._update_multichoice_domain_widget()

        self.view.DOM_elements['status'].text = 'Membrane loaded.'
        

    def load_stimuli_callback(self, attr, old, new):
        """
        Callback for the selectors['stimuli'] widget.
        """
        self.model.load_stimuli(new)
        self.update_simulation_widgets()

        # MISC --------------------------------------------------------
        self._attach_download_js() # needed to update the names of the files to download

        self.recorded_segments = [seg for seg in self.model.recordings]
        self.update_voltage()

        for param_name in ['AMPA', 'NMDA', 'GABAa', 'AMPA_NMDA', 'recordings', 'iclamps']:
            self._update_graph_param(param_name, update_colors=False)

        self.view.DOM_elements['status'].text = 'Stimuli loaded.'

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
        self.load_morphology(new)

        self.view.widgets.text['model_version'].value = self.model.name
        self.view.DOM_elements['status'].text = 'Morphology loaded.'


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
     
        
        # SEGMENTATION --------------------------------------------
        d_lambda = self.view.widgets.sliders['d_lambda'].value
        self.build_seg_tree(d_lambda)
        # self._update_group_selector_widget()
        
        
        # MISC ---------------------------------------------------
        # self._attach_download_js()

        self.view.widgets.multichoice['domains'].options = list(self.model.domains.keys())


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


    def load_mod_callback(self, event):
        """
        Creates the cell and the renderers.
        """     
        self.load_mod()  

        self.view.widgets.buttons['load_mod'].disabled = True
        self.view.DOM_elements['status'].text = 'Mechanisms loaded.'

    @log
    def load_mod(self):
        """
        Creates Mechanism object from an archive of mod files 
        and adds them to model.mechanisms.
        """

        self.model.add_default_mechanisms(recompile=False)
        self.model.add_mechanisms('mod', recompile=self.view.widgets.switches['recompile'].active)
        # TODO: Verify that the mod files are loaded successfully

        self._update_mechs_to_insert_widget()
        self._update_multichoice_domain_widget()
        logger.debug(f'Loaded mechanisms: {self.model.mechanisms.keys()}')


    # -------------------------------------------------------------------------
    # SEGMENTATION
    # -------------------------------------------------------------------------

    @log
    def build_seg_tree_callback(self, event):

        d_lambda = self.view.widgets.sliders['d_lambda'].value
        self.build_seg_tree(d_lambda)
        
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

        with remove_callbacks(self.view.widgets.selectors['group']):
            self.view.widgets.selectors['group'].options = list(self.model.groups.keys())
            self.view.widgets.selectors['group'].value = 'all'

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
        self.model.export_data()
        logger.info(f'Model exported.')
        
    def to_swc_callback(self, event):
        version = self.view.widgets.text['model_version'].value
        self.model.export_morphology(version=version)
        self.view.DOM_elements['status'].text = 'SWC file exported.'


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
            xhr.open('GET', filename, true);
            xhr.responseType = 'blob';
            xhr.onload = function(e) {{
                if (this.status == 200) {{
                    var blob = this.response;
                    var link = document.createElement('a');
                    link.href = window.URL.createObjectURL(blob);
                    link.download = filename.split('/').pop();
                    link.click();
                }}
            }};
            xhr.send();
            console.log('Downloaded', filename);
            """
            
            button.js_on_event('button_click', CustomJS(code=js_code))

        attach_download_js(self.view.widgets.buttons['export_model'], 
                           f'app/static/data/{self.model.name}_ephys.json')
        attach_download_js(self.view.widgets.buttons['export_swc'], 
                           f'app/static/data/{self.model.name}_3PS.swc')
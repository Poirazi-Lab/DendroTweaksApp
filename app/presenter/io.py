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

    @log
    def load_model_callback(self, event):
        """
        Loads the selected model.
        """
    
        self.load_model()

        self.view.widgets.buttons['load_swc'].disabled = True
        self.view.widgets.buttons['load_mod'].disabled = True
        self.view.widgets.buttons['load_model'].disabled = True


    def load_model(self):

        self.model.load_data()

        self._create_cell_renderer()
        self._init_cell_widgets()
        self._create_graph_renderer()
        
        for param_name in self.model.params:
            self._update_graph_param(param_name, update_colors=False)
        for param_name in ['AMPA', 'NMDA', 'GABAa', 'AMPA_NMDA', 'recordings', 'iclamps']:
            self._update_graph_param(param_name, update_colors=False)       

        # MISC --------------------------------------------------------
        self._attach_download_js() # needed to update the names of the files to download

        self.recorded_segments = [seg for seg in self.model.recordings]
        self.update_voltage()


    # =========================================================================
    # MORPHOLOGY
    # =========================================================================


    def load_swc_callback(self, event):
        """
        Creates the cell and the renderers.
        """     
        self.load_swc() 

        self.view.widgets.buttons['load_swc'].disabled = True
        self.view.widgets.buttons['load_model'].disabled = True


    @log
    def load_swc(self):
        """
        Creates the cell and the renderers.
        """

        # MORPHOLOGY --------------------------------------------
        
        self.create_morpohlogy()

        # LOAD MECHANISMS -----------------------------------------
        self.model.add_default_mechanisms()

        # PARAMETERS ----------------------------------------------
        self.model.add_group('all')
        self.model.set_global_param('cm', 1)
        self.model.set_global_param('Ra', 100)
        self._update_group_selector_widget()
        

        # SEGMENTATION --------------------------------------------
        d_lambda = self.view.widgets.sliders['d_lambda'].value
        self.build_seg_tree(d_lambda)
        
        
        # MISC ---------------------------------------------------
        self._attach_download_js()


    @log
    def create_morpohlogy(self):
        """
        Loads the selected cell from the SWC file. Builds the swc tree and sec tree.
        Creates sections in the simulator and sets segmentation based on the geometry.
        Builds the seg tree.
        Creates the default "all" group.
        """
        # Create swc and sec tree
        swc_file_name = self.model.name
        self.model.from_swc(swc_file_name)

        # Create and reference sections in simulator
        self.model.create_and_reference_sections_in_simulator()

        self._create_cell_renderer()
        self._init_cell_widgets()

    def _init_cell_widgets(self):
        """
        Configures the widgets after the cell is loaded.
        """
        SEC_TO_DOMAIN = {'soma': [], 'dend': [], 'axon': [], 'apic': [], 'none': ['']}
        for sec in self.model.sec_tree.sections:
            SEC_TO_DOMAIN[sec.domain].append(str(sec.idx))

        self.view.widgets.selectors['section'].options=SEC_TO_DOMAIN

        self.view.widgets.buttons['child'].disabled = False
        self.view.widgets.buttons['parent'].disabled = True
        self.view.widgets.buttons['sibling'].disabled = True


    # =========================================================================
    # MECHANISMS
    # =========================================================================


    def load_mod_callback(self, event):
        """
        Creates the cell and the renderers.
        """     
        self.load_mod()  

        self.view.widgets.buttons['load_mod'].disabled = True
        self.view.widgets.buttons['load_model'].disabled = True

    @log
    def load_mod(self):
        """
        Creates Mechanism object from an archive of mod files 
        and adds them to model.mechanisms.
        """

        self.model.add_mechanisms('mod', recompile=self.view.widgets.switches['recompile'].active)
        # TODO: Verify that the mod files are loaded successfully

        self.view.widgets.multichoice['mechanisms'].options = list(self.model.mechanisms.keys())
        logger.debug(f'Loaded mechanisms: {self.model.mechanisms.keys()}')


    # -------------------------------------------------------------------------
    # SEGMENTATION
    # -------------------------------------------------------------------------


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
        import os
        path_to_swc = os.path.join('app', 'static', 'data', f'{self.model.cell.name}.swc')
        self.model.to_swc(path_to_swc)

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
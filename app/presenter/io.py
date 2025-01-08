from logger import logger
from bokeh_utils import remove_callbacks
from bokeh_utils import log

# from model.mechanisms.distributions import Distribution

from bokeh.models.callbacks import CustomJS

import dendrotweaks as dd

class IOMixin():

    def __init__(self):
        logger.debug('IOMixin init')
        super().__init__()

    # =========================================================================
    # INPUT METHODS
    # =========================================================================

    @log
    def from_swc_callback(self, attr, old, new):
        """
        Creates the cell and the renderers.
        """

        # MORPHOLOGY --------------------------------------------
        swc_file_name = new
        self.create_morpohlogy(swc_file_name)

        # LOAD MECHANISMS -----------------------------------------
        self.add_archive('Default')
        self.model.load_archive('Synapses', recompile=False)

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


    def load_model_callback(self, attr, old, new):
        import os
        import json

        self.model.name = new.replace('.json', '')

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

    # MORPHOLOGY
    @log
    def create_morpohlogy(self, swc_file_name):
        """
        Loads the selected cell from the SWC file. Builds the swc tree and sec tree.
        Creates sections in the simulator and sets segmentation based on the geometry.
        Builds the seg tree.
        Creates the default "all" group.
        """
        # Create swc and sec tree
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

        self.view.widgets.selectors['from_swc'].disabled = True

    # MECHANISMS

    
    def mod_archives_callback(self, attr, old, new):
        """
        Callback for the selectors['mod_archives'] widget.
        """
        self.add_archive(new)
        self.view.widgets.selectors['mod_archives'].disabled = True

    @log
    def add_archive(self, archive_name):
        """
        Creates Mechanism object from an archive of mod files 
        and adds them to model.mechanisms.
        """

        self.model.add_archive(archive_name, recompile=self.view.widgets.switches['recompile'].active)
        # TODO: Verify that the mod files are loaded successfully

        self.view.widgets.multichoice['mechanisms'].options = list(self.model.mechanisms.keys())
        logger.debug(f'Loaded mechanisms: {self.model.mechanisms.keys()}')

    # GROUPS

    
    # def add_groups_from_json(self, data):
    #     for group_name, group_data in data['groups'].items():
    #         # Add the group to the model
    #         sections = [sec for sec in self.model.sec_tree.sections 
    #                     if sec.idx in group_data['nodes']]
    #         self.model.add_group(group_name, sections)
    #         # Add mechanisms to the group
    #         for mech_name in group_data['mechanisms']:
    #             self.insert_mech(mech_name=mech_name, 
    #                               group_name=group_name)
    #         # Add parameters to the group
    #         for param_name, param_data in group_data['parameters'].items():
    #             func = dd.Distribution.from_dict(param_data)
    #             self.model.groups[group_name].add_parameter(param_name, func)


    # SEGMENTATION

    def build_seg_tree_callback(self, attr, old, new):

        d_lambda = new
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



    # TODO: Implement for the channel panel!
    # @log
    # def update_channel_selector(self):
    #     logger.debug(f'Updating channel selector options')
    #     self.view.widgets.selectors['channel'].options = [ch.name for ch in self.model.channels.values() if ch.name != 'Leak']

    # FILE IMPORT

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
    # OUTPUT METHODS
    # =========================================================================

    def export_model_callback(self, event):        
        self.model.export_data()
        
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

        attach_download_js(self.view.widgets.buttons['to_json'], 
                           f'app/static/data/{self.model.name}_ephys.json')
        attach_download_js(self.view.widgets.buttons['to_swc'], 
                           f'app/static/data/{self.model.name}_3PS.swc')
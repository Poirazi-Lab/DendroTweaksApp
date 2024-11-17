from logger import logger
from bokeh_utils import remove_callbacks
from bokeh_utils import log

# from model.mechanisms.distributions import Distribution

from bokeh.models.callbacks import CustomJS

class IOMixin():

    def __init__(self):
        logger.debug('IOMixin init')
        super().__init__()

    # INPUT METHODS

    def create_cell(self, file_name):
        """
        Loads the selected cell from the SWC file. Builds the swc tree and sec tree.
        Creates sections in the simulator and sets segmentation based on the geometry.
        Builds the seg tree.
        Creates the default "all" group.
        """
        # Create swc and sec tree
        self.model.from_swc(file_name)

        # Create and reference sections in simulator
        self.model.create_and_reference_sections_in_simulator()

        # Add default group
        self.add_group('all', self.model.sec_tree.sections)

        # Set initial nseg
        d_lambda = self.view.widgets.sliders['d_lambda'].value
        logger.info(f'Aimed for {1/d_lambda} segments per length constant at {100} Hz')
        self.model.set_geom_nseg(d_lambda=d_lambda, f=100)
        self.model.build_seg_tree()
        logger.info(f'Total nseg: {len(self.model.seg_tree)}')


    @log
    def selector_cell_callback(self, attr, old, new):
        """
        Creates the cell and the renderers.
        """
        file_name = new
        self.create_cell(file_name)

        # # Add channel tabs ... 
        # self.update_channel_selector()

        # self.update_equilibtium_potentials()

        # add_callbacks_for_distributions_and_channels(app, cell_handler)

        # Initialize navigation buttons
        self.view.widgets.buttons['child'].disabled = False
        self.view.widgets.buttons['parent'].disabled = True
        self.view.widgets.buttons['sibling'].disabled = True
        
        # Update panels
        self.create_cell_renderer()
        self.create_graph_renderer()
        self.add_lasso_callback()

        sec_by_domain = {'soma': [], 'dend': [], 'axon': [], 'apic': [], 'none': ['']}
        for sec in self.model.sec_tree.sections:
            sec_by_domain[sec.domain].append(str(sec.idx))

        self.view.widgets.selectors['section'].options=sec_by_domain
        
        self.add_archive('Base', recompile=False)

        # def attach_download_js(button, file_path):

        #     js_code = f"""
        #     var filename = '{file_path}';
        #     var xhr = new XMLHttpRequest();
        #     xhr.open('GET', filename, true);
        #     xhr.responseType = 'blob';
        #     xhr.onload = function(e) {{
        #         if (this.status == 200) {{
        #             var blob = this.response;
        #             var link = document.createElement('a');
        #             link.href = window.URL.createObjectURL(blob);
        #             link.download = filename.split('/').pop();
        #             link.click();
        #         }}
        #     }};
        #     xhr.send();
        #     console.log('Downloaded', filename);
        #     """
            
        #     button.js_on_event('button_click', CustomJS(code=js_code))

        # attach_download_js(self.view.widgets.buttons['to_json'], 
        #                    f'app/static/data/{self.model.cell.name}_ephys.json')
        # attach_download_js(self.view.widgets.buttons['to_swc'], 
        #                    f'app/static/data/{self.model.cell.name}_3PS.swc')
        
        self.view.widgets.selectors['cell'].disabled = True

    # def cadyn_files_callback(self, attr, old, new):
    #     logger.debug(f'cadyn_files_callback: {new}')
    #     if new:
    #         self.model.add_ca_dynamics(mod_name=new)
    #         if self.model.cell.name == 'Hay_2011':
    #             self.Ca_dyn_temp()
    #     else: 
    #         self.model.remove_ca_dynamics()

    def add_archive(self, archive_name, recompile=False):

        self.model.add_archive(archive_name, recompile=self.view.widgets.switches['recompile'].active)
        # TODO: Verify that the mod files are loaded successfully

        self.view.widgets.multichoice['mechanisms'].options = list(self.model.mechanisms.keys())
        logger.debug(f'Loaded mechanisms: {self.model.mechanisms.keys()}')

        self.view.widgets.selectors['mod_archives'].disabled = True

    @log
    def mod_archives_callback(self, attr, old, new):        
        self.add_archive(new, recompile=self.view.widgets.switches['recompile'].active)

        
        

    # @log
    # def mod_files_callback_old(self, attr, old, new):

    #     # Only update if cell is loaded
    #     if self.model.cell is None:
    #         return

    #     mod_to_add = list(set(new).difference(set(old)))
    #     mod_to_remove = list(set(old).difference(set(new)))

    #     logger.info(f'ch_to_add: {mod_to_add}')
    #     logger.info(f'ch_to_remove: {mod_to_remove}')

    #     if len(mod_to_add) > 1: logger.warning('Only one channel can be added at a time')
    #     if len(mod_to_remove) > 1: logger.warning('Only one channel can be removed at a time')

    #     # Remove
    #     if mod_to_remove:
    #         self.model.remove_channel(mod_to_remove[0])
    #         self.view.widgets.selectors['graph_param'].value = self.view.widgets.selectors['graph_param'].options[0]

    #     # Add
    #     if mod_to_add:
    #         self.model.add_channel(mod_to_add[0], recompile=self.view.widgets.switches['recompile'].active)
    #         self.update_graph_param(f'gbar_{self.model.channels[mod_to_add[0]].suffix}')
    #         # P.add_channel(mod_to_add[0])
         
    #     # Add channel tabs ...
    #     self.update_channel_selector()

    #     self.update_equilibtium_potentials()
            
    #     # Update graph param selector with new channels
        
    #     self.update_graph_param_selector()

    @log
    def update_channel_selector(self):
        logger.debug(f'Updating channel selector options')
        self.view.widgets.selectors['channel'].options = [ch.name for ch in self.model.channels.values() if ch.name != 'Leak']

    def from_json(self, path):
        
        import json

        with open(path, 'r') as f:
            data = json.load(f)

        self.add_archive(data['archive_name'], 
                        recompile=self.view.widgets.switches['recompile'].active)

        for group_name, group_data in data['groups'].items():
            self.model.add_group(group_name, [sec for sec in self.model.cell.sections if sec.idx in group_data['sec_ids']])
            for mechanism_name, mechanism_data in group_data['mechanisms'].items():
                self.add_mechanism(mechanism_name, mechanism_data['mod_name'])
            for param_name, param_data in mechanism_data['parameters'].items():
                self.model.groups[group_name].add_parameter(param_name, Distribution.from_dict(param_data))

        # for ch in data['channels']:
        #     # mod_file = f"{data['path_to_model']}/mechanisms/{ch['name']}/{ch['name']}.mod"
        #     if not self.model.channels.get(ch['name']):
        #         self.model.add_channel(ch['name'], recompile=self.view.widgets.switches['recompile'].active)
        #     for group in ch['groups']:
        #         segments = [self.model.cell.segments[seg_name] for seg_name in group['seg_names']]
        #         self.model.channels[ch['name']].add_group(segments,
        #                                                   group['param_name'])
        #         self.model.channels[ch['name']].groups[-1].distribution = Distribution.from_dict(group['distribution'])
        #     self.update_graph_param(f"gbar_{ch['suffix']}")
        #     self.update_section_param_data()

        # with remove_callbacks(self.view.widgets.multichoice['mod_files']):
        #     self.view.widgets.multichoice['mod_files'].value = [ch['name'] for ch in data['channels']]

        # self.update_channel_selector()

        # if data.get('capacitance') is not None:
        #     self.model.capacitance.remove_all_groups()
        #     for group in data['capacitance']['groups']:
        #         segments = [self.model.cell.segments[seg_name] for seg_name in group['seg_names']]
        #         self.model.capacitance.add_group(segments, group['param_name'])
        #         self.model.capacitance.groups[-1].distribution = Distribution.from_dict(group['distribution'])
        #     self.update_graph_param('cm')
        #     self.update_section_param_data()

        # if data.get('ca_dynamics') is not None:
        #     self.view.widgets.selectors['mod_files_cadyn'].value = data['ca_dynamics']

        # self.update_equilibtium_potentials()
        # if data.get('equilibrium_potentials') is not None:
        #     for ion, value in data['equilibrium_potentials'].items():
        #         self.view.widgets.spinners[f'e{ion}'].value = value

        # if data.get('simulator') is not None:
        #     self.view.widgets.sliders['dt'].value = data['simulator']['dt']
        #     self.model.simulator.dt = data['simulator']['dt']
        #     self.view.widgets.sliders['celsius'].value = data['simulator']['celsius']
        #     self.model.simulator.celsius = data['simulator']['celsius']
        #     self.view.widgets.sliders['v_init'].value = data['simulator']['v_init']
        #     self.model.simulator.v_init = data['simulator']['v_init']

        # if self.model.cell.name == 'Poirazi_2003':
        #     self.Ra_sigmoidal_temp()

        # self.update_graph_param_selector()

    def from_json_callback(self, event):
        if self.model.cell is None:
            logger.warning('No cell loaded')
            return
        import os
        path_to_json = os.path.join('app', 'static', 'data', f'{self.model.cell.name}_ephys.json')
        self.from_json(path_to_json)

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
                self.view.widgets.selectors['cell'].options = [f for f in os.listdir('app/model/swc') if f.endswith('.swc') or f.endswith('.asc')]

            elif filename.endswith('.mod'):
                mod_folder = 'mod_cadyn' if 'cadyn' in filename else 'mod'
                widget_name = 'mod_files_cadyn' if 'cadyn' in filename else 'mod_files'
                os.makedirs(f'app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}', exist_ok=True)
                with open(f'app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}/{filename}', 'wb') as file:
                    file.write(file_content)
                logger.info(f'File {filename} saved to app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}')
                self.view.widgets.multichoice[widget_name].options = self.model.list_mod_files(mod_folder=mod_folder)

    ## OUTPUT METHODS

    def to_json_callback(self, event):
        import os
        path_to_json = os.path.join('app', 'static', 'data', f'{self.model.cell.name}_ephys.json')
        self.model.to_json(path_to_json)

    def export_to_swc_callback(self, event):
        import os
        path_to_swc = os.path.join('app', 'static', 'data', f'{self.model.cell.name}.swc')
        self.model.to_swc(path_to_swc)
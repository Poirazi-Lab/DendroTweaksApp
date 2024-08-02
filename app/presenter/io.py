from logger import logger
from bokeh_utils import remove_callbacks
from bokeh_utils import log

from model.mechanisms.distributions import Distribution

from bokeh.models.callbacks import CustomJS

class IOMixin():

    def __init__(self):
        logger.debug('IOMixin init')
        super().__init__()

    # INPUT METHODS

    @log
    def update_graph_param_selector(self):
        new_params = {f'gbar_{ch.suffix}': 
                      f'Conductance {ch.suffix}, S/cm2' 
                      for ch in self.model.channels.values()}
        self.view.update_ephys_params(new_params)
        logger.debug(f'Updating graph param selector with {new_params}')
        logger.debug(f'Updating graph param selector with ephys params: {self.view.ephys_params}')
        with remove_callbacks(self.view.widgets.selectors['graph_param']):
            if self.view.widgets.tabs['section'].active == 1:
                self.view.widgets.selectors['graph_param'].options = list(self.view.ephys_params)
                self.view.widgets.selectors['graph_param'].value = self.view.widgets.selectors['graph_param'].options[0]
            else:
                self.view.widgets.selectors['graph_param'].options = list(self.view.params)
                self.view.widgets.selectors['graph_param'].value = self.view.widgets.selectors['graph_param'].options[0]

    def reset_simulation_state(self):
        self.view.widgets.switches['record'].active = False
        self.view.widgets.switches['iclamp'].active = False
        self.view.sources['sim'].data = data={'xs': [], 'ys': [], 'color': []}

    @log
    def selector_cell_callback(self, attr, old, new):

        self.view.widgets.multichoice['mod_files'].value = ['Leak']

        # Create cell
        path_to_swc=f"app/model/swc/{self.view.widgets.selectors['cell'].value}"
        self.create_cell(path_to_swc)

        # Set initial nseg
        d_lambda = self.view.widgets.sliders['d_lambda'].value
        logger.info(f'Aimed for {1/d_lambda} segments per length constant at {100} Hz')
        self.model.cell.set_geom_nseg(d_lambda=d_lambda)
        logger.info(f'Total nseg: {self.model.cell.total_nseg}')

        for sec in self.model.cell.all:
            sec.Ra = 100
        self.model.add_capacitance()
        # self.model.add_ca_dynamics(mod_name='Park_cadyn')
        # self.model.add_ca_dynamics(mod_name='Gonzalez_cadyn')
        
        # Add channels
        for mod_name in self.view.widgets.multichoice['mod_files'].value:
            self.model.add_channel(mod_name, recompile=True)

        # Add channel tabs ... 
        self.update_channel_tabs()

        self.update_equilibtium_potentials()

        # Update graph param selector with new channels
        self.update_graph_param_selector()

        # add_callbacks_for_distributions_and_channels(app, cell_handler)

        # Initialize navigation buttons
        self.view.widgets.buttons['child'].disabled = False
        self.view.widgets.buttons['parent'].disabled = True
        self.view.widgets.buttons['sibling'].disabled = True
        
        # Update panels
        self.create_cell_renderer()
        self.create_graph_renderer()
        self.add_lasso_callback()

        self.view.widgets.selectors['section'].options=[''] + list(self.model.cell.sections.keys())
        logger.debug(f"Section selector value: {self.view.widgets.selectors['section'].value}")

        self.reset_simulation_state()

        self.view.widgets.buttons['to_json'].js_on_event('button_click', CustomJS(
            code=f"var filename = 'app/static/data/{self.model.cell.name}_ephys.json';" +
        """
        var xhr = new XMLHttpRequest();
        xhr.open('GET', filename, true);
        xhr.responseType = 'blob';
        xhr.onload = function(e) {
            if (this.status == 200) {
                var blob = this.response;
                var link = document.createElement('a');
                link.href = window.URL.createObjectURL(blob);
                link.download = filename.split('/').pop();
                link.click();
            }
        };
        xhr.send();
        console.log('Downloaded', filename);
        """))
        
        with remove_callbacks(self.view.widgets.multichoice['mod_files']):
            self.view.widgets.multichoice['mod_files'].options = self.model.list_mod_files()
            self.view.widgets.multichoice['mod_files'].value = ['Leak']

    def cadyn_files_callback(self, attr, old, new):
        logger.debug(f'cadyn_files_callback: {new}')
        if new:
            self.model.add_ca_dynamics(mod_name=new)

    @log
    def mod_files_callback(self, attr, old, new):

        # Only update if cell is loaded
        if self.model.cell is None:
            return

        mod_to_add = list(set(new).difference(set(old)))
        mod_to_remove = list(set(old).difference(set(new)))

        logger.info(f'ch_to_add: {mod_to_add}')
        logger.info(f'ch_to_remove: {mod_to_remove}')

        if len(mod_to_add) > 1: logger.warning('Only one channel can be added at a time')
        if len(mod_to_remove) > 1: logger.warning('Only one channel can be removed at a time')

        # Remove
        if mod_to_remove:
            self.model.remove_channel(mod_to_remove[0])
            self.view.widgets.selectors['graph_param'].value = self.view.widgets.selectors['graph_param'].options[0]

        # Add
        if mod_to_add:
            self.model.add_channel(mod_to_add[0], recompile=True)
            self.update_graph_param(f'gbar_{self.model.channels[mod_to_add[0]].suffix}')
            # P.add_channel(mod_to_add[0])
         
        # Add channel tabs ...
        self.update_channel_tabs()

        self.update_equilibtium_potentials()
            
        # Update graph param selector with new channels
        
        self.update_graph_param_selector()

    def from_json(self, path):
        
        import json

        with open(path, 'r') as f:
            data = json.load(f)

        for ch in data['channels']:
            # mod_file = f"{data['path_to_model']}/mechanisms/{ch['name']}/{ch['name']}.mod"
            if not self.model.channels.get(ch['name']):
                self.model.add_channel(ch['name'], recompile=True)
            for group in ch['groups']:
                segments = [self.model.cell.segments[seg_name] for seg_name in group['seg_names']]
                self.model.channels[ch['name']].add_group(segments,
                                                          group['param_name'])
                self.model.channels[ch['name']].groups[-1].distribution = Distribution.from_dict(group['distribution'])
            self.update_graph_param(f"gbar_{ch['suffix']}")
            self.update_section_param_data()

        with remove_callbacks(self.view.widgets.multichoice['mod_files']):
            self.view.widgets.multichoice['mod_files'].value = [ch['name'] for ch in data['channels']]

        self.update_channel_tabs()

        if data.get('capacitance') is not None:
            self.model.capacitance.remove_all_groups()
            for group in data['capacitance']['groups']:
                segments = [self.model.cell.segments[seg_name] for seg_name in group['seg_names']]
                self.model.capacitance.add_group(segments, group['param_name'])
                self.model.capacitance.groups[-1].distribution = Distribution.from_dict(group['distribution'])
            self.update_graph_param('cm')
            self.update_section_param_data()

        self.update_equilibtium_potentials()
        if data.get('equilibrium_potentials') is not None:
            for ion, value in data['equilibrium_potentials'].items():
                self.view.widgets.spinners[f'e{ion}'].value = value

        if data.get('simulator') is not None:
            self.view.widgets.sliders['dt'].value = data['simulator']['dt']
            self.model.simulator.dt = data['simulator']['dt']
            self.view.widgets.sliders['celsius'].value = data['simulator']['celsius']
            self.model.simulator.celsius = data['simulator']['celsius']
            self.view.widgets.sliders['v_init'].value = data['simulator']['v_init']
            self.model.simulator.v_init = data['simulator']['v_init']

        if self.model.cell.name == 'Poirazi_2003':
            self.Ra_sigmoidal_temp()
        if self.model.cell.name == 'Hay_2011':
            self.Ca_dyn_temp()

        self.update_graph_param_selector()

    def from_json_callback(self, event):
        import os
        path_to_json = os.path.join('app', 'static', 'data', f'{self.model.cell.name}_ephys.json')
        self.from_json(path_to_json)

    def import_file_callback(self, attr, old, new):
        import base64
        import os
        import io

        filename = self.view.widgets.text['filename_workaround'].value
        logger.info(f'Filename: {filename}')
        decoded = base64.b64decode(new)
        # f = io.BytesIO(decoded)
        
        if filename.endswith('.swc') or filename.endswith('.asc'):
            with open(f'app/model/swc/{filename}', 'wb') as file:
                file.write(decoded)
            logger.info(f'File {filename} saved to app/model/swc')
            self.view.widgets.selectors['cell'].options = [f for f in os.listdir('app/model/swc') if f.endswith('.swc') or f.endswith('.asc')]

        elif filename.endswith('.mod'):
            mod_folder = 'mod_cadyn' if 'cadyn' in filename else 'mod'
            widget_name = 'mod_files_cadyn' if 'cadyn' in filename else 'mod_files'
            os.makedirs(f'app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}', exist_ok=True)
            with open(f'app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}/{filename}', 'wb') as file:
                file.write(decoded)
            logger.info(f'File {filename} saved to app/model/mechanisms/{mod_folder}/{filename.replace(".mod", "")}')
            self.view.widgets.multichoice[widget_name].options = self.model.list_mod_files(mod_folder=mod_folder)

    ## OUTPUT METHODS

    def to_json_callback(self, event):
        import os
        path_to_json = os.path.join('app', 'static', 'data', f'{self.model.cell.name}_ephys.json')
        self.model.to_json(path_to_json)
from logger import logger

class SectionMixin():

    def __init__(self):
        logger.debug('SectionMixin init')
        super().__init__()
    

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
   
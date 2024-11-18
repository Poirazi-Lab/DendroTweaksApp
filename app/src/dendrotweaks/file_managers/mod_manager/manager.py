from dendrotweaks.file_managers.utils import list_folders, list_files
from dendrotweaks.file_managers.mod_manager.code_generator import CodeGenerator
from dendrotweaks.file_managers.mod_manager.parser import MODParser
from dendrotweaks.file_managers.mod_manager.reader import MODReader
import os
from pprint import pprint
# PATH_TO_TEMPLATE = "static/data/templates/template.py"
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
print(base_path)

TEMPLATES = {
    'NEURON': {
        'template': os.path.join(base_path, 'dendrotweaks', 'file_managers', 'mod_manager', 'templates', 'template_dd.py'),
        'lib': 'np'
    },
    'Jaxley': {
        'template': f'{base_path}dendrotweaks/file_managers/mod_manager/templates/template_jaxley.py',
        'lib': 'jnp'
    }
}


class MODManager():

    def __init__(self, simulator_name='NEURON', path_to_data='data'):

        self._path_to_data = path_to_data
        self._archive = None
        self._simulator_name = simulator_name

        self.reader = MODReader()
        self.parser = MODParser()

        path_to_template = TEMPLATES[simulator_name]['template']
        lib = TEMPLATES[simulator_name]['lib']
        self.code_generator = CodeGenerator(path_to_template, lib)

        self.blocks = []
        self.ast = None
        self.py_code = None

    @property
    def simulator_name(self):
        return self._simulator_name

    @simulator_name.setter
    def simulator_name(self, simulator_name):
        self._simulator_name = simulator_name
        self.code_generator = CodeGenerator(TEMPLATES[simulator_name]['template'],
                                            TEMPLATES[simulator_name]['lib'])

    def info(self):
        print(f"{'='*20}\nMOD MANAGER")
        print(f"\nPath to data: {self._path_to_data}")
        print(f"Simulator: {self._simulator_name}")
        print("\nAvailable archives:")
        pprint(self.list_archives())
        print(f"\nREAD      : {self.reader.file_name if self.reader.file_name else False}")
        print(f"PARSED    : {True if self.ast else False}")
        print(f"GENERATED : {True if self.py_code else False}")

    def to_dict(self):
        return {
            'archive': self._archive,
        }

    # FILE MANAGEMENT METHODS

    def list_archives(self, path_to_mod=''):
        path_to_mod = path_to_mod or os.path.join(self._path_to_data, 'mod')
        folders = list_folders(path_to_mod)
        archives = {}
        for folder in folders:
            path_to_archive = os.path.join(path_to_mod, folder)
            files = list_files(path_to_archive, extension='.mod')
            archives[folder] = [f.split('.')[0] for f in files]
        return archives

    def load_archive(self, archive, recompile=False):

        self._archive = archive
        self._replace_suffix_with_name(archive)

        path_to_archive = os.path.join(self._path_to_data, 'mod', archive)

        import neuron
        from neuron import h

        if all([hasattr(h, name) for name in self.list_archives()[archive]]):
            print(f'Mechanisms already loaded from "{path_to_archive}"')
            return

        if recompile or not os.path.exists(os.path.join(path_to_archive, 'x86_64')):
            self._compile_archive(archive)
        

        neuron.load_mechanisms(path_to_archive)
        print(f'Loaded mechanisms from "{path_to_archive}"')

    def _compile_archive(self, archive='Base'):
        """
        Compile all mod files in the specified archive using nrnivmodl.

        Parameters
        ----------
        archive : str
            Name of the archive to compile.
        recompile : bool
            Whether to recompile the mod files.
        """
        path_to_archive = os.path.join(self._path_to_data, 'mod', archive)

        if os.path.exists(os.path.join(path_to_archive, 'x86_64')):
            import shutil
            shutil.rmtree(os.path.join(path_to_archive, 'x86_64'))

        cwd = os.getcwd()
        os.chdir(path_to_archive)
        os.system('nrnivmodl')
        os.chdir(cwd)
        print(f'Compiled mod files from "{path_to_archive}"')

    def _replace_suffix_with_name(self, archive):
        """
        Replace the suffix in the mod files with the name of the file
        for consistency reasons.
        """

        path_to_archive = os.path.join(self._path_to_data, 'mod', archive)
        mechanism_names = self.list_archives()[archive]

        for name in mechanism_names:
            path_to_file = os.path.join(path_to_archive, name + '.mod')
            self.reader.read(path_to_file)
            self.reader.replace_suffix_with_name(name)
            self.reader.write(path_to_file)

    # READING METHODS

    def read(self, path_to_file=None, content=None,
             remove_unitsoff=True, remove_inline_comments=True,
             remove_suffix_from_gbar=True):
        """
        Reads content either from a file or directly from a string.

        Parameters:
        ----------
        path_to_file : str, optional
            Path to the file to read.
        content : str, optional
            Direct string content to read.
        remove_unitsoff : bool
            Whether to remove 'unitsoff' during preprocessing.
        remove_inline_comments : bool
            Whether to remove inline comments during preprocessing.
        remove_suffix_from_gbar : bool
            Whether to remove suffix from gbar during preprocessing.
        """
        if path_to_file:
            self.reader.read(path_to_file)
        elif content:
            self.reader._content = str(content)
            self.reader._original_content = str(content)
        else:
            raise ValueError(
                "Either 'path_to_file' or 'content' must be provided.")

        self._preprocess(remove_unitsoff,
                         remove_inline_comments,
                         remove_suffix_from_gbar)

        self._split_content_in_blocks()

    def _preprocess(self, remove_unitsoff=True, remove_inline_comments=True, remove_suffix_from_gbar=True):
        """
        Preprocess the content of the file.

        Parameters:
        ----------
        remove_unitsoff : bool
            Whether to remove 'unitsoff' during preprocessing.
        remove_inline_comments : bool
            Whether to remove inline comments during preprocessing.
        remove_suffix_from_gbar : bool
            Whether to remove suffix from gbar during preprocessing.
        """
        if remove_unitsoff:
            self.reader.remove_unitsoff()
        if remove_inline_comments:
            self.reader.remove_inline_comments()
        if remove_suffix_from_gbar:
            self.reader.remove_suffix_from_gbar()

    def _split_content_in_blocks(self):
        """
        Split the content of the file into blocks for further processing.
        """
        self.reader.split_content_in_blocks()
        self.blocks = self.reader.blocks

    # PARSING METHODS

    def parse_block(self, block_name):
        """
        Parse a specific block from the file.

        Parameters:
        block_name : str
            Name of the block to parse. e.g. NEURON, PARAMETER, etc.
        """
        assert self.blocks is not None, "You must read the file first using the read method"
        block_content = self.blocks[block_name]
        return self.parser.parse_block(block_name, block_content)

    def parse(self, update_state_vars=True, replace_constants=True):
        """
        Parse the entire file content.

        Parameters
        ----------
        update_state_vars : bool
            Whether to update state variables in the AST with the corresponding 
            power from the equation in the BREAKPOINT block.
        replace_constants : bool
            Whether to replace constants R and FARADAY with their values.
        """
        assert self.blocks is not None, "You must read the file first using the read method"
        self.parser.parse(self.blocks)

        if update_state_vars:
            self.parser.update_state_vars_with_power()
            self.parser.standardize_state_var_names()
        # TODO: Implement this
        # if replace_constants:
            # self.parser.replace_constants_with_values()

        self.ast = self.parser.ast

    # CODE GENERATION METHODS

    def ast_to_python(self):
        """
        Convert the AST to Python code.
        """
        assert self.ast is not None, "You must parse the file first using the parse method"
        self.code_generator.generate(self.ast)

        self.py_code = self.code_generator._py_code

    def write(self, path_to_file):
        """
        Write the generated Python code to a file.

        Parameters
        ----------
        path_to_file : str
            Path to the file to write the Python code to.
        """
        assert self.py_code is not None, "You must convert the AST to Python code first using the ast_to_python method"
        # check that dir exists or create (path to file is the dir and the file name)
        path_to_dir = '/'.join(path_to_file.split('/')[:-1])
        if not os.path.exists(path_to_dir):
            os.makedirs(path_to_dir)

        self.code_generator.write(path_to_file)

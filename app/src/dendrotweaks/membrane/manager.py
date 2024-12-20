from chanopy.loader import Loader
from chanopy.reader import Reader
from chanopy.parser import Parser
from chanopy.code_generators import PythonCodeGenerator, NMODLCodeGenerator
from chanopy.mechanisms import Mechanism, IonChannel, StandardIonChannel
import numpy as np

import os
from pprint import pprint
from dataclasses import dataclass
# PATH_TO_TEMPLATE = "static/data/templates/template.py"
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
print(base_path)

TEMPLATES = {
    'NEURON': {
        'template_name': 'template_dd.py',
        'library': 'np'
    },
    'Jaxley': {
        'template_name': 'template_jaxley.py',
        'library': 'jnp'
    }
}

DEFAULT_PREPROCESSING_CONFIG = {
    "replace_suffix_with_name": True,
    "remove_unitsoff": True,
    "remove_inline_comments": True,
    "remove_suffix_from_gbar": True,
    "remove_verbatim": True
}

DEFAULT_POSTPROCESSING_CONFIG = {
    "update_state_vars_with_powers": True,
    "replace_constants_with_values": True,
    "restore_expressions": True
}


class MODManager():

    def __init__(self, path_to_data='data/mod/'):

        self.path_to_data = path_to_data
        self.path_to_templates = os.path.join(base_path, 'chanopy2', 'src', 'chanopy', 'templates')
        self.path_to_mechanisms = os.path.join(base_path, 'chanopy2', 'app', 'chanopy', 'collection')

        self.loader = Loader()
        self.reader = Reader()
        self.parser = Parser()
        self.code_generators = {
            'Python': PythonCodeGenerator(),
            'NMODL': NMODLCodeGenerator()
        }

    @property
    def mechanism_name(self):
        return self.reader.file_name

    @property
    def simulator_name(self):
        return self._simulator_name

    @simulator_name.setter
    def simulator_name(self, simulator_name):
        self._simulator_name = simulator_name
        self.writer = CodeGenerator(path_to_template=TEMPLATES[simulator_name]['template'],
                                    library=TEMPLATES[simulator_name]['lib'])

    @property
    def archives(self):
        return self.loader.archives

    @property
    def content(self):
        return self.reader.content

    @property
    def blocks(self):
        return self.reader.blocks

    @property
    def ast(self):
        return self.parser.ast

    @property
    def content_python(self):
        return self.writer.py_code

    def info(self):
        print(f"{'='*20}\nMOD MANAGER")
        print(f"\nPath to data: {self.path_to_data}")
        print(f"Simulator: {self._simulator_name}")
        print("\nAvailable archives:")
        pprint(self.list_archives())
        print(f"\nREAD      : {self.reader.file_name if self.reader.file_name else False}")
        print(f"PARSED    : {True if self.ast else False}")
        print(f"GENERATED : {True if self.py_code else False}")

    def to_dict(self):
        return {
            'archives': self._archives,
        }

    # FILE MANAGEMENT METHODS

    def list_archives(self, replace_suffix_with_name: bool = False):
        self.loader.list_archives(self.path_to_data)
        # if replace_suffix_with_name:
        #     for archive_name in self.archives:
        #         for file_name in archives[archive_name]:
        #             self.reader.read(os.path.join(self.path_to_data, archive_name, f"{file_name}.mod"))
        #             self.reader.replace_suffix_with_name()

    def load_archive(self, archive_name, recompile=True):
        """
        Load a specific archive.

        Parameters:
        ----------
        archive_name : str
            Name of the archive of MOD files to load.
        recompile : bool
            Whether to recompile the files in the archive.
        """
        path_to_archive = os.path.join(self.path_to_data, 
                                       archive_name)
        self.loader.load_archive(path_to_archive, recompile)

    # READING METHODS

    def read(self, file_name, archive_name=None):
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
        path_to_file = os.path.join(self.path_to_data, 
                                    archive_name, 
                                    f"{file_name}.mod")
        self.reader.read(path_to_file)


    def preprocess(self, config=None):
        """
        Preprocess the content of the file.

        Parameters:
        ----------
        config : dict
            Configuration for preprocessing.
        """
        config = config or DEFAULT_PREPROCESSING_CONFIG

        if config.get('replace_suffix_with_name'):
            self.reader.replace_suffix_with_name(overwirte=True)
        if config.get('remove_suffix_from_gbar'):
            self.reader.remove_suffix_from_gbar()
        if config.get('remove_unitsoff'):
            self.reader.remove_unitsoff()
        if config.get('remove_inline_comments'):
            self.reader.remove_inline_comments()
        if config.get('remove_verbatim'):
            self.reader.remove_verbatim()
        
        self.reader.split_content_in_blocks()
        self.reader.find_unmatched_content()

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

    def parse(self):
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
        if self.blocks is None:
            raise ValueError("You must read the file first using the read method")
        self.parser.parse(self.blocks)


    def postprocess(self, config=None):
        """
        Postprocess the parsed AST.

        Parameters
        ----------
        update_state_vars : bool
            Whether to update state variables in the AST with the corresponding 
            power from the equation in the BREAKPOINT block.

        replace_constants : bool
            Whether to replace constants R and FARADAY with their values.
        """
        config = config or DEFAULT_POSTPROCESSING_CONFIG

        self.parser.split_comment_block()

        if config.get('update_state_vars_with_powers'):
            self.parser.update_state_vars_with_power()
            self.parser.standardize_state_var_names()
        # TODO: Implement this
        # if config.get('replace_constants'):
            # self.parser.replace_constants_with_values()
        if config.get('restore_expressions'):
            self.parser.restore_expressions()

    # CODE GENERATION METHODS

    def generate_and_write_python(self, template_name='default', path_to_file=None):
        """
        Convert the AST to Python code and write it to a file.
        """
        assert self.ast is not None, "You must parse the file first using the parse method"
        
        path_to_template = os.path.join(self.path_to_templates, f"{template_name}.py")
        content = self.code_generators['Python'].generate(self.ast, path_to_template)

        path_to_file = path_to_file or os.path.join(self.path_to_mechanisms, f"{self.mechanism_name}.py")
        write_file(content, path_to_file)

    def generate_and_write_nmodl(self, channel, template_name="standard.mod", path_to_file=None):
        """
        Convert the AST to NMODL code and write it to a file.
        """
        path_to_template = os.path.join(self.path_to_templates, f"{template_name}.mod")
        content = self.code_generators['NMODL'].generate(channel, path_to_template)

        path_to_file = path_to_file or os.path.join(self.path_to_data, channel.name, f"{channel.name}.mod")
        write_file(content, path_to_file)

    def convert_mod_to_python(self, file_name: str, 
                              archive_name: str,
                              template_name: str) -> None:
        self.read(file_name, archive_name)
        self.preprocess()
        self.parse()
        self.postprocess()
        self.generate_and_write_python(template_name)

    def create_mechanism(self, file_name: str, 
                         archive_name: str,
                         template_name: str) -> Mechanism:
        self.convert_mod_to_python(file_name, archive_name, template_name)
        return self._instantiate_mechanism(file_name)

    def _instantiate_mechanism(self, file_name: str) -> Mechanism:
        """
        Read a MOD file, parse it to an AST, and write it to a Python file.

        Parameters
        ----------
        file_name : str
            The name of the MOD file to read. Also used to name the Python file.
        """
        class_name = module_name = file_name
        import sys
        sys.path.append(self.path_to_mechanisms)
        Mechanism = dynamic_import(module_name, class_name)
        return Mechanism()

    def standardize_mod_file(self, file_name: str,
                            archive_name: str,
                            template_name: str) -> None:
        channel = self.create_mechanism(file_name, archive_name, template_name)
        standard_channel = self.standardize_channel(channel)
        self.generate_and_write_nmodl(standard_channel)

    def standardize_channel(self, channel: IonChannel, 
                            x: np.array = None,
                            temperature: float = 37) -> StandardIonChannel:
        
        standard_channel = StandardIonChannel(name=channel.name, 
                                              state_powers=channel._state_powers, 
                                              ion=channel.ion)
        standard_channel.params.update({'q10': channel.params.get('q10'),
                                        'temp': channel.params.get('temp')})
        standard_channel.set_tadj(temperature)
        data = channel.get_data(x, temperature)
        standard_channel.fit_to_data(data)

        return standard_channel


def dynamic_import(module_name, class_name):
    """
    Dynamically import a class from a module.

    Parameters
    ----------
    module_name : str
        Name of the module to import.
    class_name : str
        Name of the class to import.
    """

    from importlib import import_module
    module = import_module(module_name)
    return getattr(module, class_name)

def write_file(content, path_to_file):
    if not os.path.exists(os.path.dirname(path_to_file)):
        os.makedirs(os.path.dirname(path_to_file))
    with open(path_to_file, 'w') as f:
        f.write(content)
    print(f"Saved content to {path_to_file}")
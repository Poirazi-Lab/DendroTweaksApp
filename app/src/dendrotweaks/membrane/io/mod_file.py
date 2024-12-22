import os
import re
from typing import List
import sys

class MODFile:
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.data = None
        self.load()

    def load(self) -> None:
        with open(self.path, 'r') as f:
            self.data = f.read()

    def save(self) -> None:
        with open(self.path, 'w') as f:
            f.write(self.data)

    def remove_inline_comments(self) -> None:
        self.data = re.sub(r'//.*', '', self.data)

    def remove_keywords(self, keywords: List[str]) -> None:
        for keyword in keywords:
            self.data = re.sub(rf'\b{keyword.upper()}\b', '', self.data)

    def remove_between(self, start: str, end: str) -> None:
        self.data = re.sub(rf'{re.escape(start)}.*?{re.escape(end)}', '', self.data, flags=re.DOTALL)

    def preprocess(self) -> None:
        self.replace_suffix_with_name(overwirte=True)
        self.remove_inline_comments()
        self.remove_keywords(['UNITSON', 'UNITSOFF'])
        self.remove_between('VERBATIM', 'ENDVERBATIM')

    def replace_suffix_with_name(self, overwirte=False) -> None:
        """
        Replace the suffix in the content of the file with the file name.

        Notes
        -----
        Suffix is a string of the form SUFFIX suffix

        Parameters:
            file_name (str): The name of the file to replace the suffix with.
        """
        suffix_pattern = r'SUFFIX\s+\w+'
        match = re.search(suffix_pattern, self.data)
        print(f"Replacing {match.group()} with SUFFIX {self.name}")
        self.data = re.sub(suffix_pattern, f'SUFFIX {self.name}', self.data)
        if overwirte:
            self.save()



class Preprocessor:

    def __init__(self, config: dict = None):
        
        if config is None:
            config = {
                'remove_inline_comments': True,
                'remove_keywords': ['UNITSON', 'UNITSOFF'],
                'remove_between': [('VERBATIM', 'ENDVERBATIM')]
            }
        
    def remove_inline_comments(self, content: str) -> str:
        return re.sub(r'//.*', '', content)

    def remove_keywords(self, content: str, keywords: List[str]) -> str:
        for keyword in keywords:
            content = re.sub(rf'\b{keyword.upper()}\b', '', content)
        return content

    def remove_between(self, content: str, start: str, end: str) -> str:
        return re.sub(rf'{re.escape(start)}.*?{re.escape(end)}', '', content, flags=re.DOTALL)

    def preprocess(self, content: str) -> str:
        if self.config.get('remove_inline_comments', False):
            content = self.remove_inline_comments(content)
        if 'remove_keywords' in self.config:
            content = self.remove_keywords(content, self.config['remove_keywords'])
        if 'remove_between' in self.config:
            for start, end in self.config['remove_between']:
                content = self.remove_between(content, start, end)
        return content


class MODFileConverter():

    def __init__(self, config: dict = None):
        
        if config is None:
            self.config = {
                'replace_suffix_with_name': True,
            }

        self.mod_content = None
        self.blocks = None
        self.ast = None
        self.python_content = None
        
    def convert(self, path_to_mod, path_to_python, path_to_template):
        """ Converts a mod file to a python file.

        Args:
            path_to_mod (str): The path to the mod file.
            path_to_python (str): The path to the python file.
            path_to_template (str): The path to the JINJA template file.
        """

        self.read_file(path_to_mod) # generates self.mod_content
        self.preprocess() # generates self.blocks
        self.parse() # generates self.ast
        self.generate_python(path_to_template) # generates self.python_content
        self.write_file(path_to_python) # writes self.python_content to path_to_python


class MODFileLoader():

    def __init__(self, config: dict = None):
        
        self.converter = MODFileConverter()

    def load_from_mod(self, path: str) -> None:
        ...

    def load_from_python(self, path: str) -> Mechanism:
        ...
    
    def load_mechanism(self, path: str) -> Mechanism:
        
        self.load_from_mod(path)
        MechanismClass = self.load_from_python(path)
        return MechanismClass()


# class MechanismFactory():

#     def __init__(self):
#         self.class_map = {}

#     def register_mechanism(self, path_to_python: str):
#         module_name = '.'.join(path_to_python.split('/')[:-1])
#         class_name = path_to_python.split('/')[-1].replace('.py', '')
#         MechanismClass = dynamic_import(module_name, class_name)
#         self.class_map[class_name] = MechanismClass

#     def create_mechanism(self, name) -> Mechanism:
#         return self.class_map[name]()

#     def create_ion_channel(self, name) -> IonChannel:
#         return self.class_map[name]()

#     def create_and_standardize_channel(self, name) -> StandardChannel:
#         channel = self.create_ion_channel(name)
#         standard_channel = StandardChannel()
#         data = channel.get_data()
#         standard_channel.fit(data)
#         return standard_channel




class MechanismFactory():
    """
    A high-level class that provides a simple interface to work with .mod files.

    Examples:
       >>> manager = MechanismManager('/path/to/mods', '/path/to/pythons', '/path/to/templates')
       
       # File management: # TODO: pure conversion should be done in the Converter class!
       >>> manager.convert_mod('example.mod', 'example.py', 'template.jinja')
       >>> manager.standardize_mod('example.mod', 'example_out.mod', 'template.jinja')
       
       # Creating a channel:
       >>> channel = manager.create_channel('Nav')
       
       # Creating a standardized channel:
       >>> standard_channel = manager.create_standard_channel('Nav')
    """

    def __init__(self, path_to_mod: str, path_to_python: str, path_to_template: str):

        self.path_to_mod = path_to_mod
        self.path_to_python = path_to_python
        self.path_to_template = path_to_template

        self.converter = MODFileConverter()
        self.loader = MODFileLoader()

        self.class_map = {}

    def _get_path(self, directory: str, filename: str, extension: str = '') -> str:
        return os.path.join(directory, f"{filename}{f'.{extension}' if extension else ''}")

    def _get_mod_path(self, mechanism_name: str) -> str:
        return self._get_path(self.path_to_mod, mechanism_name, 'mod')

    def _get_python_path(self, mechanism_name: str) -> str:
        return self._get_path(self.path_to_python, mechanism_name, 'py')

    def _get_template_path(self, template_name: str, extension: str = 'jinja') -> str:
        return self._get_path(self.path_to_template, template_name, extension)

    def register_mechanism(self, path_to_python: str):
        """
        Registers a mechanism in the class map for later instantiation.

        Parameters
        ----------
        path_to_python : str
            The path to the Python file.
        """
        class_name, module_name, package_path = self._get_module_info(path_to_python)
        sys.path.append(package_path)
        MechanismClass = dynamic_import(module_name, class_name)
        self.class_map[class_name] = MechanismClass

    def _get_module_info(self, path_to_python: str) -> Tuple[str, str, str]:
        module_name = '.'.join(path_to_python.split('/')[:-1])
        class_name = path_to_python.split('/')[-1].replace('.py', '')
        package_path = '/'.join(path_to_python.split('/')[:-1])
        return class_name, module_name, package_path

    def load_mechanism(self, mod_filename: str):
        """
        Load a mechanism from a .mod file to be available in NEURON.
        """
        mod_path = self._get_mod_path(mod_filename)
        self.loader.load_mechanism(mod_path)

    def _instantiate_mechanism(self, name) -> Mechanism:
        return self.class_map[name]()
            
    def create_channel(self, channel_name: str, python_template_filename: str, load: bool = True) -> IonChannel:
        """
        Creates a channel from a .mod file.

        Parameters
        ----------
        channel_name : str
            The name of the channel.
        python_template_filename : str
            The name of the template file to generate the Python code.
        load : bool
            Whether to load the channel in NEURON. The default is True.
        """
        mod_path = self._get_mod_path(channel_name)
        python_path = self._get_python_path(channel_name)
        template_path = self._get_template_path(python_template_filename)

        # Convert mod to python
        self.converter.convert(mod_path, python_path, template_path)

        # Register mechanism
        self.register_mechanism(python_path)

        # Instantiate mechanism
        channel = self.create_mechanism(channel_name)

        # Load mechanism
        if load:
            self.load_mechanism(channel_name)

        return channel
    
    def create_standard_channel(self, channel_name: str, 
                                python_template_filename: str, 
                                mod_template_filename: str = 'standard_channel',
                                load: bool = True) -> StandardIonChannel:
        """
        Creates a standardized channel and fits it to the data of the unstandardized channel.

        Parameters
        ----------
        channel_name : str
            The name of the channel.
        python_template_filename : str
            The name of the template file to generate the Python code.
        mod_template_filename : str
            The name of the template file to generate the .mod file. The default is 'standard_channel'.
        load : bool
            Whether to load the standardized channel in NEURON. The default is True.
        """
        # Check if the unstandardized mechanism is already loaded
        if channel_name not in self.class_map:
            channel = self.create_mechanism(channel_name, python_template_filename, load=False)
        else:
            channel = self._instantiate_mechanism(channel_name)

        # Instantiate the standard channel
        standard_channel = self._standardize(channel)

        # Export the standardized mechanism
        generator = NMODLCodeGenerator()
        mod_path = self._get_mod_path(f"s{channel_name}")
        content = generator.generate(standard_channel, mod_template_filename)
        write_file(mod_path, content)

        # Load the standardized mechanism
        if load: 
            self.load_mechanism(mod_path)

        return standard_channel

    def _standardize(self, channel: IonChannel) -> StandardIonChannel:
        """
        Standardize a channel.

        Note
        ----
        Temperature-dependence is taken into account by performing
        a fit to the data at the temperature specified in the parameters
        of the original channel model.
        """
        standard_channel = StandardIonChannel(name=channel.name, 
                                              state_powers=channel._state_powers, 
                                              ion=channel.ion)

        standard_channel.params.update({'q10': channel.params.get('q10'),
                                        'temp': channel.params.get('temp')})

        fit_temperature = channel.params.get('temp') or 23

        standard_channel.set_tadj(fit_temperature)
        # Fit the standard channel to the data
        data = channel.get_data(temperature=fit_temperature)
        standard_channel.fit(data)

        return standard_channel

    
    def create_ca_dynamics(self, name) -> CaDynamics:
        return CaDynamics(name=name)
import os
import sys
from typing import List, Tuple


from dendrotweaks.membrane.io.converter import MODFileConverter
from dendrotweaks.membrane.io.loader import MODFileLoader
from dendrotweaks.membrane.io.code_generators import NMODLCodeGenerator
from dendrotweaks.membrane.mechanisms import Mechanism, IonChannel, StandardIonChannel, CaDynamics
from dendrotweaks.utils import dynamic_import, write_file


class MechanismFactory():
    """
    A high-level class that provides a simple interface to work with .mod files.

    Parameters
    ----------
    path_to_mod : str
        The path to the directory with the .mod files.
    path_to_python : str
        The path to the directory with the Python files.
    path_to_template : str
        The path to the directory with the template files.


    Examples
    --------
    >>> # Creating a MechanismFactory:
    >>> factory = MechanismFactory('/path/to/mod', '/path/to/python', '/path/to/templates')      
    >>> # Creating a channel:
    >>> channel = factory.create_channel('Nav')
    >>> # Creating a standardized channel:
    >>> standard_channel = factory.create_standard_channel('Nav')
    """

    def __init__(self, path_to_mod: str, path_to_python: str, path_to_template: str):

        self.path_to_mod = path_to_mod
        self.path_to_python = path_to_python
        self.path_to_template = path_to_template

        self.converter = MODFileConverter()
        self.loader = MODFileLoader()

        self.class_map = {}

    def _get_path(self, directory: str, filename: str, extension: str = '', archive: str = '') -> str:
        parts = [directory, archive, f"{filename}.{extension}" if extension else filename]
        return os.path.join(*filter(None, parts))

    def _get_mod_path(self, mechanism_name: str, archive_name: str = '') -> str:
        return self._get_path(self.path_to_mod, mechanism_name, 'mod', archive_name)

    def _get_python_path(self, mechanism_name: str, archive_name: str = '') -> str:
        return self._get_path(self.path_to_python, mechanism_name, 'py', archive_name)

    def _get_template_path(self, template_name: str, extension: str = 'jinja') -> str:
        return self._get_path(self.path_to_template, template_name, extension)

    def _register_mechanism(self, path_to_python: str):
        """
        Registers a mechanism in the class map for later instantiation.

        Parameters
        ----------
        path_to_python : str
            The path to the Python file.
        """
        class_name, module_name, package_path = self._get_module_info(path_to_python)
        print(f"Registering {class_name} from {module_name} in {package_path}")
        sys.path.append(package_path)
        MechanismClass = dynamic_import(module_name, class_name)
        self.class_map[class_name] = MechanismClass

    def list_archives(self):
        self.loader.list_archives(self.path_to_mod)

    def _get_module_info(self, path_to_python: str) -> Tuple[str, str, str]:
        class_name = path_to_python.split('/')[-1].replace('.py', '')
        module_name = class_name
        package_path = '/'.join(path_to_python.split('/')[:-1])
        return class_name, module_name, package_path

    def _instantiate_mechanism(self, name) -> Mechanism:
        return self.class_map[name]()
            
    def create_channel(self, channel_name: str, archive_name: str,
                       python_template_name: str, load: bool = True) -> IonChannel:
        """
        Creates a channel from a .mod file.

        Parameters
        ----------
        channel_name : str
            The name of the channel.
        python_template_name : str
            The name of the template file to generate the Python code.
        load : bool
            Whether to load the channel in NEURON. The default is True.
        """
        mod_path = self._get_mod_path(channel_name, archive_name)
        python_path = self._get_python_path(channel_name, archive_name)
        template_path = self._get_template_path(python_template_name, extension='py')

        # Convert mod to python
        self.converter.convert(mod_path, python_path, template_path)

        # Register mechanism
        self._register_mechanism(python_path)

        # Instantiate mechanism
        channel = self._instantiate_mechanism(channel_name)

        # Load mechanism
        if load:
            self.loader.load_mechanism(mod_path)

        return channel
    
    def create_standard_channel(self, channel_name: str, 
                                archive_name: str,
                                python_template_name: str, 
                                mod_template_name: str = 'standard_channel',
                                load: bool = True) -> StandardIonChannel:
        """
        Creates a standardized channel and fits it to the data of the unstandardized channel.

        Parameters
        ----------
        channel_name : str
            The name of the channel.
        python_template_name : str
            The name of the template file to generate the Python code.
        mod_template_name : str
            The name of the template file to generate the .mod file. The default is 'standard_channel'.
        load : bool
            Whether to load the standardized channel in NEURON. The default is True.
        """
        # Check if the unstandardized mechanism is already loaded
        if channel_name not in self.class_map:
            channel = self.create_channel(channel_name, python_template_name, load=False)
        else:
            channel = self._instantiate_mechanism(channel_name)

        # Instantiate the standard channel
        standard_channel = self._standardize(channel)

        # Export the standardized mechanism
        generator = NMODLCodeGenerator()
        mod_path = self._get_mod_path(f"s{channel_name}")
        template_path = self._get_template_path(mod_template_name, extension='mod')
        content = generator.generate(standard_channel, template_path)
        generator.write_file(mod_path)

        # Load the standardized mechanism
        if load: 
            self.loader.load_mechanism(mod_path)

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
        """
        Create a CaDynamics mechanism.

        Parameters
        ----------
        name : str
            The name of the mechanism.
        """
        return CaDynamics(name=name)
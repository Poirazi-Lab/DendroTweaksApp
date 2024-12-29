import os
import sys
from typing import List, Tuple


from dendrotweaks.membrane.io.converter import MODFileConverter
from dendrotweaks.membrane.io.loader import MODFileLoader
from dendrotweaks.membrane.io.code_generators import NMODLCodeGenerator
from dendrotweaks.membrane.mechanisms import Mechanism, IonChannel, StandardIonChannel
from dendrotweaks.membrane.mechanisms import CaDynamics, LeakChannel
from dendrotweaks.utils import dynamic_import
from dendrotweaks.utils import list_files, list_folders


class MechanismFactory():
    """
    A high-level class that provides a simple interface to work with .mod files.

    Examples
    --------
    >>> # Creating a MechanismFactory:
    >>> factory = MechanismFactory('/path/to/mod', '/path/to/python', '/path/to/templates')      
    >>> # Creating a channel:
    >>> channel = factory.create_channel('Nav')
    >>> # Creating a standardized channel:
    >>> standard_channel = factory.create_standard_channel('Nav')
    """

    def __init__(self):

        self.converter = MODFileConverter()

        self.class_map = {}

    # FACTORY METHODS

    def _register_mechanism(self, path_to_python_file: str):
        """
        Registers a mechanism in the class map for later instantiation.

        Parameters
        ----------
        path_to_python_file : str
            The path to the Python file.
        """
        class_name, module_name, package_path = self._get_module_info(path_to_python_file)
        print(f"Registering {class_name} from {module_name} in {package_path}")
        if not package_path in sys.path:
            sys.path.append(package_path)
        MechanismClass = dynamic_import(module_name, class_name)
        self.class_map[class_name] = MechanismClass

    def _get_module_info(self, path_to_python_file: str) -> Tuple[str, str, str]:
        class_name = os.path.basename(path_to_python_file).replace('.py', '')
        module_name = class_name
        package_path = os.path.dirname(path_to_python_file)
        return class_name, module_name, package_path

    def _instantiate_mechanism(self, class_name) -> Mechanism:
        return self.class_map[class_name]()
            
    def create_channel(self, path_to_mod_file: str,
                       path_to_python_file: str,
                       path_to_python_template: str) -> IonChannel:
        """
        Creates a channel from a .mod file.

        Parameters
        ----------
        path_to_mod_file : str
            The path to the .mod file.
        path_to_python_file : str
            The path to the Python file.
        path_to_python_template : str
            The path to the Python template file.
        """

        # Convert mod to python
        self.converter.convert(path_to_mod_file, 
                               path_to_python_file, 
                               path_to_python_template,
                               verbose=False)

        # Register mechanism
        self._register_mechanism(path_to_python_file)

        # Instantiate mechanism
        class_name = os.path.basename(path_to_python_file).replace('.py', '')
        channel = self._instantiate_mechanism(class_name)

        return channel
    
    def create_standard_channel(self, path_to_mod_file: str,
                                path_to_python_file: str,
                                path_to_python_template: str,
                                path_to_mod_template: str,
                                path_to_standard_mod_file: str) -> StandardIonChannel:
        """
        Creates a standardized channel and fits it to the data of the unstandardized channel.

        Parameters
        ----------
        path_to_mod_file : str
            The path to the .mod file.
        path_to_python_file : str
            The path to the Python file.
        path_to_python_template : str
            The path to the Python template file.
        path_to_mod_template : str
            The path to the .mod template file.
        """
        # Check if the unstandardized mechanism is already loaded
        class_name = os.path.basename(path_to_python_file).replace('.py', '')
        if class_name not in self.class_map:
            channel = self.create_channel(path_to_mod_file,
                                          path_to_python_file,
                                          path_to_python_template,
                                          )
        else:
            channel = self._instantiate_mechanism(class_name)

        # Instantiate the standard channel
        standard_channel = self._standardize(channel)

        # Export the standardized mechanism
        generator = NMODLCodeGenerator()
        content = generator.generate(standard_channel, path_to_mod_template)
        generator.write_file(path_to_standard_mod_file)

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

    def create_leak_channel(self, path_to_mod_file) -> StandardIonChannel:
        """
        Create a leak channel.

        Parameters
        ----------
        name : str
            The name of the channel.
        """
        return LeakChannel()
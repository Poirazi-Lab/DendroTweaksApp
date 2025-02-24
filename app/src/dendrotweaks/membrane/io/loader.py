import os
import shutil
import neuron
from neuron import h

from pprint import pprint

class MODFileLoader():

    def __init__(self):
        self._loaded_mechanisms = set()
              
    # LOADING METHODS

    def _get_mechanism_dir(self, path_to_mod_file: str) -> str:
        """
        Get the subdirectory for the given mod file.

        Parameters
        ----------
        path_to_mod_file : str
            Path to the .mod file.

        Returns
        -------
        str
            Path to the subdirectory for the mechanism.
        """
        mechanism_name = os.path.basename(path_to_mod_file).replace('.mod', '')
        parent_dir = os.path.dirname(path_to_mod_file)
        return os.path.join(parent_dir, mechanism_name)

    def load_mechanism(self, path_to_mod_file: str, recompile: bool = False) -> None:
        """
        Load a mechanism from the specified mod file.

        Parameters
        ----------
        path_to_mod_file : str
            Path to the .mod file.
        recompile : bool
            Force recompilation even if already compiled.
        """
        mechanism_name = os.path.basename(path_to_mod_file).replace('.mod', '')
        mechanism_dir = self._get_mechanism_dir(path_to_mod_file)
        x86_64_dir = os.path.join(mechanism_dir, 'x86_64')

        print(f"{'=' * 60}\nAdding mechanism {mechanism_name} to model...\n{'=' * 60}")

        if mechanism_name in self._loaded_mechanisms:
            print(f'Mechanism "{mechanism_name}" already loaded')
            return

        if recompile and os.path.exists(mechanism_dir):
            shutil.rmtree(mechanism_dir)

        if not os.path.exists(x86_64_dir):
            print(f'Compiling mechanism "{mechanism_name}"...')
            os.makedirs(mechanism_dir, exist_ok=True)
            shutil.copy(path_to_mod_file, mechanism_dir)
            self._compile_files(mechanism_dir)
        else:
            print(f'Using precompiled mechanism "{mechanism_name}"')

        if hasattr(h, mechanism_name):
            print(f'Mechanism "{mechanism_name}" already exists in hoc')
        else:
            neuron.load_mechanisms(mechanism_dir)
        self._loaded_mechanisms.add(mechanism_name)
        print(f'Loaded mechanism "{mechanism_name}"')

    # HELPER METHODS

    def _compile_files(self, path: str) -> None:
        """
        Compile the mod files in the specified directory.

        Parameters
        ----------
        path : str
            The path to the directory with the mod files.
        """
        cwd = os.getcwd()
        os.chdir(path)
        os.system('nrnivmodl')
        os.chdir(cwd)
        print(f'Compiled mod files from "{path}"')

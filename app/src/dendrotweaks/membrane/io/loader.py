import os
from pprint import pprint

class MODFileLoader():

    def __init__(self):
        self._loaded_mechnisms = []
              
    # LOADING METHODS

    def load_mechanism(self, path_to_mod_file: str, recompile=True) -> None:
        """
        Load a mechanism from the specified mod file.

        Parameters
        ----------
        path_to_mod_file : str
            The path to the mod file.
        """
        temp_dir = self._create_temp_dir(path_to_mod_file)
        
        if path_to_mod_file in self._loaded_mechnisms:
            print(f'Mechanism "{path_to_mod_file}" already loaded')
            return
        self._loaded_mechnisms.append(path_to_mod_file)

        import neuron
        from neuron import h

        mechanism_name = path_to_mod_file.split('/')[-1].replace('.mod', '')

        if hasattr(h, mechanism_name):
            print(f'Mechanism "{mechanism_name}" already loaded')
            return

        if recompile or not os.path.exists(os.path.join(temp_dir, 'x86_64')):
            self._compile_files(temp_dir)

        neuron.load_mechanisms(temp_dir)
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

        if os.path.exists(os.path.join(path, 'x86_64')):
            import shutil
            shutil.rmtree(os.path.join(path, 'x86_64'))

        cwd = os.getcwd()
        os.chdir(path)
        os.system('nrnivmodl')
        os.chdir(cwd)
        print(f'Compiled mod files from "{path}"')

    def _create_temp_dir(self, path_to_mod_file: str) -> str:
        """
        Creates a temporary directory for each channel.

        Parameters
        ----------
        path_to_mod : str
            The path to the directory with the mod files.
        """
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()
        shutil.copy(path_to_mod_file, temp_dir)
        return temp_dir

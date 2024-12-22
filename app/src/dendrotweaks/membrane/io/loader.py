from chanopy.utils import list_folders, list_files
import os
from pprint import pprint

class Loader():

    def __init__(self):
        self._loaded_archives = ['test']
        self.archives = {}


    def list_archives(self, path_to_data: str = None):
        folders = list_folders(path_to_data)
        print(f"Available archives in\n{path_to_data}/\n")
        
        for idx, folder in enumerate(folders):
            # Check if the folder is loaded
            loaded_marker = " [LOADED]" if folder in self._loaded_archives else ""
            
            # Determine if this is the last folder
            folder_prefix = "└──" if idx == len(folders) - 1 else "├──"
            print(f"{folder_prefix} {folder}/{loaded_marker}")
            
            path_to_archive = os.path.join(path_to_data, folder)
            files = list_files(path_to_archive, extension='.mod')
            
            # Print the files in the folder with proper tree structure
            for i, file in enumerate(files):
                file_prefix = "└──" if i == len(files) - 1 else "├──"
                connector = "│" if idx != len(folders) - 1 else " "
                print(f"{connector}   {file_prefix} {file.split('.')[0]}")
            
            # Store the archives
            self.archives[folder] = [f.split('.')[0] for f in files]
              
        

    def load_archive(self, path_to_archive, recompile=True):

        archive_name = path_to_archive.split('/')[-1]

        if archive_name in self._loaded_archives:
            print(f'Archive "{archive_name}" already loaded')
            return
        self._loaded_archives.append(archive_name)

        import neuron
        from neuron import h

        if all([hasattr(h, name) for name in self.archives[archive_name]]):
            print(f'Mechanisms already loaded from "{path_to_archive}"')
            return

        if recompile or not os.path.exists(os.path.join(path_to_archive, 'x86_64')):
            self._compile_archive(path_to_archive)

        neuron.load_mechanisms(path_to_archive)
        print(f'Loaded mechanisms from "{path_to_archive}"')

    def _compile_archive(self, path_to_archive):
        """
        Compile all mod files in the specified archive using nrnivmodl.

        Parameters
        ----------
        archive : str
            Name of the archive to compile.
        """

        if os.path.exists(os.path.join(path_to_archive, 'x86_64')):
            import shutil
            shutil.rmtree(os.path.join(path_to_archive, 'x86_64'))

        cwd = os.getcwd()
        os.chdir(path_to_archive)
        os.system('nrnivmodl')
        os.chdir(cwd)
        print(f'Compiled mod files from "{path_to_archive}"')

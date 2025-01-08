import os
from typing import List, Dict

class PathManager:
    """
    A versatile manager for handling file and directory paths related to modeling data.
    """
    def __init__(self, path_to_data: str):
        self.path_to_data = path_to_data
        self.paths = {
            'mod': os.path.join(path_to_data, 'mod'),
            'python': os.path.join(path_to_data, 'python'),
            'templates': os.path.join(path_to_data, 'templates'),
            'swc': os.path.join(path_to_data, 'swc'),
            'csv': os.path.join(path_to_data, 'csv'),
            'json': os.path.join(path_to_data, 'json'),
        }

    def __repr__(self):
        return f"PathManager({self.path_to_data})"

    def get_path(self, file_type: str, file_name: str, archive: str = "") -> str:
        """
        Get the full path to a file of a given type (e.g., mod, python, templates).
        
        Parameters:
        - file_type: The type of file (e.g., 'mod', 'python').
        - file_name: The name of the file without extension.
        - archive: The optional subdirectory within the file type (e.g., archive name for mod files).
        
        Returns:
        - str: The constructed file path.
        """
        directory = self.paths.get(file_type)
        if not directory:
            raise ValueError(f"Unknown file type: {file_type}")
        return os.path.join(directory, archive, file_name)

    def get_file_path(self, file_type: str, filename: str, extension: str, archive: str = "") -> str:
        """
        Construct a file path with an extension for a specific type and archive.
        """
        if not filename.endswith(f".{extension}"):
            filename_with_extension = f"{filename}.{extension}" if extension else filename
        else:
            filename_with_extension = filename
        return self.get_path(file_type, filename_with_extension, archive)

    def list_files(self, file_type: str, archive: str = "", extension: str = "") -> List[str]:
        """
        List all files of a given type and optional archive.
        
        Parameters:
        - file_type: The type of files to list (e.g., 'mod').
        - archive: The optional subdirectory within the type.
        - extension: File extension to filter by (e.g., 'mod').
        
        Returns:
        - List[str]: A list of file names with the specified extension.
        """
        directory = os.path.join(self.paths.get(file_type, ""), archive)
        if not os.path.isdir(directory):
            return []
        return [f.replace(extension, '') 
                for f in os.listdir(directory) if f.endswith(extension)]

    def list_archives(self) -> Dict[str, List[str]]:
        """
        List all archives and their mod files.
        
        Returns:
        - Dict[str, List[str]]: A dictionary mapping archive names to lists of mod files.
        """
        archives = {}
        mod_dir = self.paths['mod']
        for archive in os.listdir(mod_dir):
            archive_path = os.path.join(mod_dir, archive)
            if os.path.isdir(archive_path):
                archives[archive] = self.list_files('mod', archive, extension='.mod')
        return archives

    def list_swc(self) -> List[str]:
        """
        List all SWC files.
        
        Returns:
        - List[str]: A list of SWC file names.
        """
        return self.list_files('swc', extension='.swc')

    def print_directory_tree(self, file_type: str) -> None:
        """
        Print a directory tree for a given file type.
        
        Parameters:
        - file_type: The type of files (e.g., 'mod', 'swc').
        """
        base_path = self.paths.get(file_type)
        if not base_path or not os.path.isdir(base_path):
            print(f"Directory for {file_type} does not exist.")
            return

        def print_tree(path, prefix=""):
            items = os.listdir(path)
            for idx, item in enumerate(sorted(items)):
                is_last = idx == len(items) - 1
                connector = "└──" if is_last else "├──"
                item_path = os.path.join(path, item)
                print(f"{prefix}{connector} {item}")
                if os.path.isdir(item_path) and not item.startswith('x86_64'):
                    extension = "│   " if not is_last else "    "
                    print_tree(item_path, prefix + extension)

        print_tree(base_path)

    def get_channel_paths(self, mechanism_name: str, 
                          archive_name: str = "", 
                          python_template_name: str = "default") -> Dict[str, str]:
        """
        Get all necessary paths for creating a channel.
        """
        return {
            'path_to_mod_file': self.get_file_path('mod', mechanism_name, 'mod', archive_name),
            'path_to_python_file': self.get_file_path('python', mechanism_name, 'py'),
            'path_to_python_template': self.get_file_path('templates', python_template_name, 'py'),
        }

    def get_standard_channel_paths(self, mechanism_name: str, archive_name: str = "", 
                                   python_template_name: str = "default",
                                   mod_template_name: str = "default") -> Dict[str, str]:
        """
        Get all necessary paths for creating a standard channel.
        """
        return {
            **self.get_channel_paths(mechanism_name, archive_name, python_template_name),
            'path_to_mod_template': self.get_file_path('templates', mod_template_name, 'mod'),
            'path_to_standard_mod_file': self.get_file_path('mod', f"s{mechanism_name}", 'mod', archive_name),
        }
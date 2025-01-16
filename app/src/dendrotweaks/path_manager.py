import os
from typing import List, Dict

class PathManager:
    """
    A versatile manager for handling file and directory paths related to modeling data.
    """
    def __init__(self, path_to_data: str, model_name: str = None):
        self.path_to_data = path_to_data
        self.model_name = model_name
        self.paths = {
            'default_mod': os.path.join(path_to_data, 'Default'),
            'templates': os.path.join(path_to_data, 'Templates'),
        }
        if model_name:
            self.update_paths(model_name)

    def update_paths(self, model_name: str):
        """
        Set the paths for the given model name and data path.
        
        Parameters:
        - model_name: The name of the model.
        - path_to_data: The base path to the data.
        """
        self.paths.update({
            'model': os.path.join(self.path_to_data, model_name),
            'mod': os.path.join(self.path_to_data, model_name, 'mod'),
            'python': os.path.join(self.path_to_data, model_name, 'python'),
            'swc': os.path.join(self.path_to_data, model_name, 'swc'),
            'csv': os.path.join(self.path_to_data, model_name, 'csv'),
            'json': os.path.join(self.path_to_data, model_name, 'json'),
        })

    def __repr__(self):
        return f"PathManager({self.path_to_data}/{self.model_name})"

    def list_models(self) -> List[str]:
        """
        List all model files.
        
        Returns:
        - List[str]: A list of model file names.
        """
        DIRS_TO_IGNORE = ['Default', 'Templates']
        return [f for f in os.listdir(self.path_to_data)
                if os.path.isdir(os.path.join(self.path_to_data, f))
                and f not in DIRS_TO_IGNORE]

    def get_path(self, file_type: str) -> str:
        """
        Get the path for a specific file type.
        
        Parameters:
        - file_type: The type of file (e.g., 'mod', 'swc').
        
        Returns:
        - str: The path to the file type.
        """
        path = self.paths.get(file_type, None)
        if os.path.isdir(path):
            return path
        raise FileNotFoundError(f"Directory for {file_type} does not exist.")

    def get_file_path(self, file_type: str, file_name: str, extension: str) -> str:
        """
        Construct a file path with an optional extension for a specific type.
        
        Parameters:
        - file_type: The type of file (e.g., 'mod', 'swc').
        - filename: The name of the file.
        - extension: The file extension.
        
        Returns:
        - str: The constructed file path.
        """
        dir_path = self.get_path(file_type)
        file_name = f"{file_name}.{extension}"
        return os.path.join(dir_path, file_name)

    def list_files(self, file_type: str, extension: str = "") -> List[str]:
        """
        List all files of a given type and optional archive.
        
        Parameters:
        - file_type: The type of files to list (e.g., 'mod').
        - archive: The optional subdirectory within the type.
        - extension: File extension to filter by (e.g., 'mod').
        
        Returns:
        - List[str]: A list of file names with the specified extension.
        """
        directory = self.paths.get(file_type, "")
        if not extension.startswith('.'): extension = f".{extension}"
        if not os.path.isdir(directory):
            return []
        return [f.replace(extension, '') 
                for f in os.listdir(directory) if f.endswith(extension)]


    def print_directory_tree(self, subfolder=None) -> None:
        """
        Print a directory tree for a given file type.
        
        Parameters:
        - file_type: The type of files (e.g., 'mod', 'swc').
        """
        base_path = self.paths.get('model') if not subfolder else self.paths.get(subfolder)
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
                          python_template_name: str = "default") -> Dict[str, str]:
        """
        Get all necessary paths for creating a channel.
        """
        return {
            'path_to_mod_file': self.get_file_path('mod', mechanism_name, 'mod'),
            'path_to_python_file': self.get_file_path('python', mechanism_name, 'py'),
            'path_to_python_template': self.get_file_path('templates', python_template_name, 'py'),
        }

    def get_standard_channel_paths(self, mechanism_name: str,
                                   python_template_name: str = "default",
                                   mod_template_name: str = "default") -> Dict[str, str]:
        """
        Get all necessary paths for creating a standard channel.
        """
        return {
            **self.get_channel_paths(mechanism_name, python_template_name),
            'path_to_mod_template': self.get_file_path('templates', mod_template_name, 'mod'),
            'path_to_standard_mod_file': self.get_file_path('mod', f"s{mechanism_name}", 'mod'),
        }
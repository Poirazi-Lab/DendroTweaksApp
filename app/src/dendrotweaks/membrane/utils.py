import os


def list_folders(path_to_folder):
    folders = [f for f in os.listdir(path_to_folder)
               if os.path.isdir(os.path.join(path_to_folder, f))]
    sorted_folders = sorted(folders, key=lambda x: x.lower())
    return sorted_folders


def list_files(path_to_folder, extension):
    files = [f for f in os.listdir(path_to_folder)
             if f.endswith(extension)]
    return files
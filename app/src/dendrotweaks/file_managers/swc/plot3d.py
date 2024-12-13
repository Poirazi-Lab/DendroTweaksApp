import sys
sys.path.append('/home/roman/Documents/code/DendroTweaks/app/src/')
from dendrotweaks.file_managers.swc import SWCManager
import argparse
import os

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Show 3D morphology from SWC file.')
    parser.add_argument('file_path', type=str, help='Path to the SWC file')
    args = parser.parse_args()

    print(f'Plotting 3D morphology from {args.file_path}...')

    swcm = SWCManager()

    path_to_data, file_name = os.path.split(args.file_path)
    swcm.path_to_data = path_to_data.replace('/swc', '')   
    swcm.read(file_name)

    swcm.build_swc_tree()
    swcm.postprocess_swc_tree(sort=True, split=True, shift=True, extend=True)
    swcm.build_sec_tree()

    swcm.plot_3d()
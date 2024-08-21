import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from collections import defaultdict
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import Axes3D

from scipy.interpolate import griddata

from utils import get_sec_name, get_sec_type, get_sec_id, get_seg_name

from functools import cached_property

        
SWC_TYPES = {0: 'undefined', 1: 'soma', 2: 'axon', 3: 'dendrite', 4: 'apical dendrite', 5: 'custom'}


class SWCSection():
    def __init__(self, data: dict):
        if isinstance(data, pd.DataFrame):
            self.df = data
        elif isinstance(data, dict):
            self.df = pd.DataFrame(data).set_index('ID', drop=True)
        else:
            raise ValueError('Data should be a DataFrame or a dictionary')
        self.df.sort_index(ascending=True, inplace=True)
        self.df['Type'] = self.df['Type'].astype(int)
        self.df[['X', 'Y', 'Z', 'R']] = self.df[['X', 'Y', 'Z', 'R']].astype(float)
        self.df['Parent'] = self.df['Parent'].astype(int)
        self.parent = None
        self.children = []


    @property
    def subtree(self):
        subtree = [self]
        for child in self.children:
            subtree.extend(child.subtree)
        return subtree
        
    
    def info(self):
        return {'Type': SWC_TYPES[self.df['Type'].iloc[0]],
                    'ID': f'{self.df.index[0]} → {self.df.index[-1]} ({len(self.df)})',
                    'Parent': self.parent.df.index[0] if self.parent is not None else None,
                    'Children': [child.df.index[0] for child in self.children] if self.children else None}
        
    
    def print_sec(self, parent=True, children=False):
        if parent and self.parent is not None:
            print('Parent:\n', self.parent.df, '\n---------------------------------')
        print('Section:\n', self.df, '\n---------------------------------')
        if children and self.children:
            print('Children:')
            for child in self.children: print(child.df, '\n---------------------------------')


    def _setup_plot(self, ax, figsize=[5, 5], **kwargs):
        if ax is not None:
            plt.sca(ax)
        else:
            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(111, **kwargs)
        return ax


    def plot_sec(self, ax=None, parent=True, shift=False, fill_color='orange', line_color='red'):
        
        ax = self._setup_plot(ax, figsize=[5,2])

        def _get_distances(sec, shift):
            if sec.parent is not None:
                parent_distances = calculate_distances(sec.parent.df.X, sec.parent.df.Y, sec.parent.df.Z)
                # print(f'Parent distances: {parent_distances}')
            
                connection_idx = _find_connection_idx(sec)

                if not sec.parent.df[['X', 'Y', 'Z']].iloc[connection_idx].equals(sec.df[['X', 'Y', 'Z']].iloc[0]):
                    # print('Coordinates do not match')
                    
                    distances = calculate_distances(pd.concat([sec.parent.df.X.iloc[connection_idx:connection_idx+1], self.df.X]),
                                                    pd.concat([sec.parent.df.Y.iloc[connection_idx:connection_idx+1], self.df.Y]),
                                                    pd.concat([sec.parent.df.Z.iloc[connection_idx:connection_idx+1], self.df.Z]))
                    
                    # print(f'Distances 1: {distances}')
                    missing_distances = distances[:2]
                    distances = distances[1:]
                    
                    missing_radii = [sec.parent.df.R.iloc[connection_idx], sec.df.R.iloc[0]]
                else:
                    # print('Coordinates match')
                    distances = calculate_distances(sec.df.X, sec.df.Y, sec.df.Z)
                    
                    missing_distances = np.array([])
                    missing_radii = np.array([])
                    
                
            else:
                if self.df['Parent'].tolist() == [-1, 1, 1]:
                    distances = [-self.df.R.iloc[0], 0, self.df.R.iloc[0]]
                    
                else:
                    distances = calculate_distances(sec.df.X, sec.df.Y, sec.df.Z)
                missing_distances = np.array([])
                missing_radii = np.array([])

            # print()
            # print(f'Missing distances: {missing_distances}')
            # print(f'Distances: {distances}')
            # print()
            if shift:
                shift_ = distances[-1]
                # print(f'Shifting {distances} by {shift_}')
                distances = [d - shift_ for d in distances]
                if self.df['Parent'].tolist() == [-1, 1, 1]:
                    distances = [d + shift_ for d in distances]
                # print(f'Distances: {distances}')
                
                if missing_distances:
                    # print(f'Shifting {missing_distances} by {shift_}')
                    missing_distances = [d - shift_ for d in missing_distances]
                    # print(f'Missing distances: {missing_distances}')
            
            return distances, missing_distances, missing_radii
                
        def _find_connection_idx(sec):
            connection_idx =  np.where(sec.parent.df.index == sec.df['Parent'].iloc[0])
            if connection_idx[0].size > 1:
                raise ValueError(f'More than one connection index found: {connection_idx}')
            elif connection_idx[0].size == 0:
                raise ValueError(f'No connection index found')
            else:
                return connection_idx[0][0]
            

        if parent and self.parent is not None:
            self.parent.plot_sec(ax, parent=False, shift=True, fill_color='dodgerblue', line_color='blue')
            
        distances, missing_distances, missing_radii = _get_distances(self, shift)

        if missing_distances:
            plt.fill_between(missing_distances, 
                             np.zeros_like(missing_distances),
                             missing_radii, color=fill_color, alpha=0.3, edgecolor='None')
            
        plt.fill_between(distances, np.zeros_like(distances), self.df.R, color=fill_color, alpha=.8, edgecolor='None')
        new_radii = linear_regression(distances, self.df.R)
        plt.plot(distances, new_radii, color=line_color, linestyle='--', alpha=0.5)


        # for d in distances:
            # plt.axvline(d, color=line_color, linestyle='--', alpha=0.1)
        plt.plot(distances, self.df.R, '.', color='#019E73')
            
            
        
        ax.set_title(f'type: {self.info()["Type"]}, ID: {self.info()["ID"]}, \nParent: {self.info()["Parent"]}, Children: {self.info()["Children"]}')
        

    def plot_sec_3d(self, ax=None, parent=False, children=False, projection='', line_color='orange', marker_color='red'):

        ax = self._setup_plot(ax, projection='3d', aspect='equal')
        
        ax.plot(self.df.X, self.df.Y, self.df.Z, label=f'Sec {self.df.index[0]}-{self.df.index[-1]}[{len(self.df)}] ← {self.df.Parent.iloc[0]}', color=line_color)
        ax.scatter(self.df.X, self.df.Y, self.df.Z, c=marker_color, s=5)
        if children and self.children:
            for child in self.children:
                child.plot_sec_3d(ax, children=False, parent=False, line_color='lawngreen', marker_color='green')
        #connect parent to children
            # for child in self.children:
            #     parent_idx = find_parent_idx(child.df, parent=self.df)
            #     ax.plot([self.df.X.iloc[parent_idx], child.df.X.iloc[0]], [self.df.Y.iloc[parent_idx], child.df.Y.iloc[0]], [self.df.Z.iloc[parent_idx], child.df.Z.iloc[0]], color='lawngreen', linestyle='--')
        if self.parent is not None:
            if parent:
                self.parent.plot_sec_3d(ax, parent=False, children=False, line_color='dodgerblue', marker_color='blue')
            #connect sec to parent
            #check if any points of sec are connected to parent
            parent_idx = find_parent_idx(self.df, parent=self.parent.df)
            if self.df[['X', 'Y', 'Z']].iloc[0].equals(self.parent.df[['X', 'Y', 'Z']].iloc[parent_idx]):
                pass
            else:
                ax.plot([self.df.X.iloc[0], self.parent.df.X.iloc[parent_idx]], [self.df.Y.iloc[0], self.parent.df.Y.iloc[parent_idx]], [self.df.Z.iloc[0], self.parent.df.Z.iloc[parent_idx]], color=line_color, linestyle='--')
        
        
        if projection == 'XY':
            ax.view_init(90, -90)

        data = [self.df]

        if self.children:
            data.extend([child.df for child in self.children])
        if self.parent is not None:
            data.append(self.parent.df)
        
        if children or parent:
            merged_data = pd.concat(data)
            adjust_limits(merged_data, ax)
            ax.legend()



class SWCManager():

    SWC_TYPES = {'soma':1, 'axon':2, 'dend':3, 'apic':4}

    def __init__(self):
        self._swc = None
        self.sections = []


    @property
    def df(self):
        return pd.concat([sec.df for sec in self.sections])


    @property
    def soma(self):
        soma = [sec for sec in self.sections if (sec.df['Type'] == 1).all()]
        if len(soma) == 1:
            return soma[0]
        elif len(soma) > 1:
            raise ValueError('Multiple soma sections found')
        else:
            raise ValueError('No soma section found')


    @soma.setter
    def soma(self, new_soma_df):
        # replace the old soma section with the new one
        self.sections = [new_soma_df if (sec.df['Type'] == 1).all() else sec for sec in self.sections]
        

    @property
    def soma_notation(self):
        if len(self.soma.df) == 1:
            return '1PS'
        elif len(self.soma.df) == 3 and self.soma.df['Parent'].tolist() == [-1, 1, 1]:
            return '3PS'
        else:
            return 'contour'


    @property
    def soma_center(self):
        return self.soma.df[['X', 'Y', 'Z']].mean()


    @property
    def apical_center(self):
        df_apical = self.df[self.df['Type'] == 4]
        if len(df_apical) == 0:
            return None
        apical_center = df_apical[['X', 'Y', 'Z']].mean()
        return apical_center


    def load_swc(self, swc):
        self._swc = swc
        with open(self._swc) as f:
            content = f.read()
        data = content.split('\n')
        data = [line for line in data if '#' not in line]
        self._df = pd.read_csv(io.StringIO('\n'.join(data)), delim_whitespace=True, names=['ID', 'Type', 'X', 'Y', 'Z', 'R', 'Parent'])
        

    def plot_raw(self, drop = [], ax=None, projection='XY'):
        if ax is not None:
            plt.sca(ax)
        else:
            fig = plt.figure(figsize=(10, 10))
            ax = fig.add_subplot(111, projection='3d')
        for sec_type in self._df['Type'].unique():
            if not sec_type in drop:
                type_df = self._df[self._df['Type'] == sec_type]
                ax.scatter(type_df['X'], type_df['Y'], type_df['Z'], label=f'Type {sec_type}', s=5)
        if projection == 'XY':
            ax.view_init(90, -90)
        elif projection == 'ZY':
            ax.view_init(0, 0)
        adjust_limits(self._df[~self._df.Type.isin(drop)], ax)
        ax.legend()

    def sec_to_df(self, sec, parent_id, root_id, drop_first, drop_last):

        connections = set([child.parentseg().x for child in sec.children()])
        
        swc_type = self.SWC_TYPES.get(get_sec_type(sec), 0)
        if not swc_type:
            raise ValueError(f'Unknown section type: {get_sec_type(sec)}. Update self.SWC_TYPES dictionary.')

        data = {
            'ID': [i + root_id for i in range(sec.n3d())],
            'Type': [swc_type for i in range(sec.n3d())],
            'X': [sec.x3d(i) for i in range(sec.n3d())],
            'Y': [sec.y3d(i) for i in range(sec.n3d())],
            'Z': [sec.z3d(i) for i in range(sec.n3d())],
            'R': [sec.diam3d(i)/2 for i in range(sec.n3d())],
            'Parent': [parent_id] + [i + root_id for i in range(sec.n3d() - 1)]
        }

        if 0.5 in connections and sec.n3d() == 2:
            # insert a point in the middle of the section
            data['ID'].insert(1, root_id + 1)
            data['ID'][2] = root_id + 2
            data['Type'].insert(1, swc_type)
            data['X'].insert(1, sec.x3d(0) + (sec.x3d(1) - sec.x3d(0))/2)
            data['Y'].insert(1, sec.y3d(0) + (sec.y3d(1) - sec.y3d(0))/2)
            data['Z'].insert(1, sec.z3d(0) + (sec.z3d(1) - sec.z3d(0))/2)
            data['R'].insert(1, sec.diam3d(0)/2)
            data['Parent'].insert(1, root_id)
            data['Parent'][2] = root_id + 1

        
        sec_df = pd.DataFrame(data = data).set_index('ID', drop=True)

        if drop_first:
            sec_df.index -= 1
            sec_df.iloc[1, -1] = sec_df.iloc[0, -1]
            sec_df.iloc[2:, -1] = sec_df.iloc[2:, -1].apply(lambda x: x-1)
            sec_df.drop(sec_df.index[0], inplace=True)
            
        # sec_df.index += root_id
        sec_df.iloc[:,1:] = sec_df.iloc[:,1:].apply(lambda x: np.round(x, 5))

        if drop_last:
            sec_df.drop(sec_df.index[-1], inplace=True)

        parent_ids = {f'{get_sec_name(sec)}(0.0)': sec_df.index[0], f'{get_sec_name(sec)}(1.0)': sec_df.index[-1]} 
        if 0.5 in connections and sec.n3d() == 3:
            parent_ids.update({f'{get_sec_name(sec)}(0.5)': sec_df.index[1]})

        return sec_df, parent_ids

    def from_hoc(self, hoc_sections, soma_format='3PS'):
        
        parents = dict()

        for sec in hoc_sections:
            if sec.n3d():
                if sec.parentseg():
                    parent_id = parents[get_seg_name(sec.parentseg())]
                    # print(parent_id)
                    df_sec, parent_ids = self.sec_to_df(sec, 
                                            parent_id=parent_id, 
                                            root_id=self.df.index[-1] + 1,
                                            drop_first=True, # True?
                                            drop_last=False)
                else:
                # In case of soma
                    df_sec, parent_ids = self.sec_to_df(sec,
                                            parent_id=-1, 
                                            root_id=1,
                                            drop_first=False,
                                            drop_last=False)
                    if soma_format == '3PS':
                        df_sec = df_sec.reindex([2,1,3])
                        df_sec.index = [1,2,3]
                        df_sec['Parent'] = [-1, 1, 1]
                        

                self.sections.append(SWCSection(df_sec))

                parents.update(parent_ids)

        for sec in self.sections:
            sec.parent = self.find_parent(sec)
            sec.children = self.find_children(sec)
                

    @cached_property
    def children_dict(self):
        return self._df.groupby('Parent')['ID'].apply(list).to_dict()


    def build_section(self, idx, new_idx=1, new_parent_idx=-1, column_names=[], type_correction=-1):
        # print(f'Building section {idx} new: {new_idx}, parent: {new_parent_idx}')

        # 1. Initialize the section
        new_section_ids = [new_idx]
        columns = {name: [self._df.loc[self._df['ID'] == idx, name].values[0]] for name in column_names}
        children_ids = self.children_dict.get(idx, [])

        # 2. Traverse the tree until a bifurcation is reached
        while len(children_ids) == 1:
            idx = children_ids[0]
            new_idx += 1
            new_section_ids.append(new_idx)
            for name in column_names:
                columns[name].append(self._df.loc[self._df['ID'] == idx, name].values[0])
            if 'Type' in columns and type_correction is not None: 
                columns['Type'] = [columns['Type'][type_correction]] * len(columns['Type'])
            children_ids = self.children_dict.get(idx, [])

        # print(f'New section: {new_section_ids}')
        # print(f'Children: {children_ids}')

        # 3. On bifurcation
        if len(children_ids) > 1:
            parent_idx = new_idx
            for child_idx in children_ids:
                # new_idx is needed for the next child
                new_idx = self.build_section(idx=child_idx, new_idx=new_idx+1, new_parent_idx=parent_idx, column_names=column_names)

        # 4. Update the parent index
        new_parent_column = [new_parent_idx] + new_section_ids[:-1]
        sec_dict = {'ID':new_section_ids, **columns, 'Parent':new_parent_column}
        self.sections.append(sec_dict)
        return new_idx


    def build_tree(self, idx, new_idx=1, new_parent_idx=-1, column_names=['Type', 'X', 'Y', 'Z', 'R']):

        # 1. Recursively build the tree
        self.build_section(idx=idx,
                           new_idx=new_idx, 
                           new_parent_idx=new_parent_idx, 
                           column_names=column_names)

        # 2. Merge soma sections if multiple (e.g. 3PS notation)
        if 'Type' in self._df.columns:
            
            soma_sections = []
            non_soma_sections = []
            for section in self.sections:
                if all(value == 1 for value in section['Type']):
                    soma_sections.append(section)
                else:
                    non_soma_sections.append(section)
            if len(soma_sections) > 1:
                soma_section = defaultdict(list)
                for section in soma_sections:
                    for key in section:
                        soma_section[key].extend(section[key])
                self.sections = [dict(soma_section)] + non_soma_sections
                

        # 3. Sort the sections
        self.sections = sorted(self.sections, key=lambda x: x['ID'][0])

        # 4. Convert the sections to SWCSection objects
        self.sections = [SWCSection(sec_dict) for sec_dict in self.sections]
            
        # 5. Update the parent and children attributes
        for sec in self.sections:
            sec.parent = self.find_parent(sec)
            sec.children = self.find_children(sec)


    def find_parent(self, sec):
        parents = [s for s in self.sections if (s is not sec) and (sec.df['Parent'].isin(s.df.index).any())]
        if len(parents) == 1:
            return parents[0]
        elif len(parents) > 1:
            for parent in parents:
                print(parent.df)
            raise ValueError(f'Multiple parents found for section {sec}')
        else:
            return None


    def find_children(self, sec):
        return [s for s in self.sections if (s is not sec) and (s.df['Parent'].isin(sec.df.index).any())]


    def from_swc(self, path, idx=1, **kwargs):
        self.load_swc(path)
        self.build_tree(idx=idx, **kwargs)


    def shift_to_soma_center(self):
        soma_x, soma_y, soma_z = self.soma_center
        for sec in self.sections:
            sec.df['X'] = sec.df['X'] - soma_x
            sec.df['Y'] = sec.df['Y'] - soma_y
            sec.df['Z'] = sec.df['Z'] - soma_z

    def align_apical_tree(self):
        # Calculate the rotation vector and angle
        from scipy.spatial.transform import Rotation

        soma_center = self.soma_center
        apical_center = self.apical_center

        rotation_vector = np.cross([0, 1, 0], apical_center - soma_center)
        rotation_angle = np.arccos(np.dot([0, 1, 0], (apical_center - soma_center) / np.linalg.norm(apical_center - soma_center)))
        
        # Create the rotation matrix
        rotation_matrix = Rotation.from_rotvec(rotation_angle * rotation_vector / np.linalg.norm(rotation_vector)).as_matrix()
        
        # Apply the rotation to each point
        # self.df[['X', 'Y', 'Z']] = df[['X', 'Y', 'Z']].dot(rotation_matrix)
        for sec in self.sections:
            sec.df[['X', 'Y', 'Z']] = sec.df[['X', 'Y', 'Z']].dot(rotation_matrix)

        

    def round_coordinates(self, decimals=5):
        for sec in self.sections:
            sec.df[['X', 'Y', 'Z']] = sec.df[['X', 'Y', 'Z']].round(decimals=decimals)
            sec.df[['X', 'Y', 'Z']] = sec.df[['X', 'Y', 'Z']].where(~np.isclose(sec.df[['X', 'Y', 'Z']], 0), 0)
        


    def soma_to_3PS_notation(self, soma_idx=1):

        if self.soma_notation == '3PS':
            print('Soma is already in 3PS notation')
            return
        
        soma3 = {'ID': [soma_idx, soma_idx+1, soma_idx+2],}
        
        soma3['Type'] = [1, 1, 1]

        old_soma_len = len(self.soma.df)
        start_idx = self.soma.df.index[-1] + 1

        if self.soma_notation == '1PS':
            r = self.soma.df.loc[1, 'R']
            soma3['X'] = [self.soma.df.loc[1, 'X']] * 3
            soma3['Y'] = [self.soma.df.loc[1, 'Y'], self.soma.df.loc[1, 'Y'] - r, self.soma.df.loc[1, 'Y'] + r]
            soma3['Z'] = [self.soma.df.loc[1, 'Z'], self.soma.df.loc[1, 'Z'], self.soma.df.loc[1, 'Z']]
            df_soma3['R'] = [r]*3
            
        elif self.soma_notation == 'contour':
            distances = []
            for i, row in self.soma.df.iterrows():
                point = (row['X'], row['Y'], row['Z'])
                distances.append(distance_3d(point, self.soma_center))
            std_dev = np.std(distances)
            if std_dev > 0.1:
                print('Soma is not a contour')
                # in not a contour soma use radius to have same surface area
                A = calculate_surface_area(self.soma.df)
                r = calculate_sphere_radius(A)
                print(f'Radius: {r}')
            else:
                print('Soma is a contour')
                r = max(np.mean(distances), self.soma.df['R'].mean())
                print(f'Radius: {r}')
            soma3['X'] = [self.soma_center[0]] * 3
            soma3['Y'] = [self.soma_center[1], self.soma_center[1] - r, self.soma_center[1] + r]
            soma3['Z'] = [self.soma_center[2]] * 3
            soma3['R'] = [r]*3

        soma3['Parent'] = [-1, 1, 1]

        new_soma = SWCSection(soma3)
        new_soma.parent = self.soma.parent
        new_soma.children = self.soma.children
        for child in new_soma.children:
            child.parent = new_soma
        self.sections = [new_soma if (sec.df['Type'] == 1).all() else sec for sec in self.sections]
        
        self.update_index(n_added_points=len(self.soma.df) - old_soma_len, 
                          start_idx=start_idx)

        for child in self.soma.children:
            child.df.loc[child.df.index[0], 'Parent'] = 1

    def update_index(self, n_added_points, start_idx):
        print(f'Updating index by {n_added_points} starting from {start_idx}')

        for sec in self.sections:
            if sec.df.index[0] >= start_idx:
                sec.df.index = sec.df.index + n_added_points
                # if sec['Parent'].iloc[0] >= start_idx - 1:
                sec.df['Parent'] = sec.df['Parent'] + n_added_points


    def __str__(self):
        return f'SWCManager {len(self.sections)} sections {self.soma_notation}'

    def export2swc(self, path):
        self.df.to_csv(path.replace('.swc', '_') + self.soma_notation + '.swc', header=None, index=True, sep=' ', mode='w')
        print(f'Saved to {path.replace(".swc", "_") + self.soma_notation + ".swc"}')


    def plot(self, root_idx=0, ax=None, projection='3d', apical_axis=False):
        if ax is not None:
            plt.sca(ax)
        else:
            fig = plt.figure(figsize=(10, 10))
            ax = fig.add_subplot(111, projection='3d')
        
        for sec in self.sections[root_idx].subtree:
            sec.plot_sec_3d(ax=ax, children=False, parent=False)
        
        if projection == 'XY':
            ax.view_init(90, -90)
        elif projection == 'ZY':
            ax.view_init(0, 0)
    

        if apical_axis and self.apical_center is not None:
        
            ax.plot([self.soma_center[0], self.apical_center[0]],
                    [self.soma_center[1], self.apical_center[1]],
                    [self.soma_center[2], self.apical_center[2]],
                    color='k', linestyle=':', zorder=1001)
            

        adjust_limits(self.df, ax)




def calculate_surface_area(df):
    """ Calculates the surface area of the section"""
    # Calculate the distances between consecutive points
    dist = np.sqrt(df['X'].diff()**2 + df['Y'].diff()**2 + df['Z'].diff()**2)
    # Calculate the radii of the two ends of each frustum
    R_next = df['R'].shift(-1)
    # Calculate the surface area of each frustum
    area = np.pi * (df['R'] + R_next) * np.sqrt((R_next - df['R'])**2 + dist**2)
    return area.sum()


def calculate_sphere_radius(total_area):
    """ Calculates the radius of a sphere with a given surface area"""
    return np.sqrt(total_area / (4 * np.pi))
        
        
def calculate_distances(X, Y, Z):
    dX = np.diff(X)
    dY = np.diff(Y)
    dZ = np.diff(Z)

    # Calculate Euclidean distance between consecutive points
    distances = np.sqrt(dX**2 + dY**2 + dZ**2)

    # Calculate cumulative distances
    distances = np.cumsum(distances)

    # Since we have n-1 distances for n points, you might want to add a 0 at the beginning of the array
    distances = np.insert(distances, 0, 0)
    return distances.tolist()


def find_parent_idx(sec, parent):
    """ Returns the index of the parent section to which the given section is connected """
    parent_loc_id = sec['Parent'].iloc[0]
    if parent_loc_id == -1:
        return None
    # where this section is connected to the parent
    parent_idx = [i for i, x in enumerate(parent.index) if x == parent_loc_id]
    if parent_idx:
        return parent_idx[0]
    else:
        raise ValueError(f'The section\'s 0-end {sec.index[0]} is not connected to the parent')


def distance_3d(point1, point2):
    return np.sqrt((point1[0] - point2[0])**2 +
                   (point1[1] - point2[1])**2 +
                   (point1[2] - point2[2])**2)


def adjust_limits(data, ax, padding_factor=1, epsilon=1e-10):

    max_ax_range = np.array([getattr(data, 'X').max()-getattr(data, 'X').min(), 
                                    getattr(data, 'Y').max()-getattr(data, 'Y').min(), 
                                    getattr(data, 'Z').max()-getattr(data, 'Z').min()]).max() / 2.0
    max_ax_range *= padding_factor

    mid_x = (getattr(data, 'X').max()+getattr(data, 'X').min()) * 0.5
    mid_y = (getattr(data, 'Y').max()+getattr(data, 'Y').min()) * 0.5
    mid_z = (getattr(data, 'Z').max()+getattr(data, 'Z').min()) * 0.5

    ax.set_xlim(mid_x - max(max_ax_range, epsilon), mid_x + max(max_ax_range, epsilon))
    ax.set_ylim(mid_y - max(max_ax_range, epsilon), mid_y + max(max_ax_range, epsilon))
    ax.set_zlim(mid_z - max(max_ax_range, epsilon), mid_z + max(max_ax_range, epsilon))


from scipy import stats
def linear_regression(distances, radii):
    slope, intercept, r_value, p_value, std_err = stats.linregress(distances, radii)
    distances = np.array(distances, dtype=float)
    if slope > 0:
        slope = 0
        intercept = radii.median()
    new_radii = slope * distances + intercept
    return new_radii
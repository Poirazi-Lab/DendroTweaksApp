import os
import re
from typing import List
import sys

class MODFile:
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.data = None
        self.load()

    def load(self) -> None:
        with open(self.path, 'r') as f:
            self.data = f.read()

    def save(self) -> None:
        with open(self.path, 'w') as f:
            f.write(self.data)

    def remove_inline_comments(self) -> None:
        self.data = re.sub(r'//.*', '', self.data)

    def remove_keywords(self, keywords: List[str]) -> None:
        for keyword in keywords:
            self.data = re.sub(rf'\b{keyword.upper()}\b', '', self.data)

    def remove_between(self, start: str, end: str) -> None:
        self.data = re.sub(rf'{re.escape(start)}.*?{re.escape(end)}', '', self.data, flags=re.DOTALL)

    def preprocess(self) -> None:
        self.replace_suffix_with_name(overwirte=True)
        self.remove_inline_comments()
        self.remove_keywords(['UNITSON', 'UNITSOFF'])
        self.remove_between('VERBATIM', 'ENDVERBATIM')

    def replace_suffix_with_name(self, overwirte=False) -> None:
        """
        Replace the suffix in the content of the file with the file name.

        Notes
        -----
        Suffix is a string of the form SUFFIX suffix

        Parameters:
            file_name (str): The name of the file to replace the suffix with.
        """
        suffix_pattern = r'SUFFIX\s+\w+'
        match = re.search(suffix_pattern, self.data)
        print(f"Replacing {match.group()} with SUFFIX {self.name}")
        self.data = re.sub(suffix_pattern, f'SUFFIX {self.name}', self.data)
        if overwirte:
            self.save()



class Preprocessor:

    def __init__(self, config: dict = None):
        
        if config is None:
            config = {
                'remove_inline_comments': True,
                'remove_keywords': ['UNITSON', 'UNITSOFF'],
                'remove_between': [('VERBATIM', 'ENDVERBATIM')]
            }
        
    def remove_inline_comments(self, content: str) -> str:
        return re.sub(r'//.*', '', content)

    def remove_keywords(self, content: str, keywords: List[str]) -> str:
        for keyword in keywords:
            content = re.sub(rf'\b{keyword.upper()}\b', '', content)
        return content

    def remove_between(self, content: str, start: str, end: str) -> str:
        return re.sub(rf'{re.escape(start)}.*?{re.escape(end)}', '', content, flags=re.DOTALL)

    def preprocess(self, content: str) -> str:
        if self.config.get('remove_inline_comments', False):
            content = self.remove_inline_comments(content)
        if 'remove_keywords' in self.config:
            content = self.remove_keywords(content, self.config['remove_keywords'])
        if 'remove_between' in self.config:
            for start, end in self.config['remove_between']:
                content = self.remove_between(content, start, end)
        return content



class MODFileLoader():

    def __init__(self, config: dict = None):
        
        self.converter = MODFileConverter()

    def load_from_mod(self, path: str) -> None:
        ...

    def load_from_python(self, path: str) -> Mechanism:
        ...
    
    def load_mechanism(self, path: str) -> Mechanism:
        
        self.load_from_mod(path)
        MechanismClass = self.load_from_python(path)
        return MechanismClass()


# class MechanismFactory():

#     def __init__(self):
#         self.class_map = {}

#     def register_mechanism(self, path_to_python: str):
#         module_name = '.'.join(path_to_python.split('/')[:-1])
#         class_name = path_to_python.split('/')[-1].replace('.py', '')
#         MechanismClass = dynamic_import(module_name, class_name)
#         self.class_map[class_name] = MechanismClass

#     def create_mechanism(self, name) -> Mechanism:
#         return self.class_map[name]()

#     def create_ion_channel(self, name) -> IonChannel:
#         return self.class_map[name]()

#     def create_and_standardize_channel(self, name) -> StandardChannel:
#         channel = self.create_ion_channel(name)
#         standard_channel = StandardChannel()
#         data = channel.get_data()
#         standard_channel.fit(data)
#         return standard_channel



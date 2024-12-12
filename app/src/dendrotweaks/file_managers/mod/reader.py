import re
from typing import List, Dict

class MODReader():
    """
    Reader class for .mod files.

    Provides methods to read and preprocess .mod files.
    Splits the content of the file into blocks for further parsing.

    Attributes:
        blocks (Dict[str, List[str]]): A dictionary with the blocks of the .mod file.
    """

    BLOCK_TYPES = ['TITLE',
                  'COMMENT',
                  'NEURON',
                  'UNITS',
                  'PARAMETER',
                  'ASSIGNED',
                  'STATE',
                  'BREAKPOINT',
                  'DERIVATIVE',
                  'INITIAL',
                  'FUNCTION',
                  'PROCEDURE',
                  'KINETIC']

    def __init__(self):
        self._path_to_file = ''
        self._original_content = None
        self._content = None
        self.blocks = {}
        self._unmatched = ''

    @property
    def file_name(self):
        """
        Returns the name of the file without the extension.

        Returns:
            str: The name of the file without the extension.
        """
        return self._path_to_file.split('/')[-1].split('.')[0]

    #provide content as a printed string
    @property
    def content(self):
        """
        Returns the original content of the file.

        Returns:
            str: The original content of the file.
        """
        print(self._content)

    def info(self):
        print(f"\n{'='*20}\nREADER\n"
              f"\nPath to file: {self._path_to_file}")
        for block_name, block_content in self.blocks.items():
            print(f"{len(block_content)} - {block_name}")
        self.find_unmatched_content()

    def read(self, path_to_file: str) -> None:
        """
        The key method to read the content of the file.
        This is the first method to call when working with a .mod file.

        Parameters:
            path_to_file (str): Path to the file to read.
        """
        self._path_to_file = path_to_file
        with open(path_to_file) as f:
            self._original_content = f.read()
        
        self._content = self._original_content
        
    # Preprocess the file

    def remove_unitsoff(self) -> None:
        """
        Removes 'UNITSOFF' and 'UNITSON' from the content of the file.
        """
        self._content = re.sub(r'UNITSOFF|UNITSON', '', self._content)

    def remove_verbatim(self) -> None:
        """
        Removes 'VERBATIM' and 'ENDVERBATIM' from the content of the file.
        """
        # TODO: Does it remove the content between VERBATIM and ENDVERBATIM?
        self._content = re.sub(r'VERBATIM|ENDVERBATIM', '', self._content)

    def remove_inline_comments(self) -> None:
        """
        Removes the rest of the line after ":" from the content of the file.
        """
        self._content = re.sub(r':.*', '', self._content)

    def remove_suffix_from_gbar(self) -> None:
        """
        Removes the suffix from 'gbar' in the content of the file.

        Example
        -------
            gnabar -> gbar
        """
        self._content =  re.sub(r'\b\w*g\w*bar\w*\b', 'gbar', self._content)

    def remove_suffix_from_variable_names(self) -> None:
        """
        Removes the suffix from variable names in the content of the file.

        Example
        -------
            mna -> m
        """
        suffix = self.ast['mod_file']['neuron_block']['suffix']
        print(f"Renaming variables with suffix {suffix}")
        for assigned in self.ast['mod_file']['assigned_block']:
            if suffix in assigned['name']:
                self.data = self.data.replace(assigned['name'], assigned['name'].replace(suffix, ''))
                print(f"Renamed {assigned['name']} to {assigned['name'].replace(suffix, '')}")
        for parameter in self.ast['mod_file']['parameter_block']:
            if suffix in parameter['name']:
                self.data = self.data.replace(parameter['name'], parameter['name'].replace(suffix, ''))
                print(f"Renamed {parameter['name']} to {parameter['name'].replace(suffix, '')}")
                

        with open(self._mod_file, 'w') as f:
            f.write(self.data)
            print(f"Saved changes to {self._mod_file}")

    def split_content_in_blocks(self) -> None:
        """
        Split the content of the file into blocks for further processing.
        """
        for block_type in self.BLOCK_TYPES:
            matches = self._get_block_regex(block_type)
            self.blocks[block_type] = matches

    def _get_block_regex(self, block_name: str) -> List[str]:
        """
        Get the regex pattern for a specific block.

        Example
        -------
            NEURON {
                ...
            }

        Parameters:
        ----------
            block_name (str): Name of the block to get the regex pattern for.

        Returns:
            List[str]: A list of matches for the block.
        """
        if block_name == 'TITLE':
            pattern = r"(" + re.escape(block_name) + r"[\s\S]*?\n)"
        elif block_name == 'COMMENT':
            pattern = r"(" + re.escape(block_name) + r"[\s\S]*?ENDCOMMENT)"
        else:
            pattern = r"(\b" + re.escape(block_name) + r"\b[\s\S]*?\{(?:[^{}]*\{[^{}]*\})*[^{}]*?\})"
        matches = re.findall(pattern, self._content, re.DOTALL)
        return matches

    def find_unmatched_content(self, verbose:bool=True) -> None:
        """
        Find unmatched content in the content of the file.

        Parameters
        ----------
        verbose (bool): Whether to print the unmatched content.
        """
        unmatched = self._content
        for block_name, block in self.blocks.items():
            for block_content in block:
                unmatched = unmatched.replace(block_content, '')
        unmatched = unmatched.strip()
        if verbose: 
            if unmatched: print(f"Unmatched content:\n{unmatched}")
            else: print("No unmatched content.")
        self._unmatched = unmatched

    def replace_suffix_with_name(self, file_name: str) -> None:
        """
        Replace the suffix in the content of the file with the file name.

        Notes
        -----
        Suffix is a string of the form SUFFIX suffix

        Parameters:
            file_name (str): The name of the file to replace the suffix with.
        """
        suffix_pattern = r'SUFFIX\s+\w+'
        match = re.search(suffix_pattern, self._content)
        print(f"Replacing {match.group()} with SUFFIX {file_name}")
        self._content = re.sub(suffix_pattern, f'SUFFIX {file_name}', self._content)
            

    def write(self, path_to_file: str) -> None:
        """
        Write the content of the file to a new file.

        Parameters:
            path_to_file (str): Path to the new file.
        """
        with open(path_to_file, 'w') as f:
            f.write(self._content)
        print(f"Saved changes to {path_to_file}")
import re
import pprint
from typing import List, Dict, Union, Any

from dendrotweaks.file_managers.mod.grammar_blocks import title, comment_block
from dendrotweaks.file_managers.mod.grammar_blocks import neuron_block
from dendrotweaks.file_managers.mod.grammar_blocks import units_block, parameter_block, assigned_block
from dendrotweaks.file_managers.mod.grammar_blocks import state_block
from dendrotweaks.file_managers.mod.grammar_blocks import breakpoint_block, derivative_block, initial_block
from dendrotweaks.file_managers.mod.grammar_blocks import function_block, procedure_block

from dendrotweaks.file_managers.mod.ast import AbstracSyntaxTree


class MODParser():
    """
    A parser for .mod files that uses a Pyparsing grammar 
    to parse the content of the file.
    """

    BLOCKS = {"TITLE": title,
              "COMMENT": comment_block,
              "NEURON": neuron_block,
              "UNITS": units_block,
              "PARAMETER": parameter_block,
              "ASSIGNED": assigned_block,
              "STATE": state_block,
              "BREAKPOINT": breakpoint_block,
              "DERIVATIVE": derivative_block,
              "INITIAL": initial_block,
              "FUNCTION": function_block,
              "PROCEDURE": procedure_block,
              }

    def __init__(self):
        self._result = {}
        self._ast = {}

    def info(self):
        print(f"\n{'='*20}\nPARSER\n")
        print(f"File parsed: {bool(self._ast)}")
        for block_name, parsed_content in self._ast.items():
            print(f"{bool(parsed_content):1} - {block_name}")

    # PARSING

    @property
    def ast(self) -> Dict:
        return AbstracSyntaxTree(self._ast)

    def parse_block(self, block_name: str, block_content: List[str]) -> List[Dict]:
        """ To ensure that parsing is independent for each block.
        Could help in debugging the grammar (per block).
        """
        grammar = self.BLOCKS.get(block_name)
        if grammar is None:
            return []  # Or handle the error appropriately

        parsed_blocks = [grammar.parseString(block) for block in block_content]
        self._result[block_name] = parsed_blocks
        return [block.asDict()['block'] for block in parsed_blocks]

    def parse(self, blocks: Dict[str, List[str]]) -> None:
        """
        Parse the entire content of the file.

        Parameters
        ----------
        blocks : Dict[str, List[str]]
            A dictionary with the blocks of the .mod file.
        """
        for block_name, block_content in blocks.items():
            # print(f"Parsing block {block_name}")
            self.parse_block(block_name, block_content)
        self._ast = {block_name: [r.asDict()['block'] for r in result]
                    for block_name, result in self._result.items()}
        self._ast = {k: v[0] if len(v) == 1 and k not in ['FUNCTION', 'PROCEDURE'] else v
                        for k, v in self._ast.items()}

    # POST PROCESSING

    # General methods
                
    def find_in_blocks(self, pattern, block_types = ['ASSIGNED', 'PROCEDURE', 'PARAMETER']):
        """
        Find a pattern in the specified block types.

        Parameters
        ----------
        pattern : str
            The regex pattern to search for in the blocks.
        block_types : list
            A list of block types to search for the pattern.

        Returns
        -------
        str or list or None
            A list of matching strings if found, a single matching string if there's only one,
            or None if no matches are found.

        Examples
        --------
        Find the name of the variable representing time constant of a state variable:
        >>> pattern = re.compile('tau', re.IGNORECASE)
        >>> parser.find_in_blocks('tau')
        ['m_tau', 'hTau', 'ntau']
        """
        for block_type in block_types:
            matches = find_in_nested_dict(self._ast[block_type], pattern)
            if matches: 
                return matches[0] if len(matches) == 1 else matches

    def replace_in_blocks(self, replacements, block_types = ['FUNCTION', 'PROCEDURE']):
        """
        Replace the variable names with their values or another variable name in
        the specified block types.

        Parameters
        ----------
        replacements : dict
            A dictionary with the constants as keys and their replacement values.
        block_types : list
            A list of block types to apply the replacements to.

        Examples
        --------
        Replace the Faraday constant with its value in every FUNCTION block:
        >>> parser.replace({'FARADAY': 96485.309}, block_types=['FUNCTION'])
        """
        for block_type in block_types:
            for old, new in replacements.items():
                self._ast[block_type] = [
                    replace_in_nested_dict(block, old, new)
                    for block in self._ast[block_type]
                ]

    # Specific methods

    def standardize_state_var_names(self):
        """
        Standardize the names of the variables representing the inf and tau of
        the state variables in the .mod file.
        """
        
        for state_var in self._ast['STATE']:

            # print(f"Standardizing names for state variable: {state_var}")

            inf_pattern = f'({state_var}.*inf|inf.*{state_var})'
            inf_pattern = re.compile(inf_pattern, re.IGNORECASE)

            tau_pattern = f'({state_var}.*tau|tau.*{state_var})'
            tau_pattern = re.compile(tau_pattern, re.IGNORECASE)

            inf_var_name = self.find_in_blocks(pattern=inf_pattern)
            tau_var_name = self.find_in_blocks(pattern=tau_pattern)

            # print(f"Found inf variable: {inf_var_name}")
            # print(f"Found tau variable: {tau_var_name}")

            replacements = {
                inf_var_name: f'{state_var}Inf',
                tau_var_name: f'{state_var}Tau'    
            }
            
            self.replace_in_blocks(replacements)

    def _find_power(self, expression: Dict or List, state_var: str, power=0):
        """
        Finds the power of a given state variable in an expression by 
        recursively searching the expression in a nested dictionary.

        Parameters
        ----------
        expression : dict or list
            The expression to search for the state variable.
        state_var : str
            The state variable name to search for.
        power : int
            The current power of the state variable. Used to keep track of the power.

        Returns
        -------
        int
            The power of the state variable in the expression.

        Examples
        --------
        Consider a statement in the BREAKPOINT block for a Na channel:
        >>> g = tadj * gbar * pow(m, 3) * h
        The expression for this statement could be represented as a nested dictionary:
        >>> expr = {'*': ['tadj', {'*': ['gbar', {'*': [{'pow': ['m', 3]}, 'h']}]}]}
        The corresponding tree representation would be:
        * 
        └── tadj
            └── * 
                ├── gbar
                └── *
                    ├── pow
                    │   ├── m
                    │   └── 3
                    └── h
        To find the power of 'm' and 'h' in the expression:
        >>> parser._find_power(expr, 'm')
        3
        >>> parser._find_power(expr, 'h')
        1
        """
        # If expression is a dictionary (e.g. {'pow': ['m', 3]})
        if isinstance(expression, dict):
            for operator, operands in expression.items():
                if operator == 'pow' and operands[0] == state_var:
                    # Found a power operation on the target variable
                    power = int(operands[1])
                else:
                    # Continue traversing the dictionary
                    power = self._find_power(operands, state_var, power)

         # If expression is a list (e.g. [{'pow': ['m', 3]}, 'h'])
        elif isinstance(expression, list):
            for operand in expression:
                power = self._find_power(operand, state_var, power)
        
        # If expression directly matches the variable (e.g., 'h')
        elif expression == state_var:
            # A standalone variable has an implicit power of 1
            power += 1 # In case the variable is found multiple times in the expression

        # If none of the above, just return current power
        return power

    def update_state_vars_with_power(self):
        """
        Update the state variables in the AST with the corresponding power
        from the equation in the BREAKPOINT block.
        """
        if self._ast['BREAKPOINT'].get('statements'):
            expr = self._ast['BREAKPOINT']['statements'][0]['expression']
            state_vars = {
                state_var: self._find_power(expr, state_var) 
                for state_var in self._ast['STATE']
            }
            self._ast['STATE'] = state_vars
        else:
            print(
                f"The breakpoint block for {self._ast.suffix} does not have any statements.")



# HELPER FUNCTIONS

def replace_in_nested_dict(data: Dict, target: Any, replacement: Any) -> Dict:
    """
    A recursive helper function to replace a target value 
    with a replacement value in a nested dictionary.

    Notes
    -----
    The structure of the AST dictionary assumes that dictionaries can have:
    - as a key a single value (string) that represents an operator (e.g. '+' or '*') 
    or a function name (e.g. 'pow').
    - as a value either a list or a single value (string or number). A list can contain
    only dictionaries or single values (string or number).
    Lists represent the operands of an operator or arguments of a function.
    Dictionaries represent the operator or function and its operands or arguments.
    Single values represent variables or numbers.

    Parameters
    ----------
    data : dict
        The original dictionary to search for the target value.
    target : any
        The value to search for in the dictionary.
    replacement : any
        The value to replace the target value with.

    Examples
    --------
    Rename a variable:
    >>> d = {'+': {'a': 'b'}} # Represents a + b
    >>> replace_in_nested_dict(d, 'a', 'c')
    {'+': {'c': 'b'}}

    Replace a constant name with its value:
    >>> d = {'*': {'a': 'FARADAY'}} # Represents a * FARADAY
    >>> replace_in_nested_dict(d, 'FARADAY', 96485.309)
    {'*': {'a': 96485.309}}

    Returns
    -------
    dict
        The original dictionary with the target value replaced 
        by the replacement value.
    """
    if isinstance(data, dict):
        return {key: replace_in_nested_dict(value, target, replacement) 
                for key, value in data.items()}
    elif isinstance(data, list):
        return [replace_in_nested_dict(item, target, replacement) 
                for item in data]
    elif data == target:
        return replacement
    else:
        return data

def find_in_nested_dict(data: Dict, pattern: str) -> Union[str, List[str], None]:
    """
    A recursive function to find strings in a nested dictionary 
    that match a given regex pattern.

    Parameters
    ----------
    data : dict
        The dictionary to search within.
    pattern : str
        The regex pattern to search for within string values in the dictionary.

    Returns
    -------
    Union[str, List[str], None]
        A list of matching strings if found, a single matching string if there's only one,
        or None if no matches are found.
    """
    matches = []

    def _recursive_search(data: Any):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(key, str) and re.search(pattern, key):
                    matches.append(key)
                _recursive_search(value)
        elif isinstance(data, list):
            for item in data:
                _recursive_search(item)
        elif isinstance(data, str) and re.search(pattern, data):
            matches.append(data)

    _recursive_search(data)
    if not matches:
        return None
    matches = list(set(matches))
    return matches if len(matches) > 1 else matches[0]
    
                
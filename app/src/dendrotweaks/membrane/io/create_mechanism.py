from dendrotweaks.reader import Reader
from dendrotweaks.parser import Parser
from dendrotweaks.writer import PythonCodeGenerator, NMODLCodeGenerator

reader = Reader()
parser = Parser()
py_generator = PythonCodeGenerator()
mod_generator = NMODLCodeGenerator()

def create_channel(path_to_file: str, path_to_template: str) -> None:

    # Read the mechanism file
    content = read_file(path_to_file)
    
    content = reader._remove_inline_comments(content)
    content = reader._remove_unitsoff(content)
    content = reader._remove_verbatim(content)

    blocks = reader.split_to_blocks(content)

    # Parse the mechanism file
    parser.parse(blocks)
    parser._update_state_vars_with_power()
    parser._standardize_state_var_names()
    parser._replace_constants_with_values()
    parser.restore_expressions()

    ast = parser.ast


    # Generate Python code
    python_code = generator.generate(ast, path_to_template)

    # Write the Python code to a file
    write_file('mechanism.py', python_code)
    
import re
import pyparsing as pp

pp.ParserElement.enablePackrat()

from pyparsing import (alphas, alphanums, nums)
from pyparsing import (Char, Word, Empty, Literal, Regex, Keyword)
from pyparsing import (infix_notation, opAssoc)

from pyparsing import (Group, Combine, Dict, Suppress, delimitedList, Optional)
from pyparsing import (ZeroOrMore, OneOrMore, oneOf)
from pyparsing import Forward
from pyparsing import (restOfLine, SkipTo)
from pyparsing import pyparsing_common
from pyparsing import LineEnd
from pyparsing import infixNotation, opAssoc, And
from pyparsing import NotAny

# Symbols
LBRACE, RBRACE, LPAREN, RPAREN, EQUAL, COLON = map(Suppress, "{}()=:")

# Keywords

## Block keywords
TITLE = Suppress(Keyword('TITLE', caseless=False))
COMMENT = Suppress(Keyword('COMMENT', caseless=False))
ENDCOMMENT = Suppress(Keyword('ENDCOMMENT', caseless=False))
NEURON = Suppress(Keyword('NEURON', caseless=False))
UNITS = Suppress(Keyword('UNITS', caseless=False))
PARAMETER = Suppress(Keyword('PARAMETER', caseless=False))
ASSIGNED = Suppress(Keyword('ASSIGNED', caseless=False))
STATE = Suppress(Keyword('STATE', caseless=False))
BREAKPOINT = Suppress(Keyword('BREAKPOINT', caseless=False))
INITIAL = Suppress(Keyword('INITIAL', caseless=False))
DERIVATIVE = Suppress(Keyword('DERIVATIVE', caseless=False))
FUNCTION = Suppress(Keyword('FUNCTION', caseless=False))
PROCEDURE = Suppress(Keyword('PROCEDURE', caseless=False))
INDEPENDENT = Suppress(Keyword('INDEPENDENT', caseless=False))
FROM = Suppress(Keyword('FROM', caseless=False))
TO = Suppress(Keyword('TO', caseless=False))
KINETIC = Suppress(Keyword('KINETIC', caseless=False))
STEADYSTATE = Suppress(Keyword('STEADYSTATE', caseless=False))

block_to_keep = TITLE | COMMENT | NEURON | UNITS | PARAMETER | ASSIGNED | STATE | BREAKPOINT | INITIAL | DERIVATIVE | FUNCTION | PROCEDURE

## Misc keywords
VERBATIM = Suppress(Keyword('VERBATIM', caseless=False))
ENDVERBATIM = Suppress(Keyword('ENDVERBATIM', caseless=False))



# TITLE

title = Combine(TITLE + restOfLine('title'))

comment = Combine(COLON + restOfLine)("comment")

comment_block = Combine(COMMENT + SkipTo(ENDCOMMENT) + ENDCOMMENT)('comment_block')

# VERBATIM
verbatim = VERBATIM + SkipTo(ENDVERBATIM) + ENDVERBATIM

## Block keywords
FARADAY = Keyword('FARADAY', caseless=False)
R = Keyword('R', caseless=False)

number = pyparsing_common.number
identifier = Word(alphas, alphanums + "_") 
# unit = Combine(LPAREN + Word(alphas + nums + "/") + RPAREN)
unit = Combine(LPAREN
               + ( Combine(Word(alphas + "23") + "/" + Word(alphas + "23"))
                  | Combine("/" + Word(alphas + "23") + "/" + Word(alphas + "23"))
                  | Combine("/" + Word(alphas + "23"))
                  | Combine(Word(nums) + "/" + Word(alphas + "23"))
                  | Word(alphas + "23"))
               + RPAREN)
dimensionless = LPAREN + Literal("1") + RPAREN

faraday_constant = Dict(Group(FARADAY + EQUAL + LPAREN + Suppress(Literal('faraday')) + RPAREN + Optional(unit)))
gas_constant = Dict(Group(R + EQUAL + LPAREN + Suppress(Literal('k-mole')) + RPAREN + Optional(unit)))

constant = faraday_constant | gas_constant

quantity = And([number + Suppress(unit)])

value_range = Suppress(Literal('<')) + Suppress(number) + Suppress(Literal(',')) + Suppress(number) + Suppress(Literal('>'))

from_to = FROM + number("from") + TO + number("to")

# NEURON block

## Block keywords
SUFFIX = Suppress(Keyword('SUFFIX', caseless=False))
NONSPECIFIC_CURRENT = Suppress(Keyword('NONSPECIFIC_CURRENT', caseless=False))
USEION = Suppress(Keyword('USEION', caseless=False))
READ = Suppress(Keyword('READ', caseless=False))
WRITE = Suppress(Keyword('WRITE', caseless=False))
VALENCE = Suppress(Keyword('VALENCE', caseless=False))
RANGE = Suppress(Keyword('RANGE', caseless=False))
GLOBAL = Suppress(Keyword('GLOBAL', caseless=False))

## Block statements
suffix_stmt = SUFFIX + identifier("suffix")
nonspecific_current_stmt = NONSPECIFIC_CURRENT + identifier("nonspecific_current")
useion_stmt = Group(
    USEION
    + identifier("ion")
    + Group(READ + delimitedList(identifier))("read")
    + Optional(Group(WRITE + delimitedList(identifier))("write"))
    + Optional(VALENCE + number("valence"))
)("useion*")
range_stmt = Group(RANGE + delimitedList(identifier))("range")
global_stmt = Group(GLOBAL + delimitedList(identifier))("global")

neuron_stmt = suffix_stmt | nonspecific_current_stmt | useion_stmt | range_stmt | global_stmt

## Block definition
neuron_block = Group(
    NEURON
    + LBRACE
    + OneOrMore(neuron_stmt)
    + RBRACE
)("neuron_block")


# UNITS block



## Block statements
unit_definition = Dict(Group(unit + EQUAL + unit)) | constant

## Block definition
units_block = Group(
    UNITS 
    + LBRACE 
    + OneOrMore(unit_definition) 
    + RBRACE
)("units_block")

# units_blocks = ZeroOrMore(units_block)("units_block")

# PARAMETER block

## Block statements
parameter_stmt = Group(
    identifier('name') + EQUAL + number('value') + Optional(unit | dimensionless)('unit') + Optional(value_range)
)

## Block definition
parameter_block = Group(
    PARAMETER 
    + LBRACE 
    + OneOrMore(parameter_stmt) 
    + RBRACE
)("parameter_block")

parameter_block = parameter_block.ignore(comment)



# ASSIGNED block

## Block statements
assigned_stmt = Group(identifier('name') + Optional(unit | dimensionless)('unit') + Optional(comment))

## Block definition
assigned_block = Group(
    ASSIGNED 
    + LBRACE 
    + OneOrMore(assigned_stmt)
    + RBRACE
)("assigned_block")



# STATE block

## Block definition
state_var = Word(alphas) + Suppress(Optional(unit | dimensionless)) + Suppress(Optional(from_to))
# state_var = Group(identifier('name') + Optional(unit | dimensionless)('unit') + Optional(comment))
state_block = Group(
    STATE 
    + LBRACE 
    + OneOrMore(state_var) 
    + RBRACE
)("state_block")




# breakpoint_block = BREAKPOINT + SkipTo(block_to_keep)
# breakpoint_block = Suppress(breakpoint_block)

# DERIVATIVE block (not used)
# derivative_block = DERIVATIVE + SkipTo(block_to_keep)
# derivative_block = Suppress(derivative_block)

# INDEPENDENT block (not used)
independent_block = INDEPENDENT + SkipTo(block_to_keep)
independent_block = Suppress(independent_block)

kinetic_block = KINETIC + SkipTo(block_to_keep)
kinetic_block = Suppress(kinetic_block)

derivative_block = DERIVATIVE + SkipTo(block_to_keep)
derivative_block = Suppress(kinetic_block)

# Functional blocks

## Signature

param = Group(identifier('name') + Optional(unit('unit') | dimensionless('unit')))
param_list = delimitedList(param)('params')
signature = Group(
    identifier('f_name') 
    + LPAREN 
    + Optional(param_list) 
    + RPAREN 
    + Optional(unit)('returned_unit')
)('signature')

## Local 
LOCAL = Keyword("LOCAL", caseless=False)
LOCAL = Suppress(LOCAL)
local_stmt = LOCAL + delimitedList(identifier)

# Expression
expr = Forward()
parenth_expr = LPAREN + expr + RPAREN

## Function call with arguments
arg = expr | identifier | number
arg_list = delimitedList(arg)('args')
func_call_with_args = Group(identifier + LPAREN + Optional(arg_list) + RPAREN)
def func_call_with_args_action(tokens):
    function_name = tokens[0][0]
    function_args = tokens[0][1:]
    return {function_name: function_args}
func_call_with_args.setParseAction(func_call_with_args_action)

## Function call with expression
func_call_with_expr = Group(identifier('name') + LPAREN + expr + RPAREN)
def func_call_with_expr_action(tokens):
    function_name = tokens[0][0]
    function_expr = tokens[0][1]
    return {function_name: function_expr}
func_call_with_expr.setParseAction(func_call_with_expr_action)

## Operands
func_operand = func_call_with_args | func_call_with_expr
operand = func_operand | quantity | number | identifier # the order is important!
operand = operand | LPAREN + operand + RPAREN

## Operators
signop = Literal('-')
plusop = oneOf('+ -')
mulop = oneOf('* /')
orderop = oneOf('< > <= >= ==')
powop = Literal('^')

# def sign_action(tokens):
#     tokens = tokens[0]
#     return {tokens[0]: tokens[1]}

# def op_action(tokens):
#     tokens = tokens[0]
#     return {tokens[1]: [tokens[0], tokens[2]]}

def sign_action(tokens):
    tokens = tokens[0]
    return {tokens[0]: [tokens[1]]}

def op_action(tokens):
    tokens = tokens[0]
    while len(tokens) > 3:
        tokens = [{tokens[1]: [tokens[0], tokens[2]]}] + tokens[3:]
    return {tokens[1]: [tokens[0], tokens[2]]}

## Expression
expr <<= infix_notation(
 operand,
 [
  (signop, 1, opAssoc.RIGHT, sign_action),
  (powop, 2, opAssoc.RIGHT, op_action),
  (mulop, 2, opAssoc.LEFT, op_action),
  (plusop, 2, opAssoc.LEFT, op_action),
  (orderop, 2, opAssoc.LEFT, op_action),
 ]
)('expression')


# expr = expr | LPAREN + expr + RPAREN


## Assignment
assignment_stmt = Group(
    identifier('assigned_var') 
    + EQUAL 
    + expr
)

# BREAKPOINT block (not used)
SOLVE = Suppress(Keyword('SOLVE', caseless=False))
METHOD = Suppress(Keyword('METHOD', caseless=False))
STEADYSTATE = Suppress(Keyword('STEADYSTATE', caseless=False))

solve_stmt = Group(
    SOLVE
    + identifier("solve")
    + (METHOD | STEADYSTATE)
    + identifier("method")
)("solve_stmt")

breakpoint_block = Group(
    BREAKPOINT 
    + LBRACE 
    + solve_stmt
    + ZeroOrMore(assignment_stmt)("statements")
    + RBRACE
)("breakpoint_block")

initial_stmt = (solve_stmt | assignment_stmt | func_call_with_args )

initial_block = Group(
    INITIAL
    + LBRACE
    # + OneOrMore(func_call_with_args)("func_calls")
    # + OneOrMore(assignment_stmt)("statements")
    + OneOrMore(initial_stmt)("statements")
    + RBRACE
)("initial_block")

derivative_assignment_stmt = Group(
    identifier('assigned_var') 
    + "'"
    + EQUAL 
    + expr
)

derivative_block = Group(
    DERIVATIVE
    + Word(alphas)("name")
    + LBRACE
    + OneOrMore(func_call_with_args)("func_calls")
    + OneOrMore(derivative_assignment_stmt)("statements")
    + RBRACE
)("derivative_block")

# FUNCTION block

## IF-ELSE statement
IF = Keyword("if", caseless=False)
IF = Suppress(IF)
ELSE = Keyword("else", caseless=False)
ELSE = Suppress(ELSE)

if_else_stmt = Group(
    IF + LPAREN + expr('condition') + RPAREN 
    + LBRACE 
    + OneOrMore(assignment_stmt)('if_statements')
    + RBRACE
    + Optional(ELSE + LBRACE + OneOrMore(assignment_stmt)('else_statements') + RBRACE)
)


if_else_stmt = if_else_stmt('if_else_statements*')
assignment_stmt = assignment_stmt('assignment_statements*')

stmt = (assignment_stmt | if_else_stmt)

## Block definition
function_block = Group(
    FUNCTION 
    + signature('signature') 
    + LBRACE 
    + ZeroOrMore(local_stmt)('locals')
    # + ZeroOrMore(if_else_stmt)('if_else_statements')
    # + ZeroOrMore(assignment_stmt)('statements')
    + OneOrMore(stmt)('statements')
    + RBRACE)

function_blocks = OneOrMore(function_block)("function_blocks")


# PROCEDURE block

# stmt = (if_else_stmt('if_else_statements*') | assignment_stmt('statements*'))



## Block definition
procedure_block = Group(
    PROCEDURE 
    + signature('signature') 
    + LBRACE 
    + ZeroOrMore(local_stmt)('locals')
    # + ZeroOrMore(if_else_stmt)('if_else_statements')
    # + OneOrMore(assignment_stmt)('statements')
    + OneOrMore(stmt)('statements')
    + RBRACE)

procedure_blocks = OneOrMore(procedure_block)("procedure_blocks")

# MOD file

block = kinetic_block | independent_block | breakpoint_block | initial_block | derivative_block | procedure_blocks | function_blocks | title | comment_block | neuron_block | units_block | parameter_block | assigned_block | state_block
MOD = Group(ZeroOrMore(block))('mod_file')


class ModParser():

    def __init__(self, grammar):
        self._mod_file = None
        self.data = None
        self.grammar = grammar
        self.ast = None
        self.name = None
        self._original_data = None

    def read_file(self, mod_file):
        self._mod_file = mod_file
        self.name = mod_file.split('/')[-1].split('.')[0]
        with open(mod_file) as f:
            self.data = f.read()
        self._original_data = self.data
        

    def clean_up(self, remove_inline_comments=True, remove_unitsoff=True, remove_suffix_from_gbar=True):
        if remove_unitsoff:
            self.data = re.sub(r'UNITSOFF|UNITSON', '', self.data)
        if remove_inline_comments:
            self.remove_inline_comments()
        if remove_suffix_from_gbar:
            self.remove_suffix_from_gbar()

    def remove_inline_comments(self):
        # removes the rest of the line after ":" but not withig comment block
        self.data = re.sub(r':.*', '', self.data)

    def remove_suffix_from_gbar(self):
        self.data =  re.sub(r'\b\w*g\w*bar\w*\b', 'gbar', self.data)

    def remove_suffix_from_variable_names(self):
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

    def parse_basic(self, mod_file):
        self.read_file(mod_file)
        self.clean_up()
        self.result = self.grammar.parseString(self.data)
        self.ast = self.result.asDict()

    @property
    def suffix(self):
        if self.ast is not None:
            return self.ast['mod_file']['neuron_block']['suffix']

    def parse(self, mod_file):
        self.parse_basic(mod_file)
        self.update_state_vars_with_power()
        self.replace_constants_with_values()

    def _get_block_regex(self, block_name):
        if block_name == 'TITLE':
            pattern = r"(" + re.escape(block_name) + r"[\s\S]*?\n)"
        elif block_name == 'COMMENT':
            pattern = r"(" + re.escape(block_name) + r"[\s\S]*?ENDCOMMENT)"
        else:
            pattern = r"(\b" + re.escape(block_name) + r"\b[\s\S]*?\{(?:[^{}]*\{[^{}]*\})*[^{}]*?\})"
        match = re.findall(pattern, self.data, re.DOTALL)
        return match

    def restore_expression(self, d):
        if isinstance(d, dict):
            for key, value in d.items():
                if key in ['exp', 'log', 'log10', 'sin', 'cos', 'tan', 'sqrt']:
                            key = 'np.' + key
                if key == 'fabs':
                    key = 'np.abs'
                if key == 'pow':
                    key = 'np.power'
                if isinstance(value, list):
                    if len(value) == 1:
                        # note, parentheses were added
                        return key + '(' + self.restore_expression(value[0]) + ')'
                    elif key in ['+', '-', '*', '/', '^', '>', '<', '==']:
                        if key == '^': key = '**'
                        return '(' + (' ' + key + ' ').join([self.restore_expression(v) for v in value]) + ')'
                    else:  # it's a function call
                        return key + '(' + ', '.join([self.restore_expression(v) for v in value]) + ')'
                else:
                    return key + self.restore_expression(value)
        else:
            return str(d)

    def remove_parentheses(self, s):
        if s.startswith('(') and s.endswith(')'):
            return s[1:-1]
        return s

    def extend_expression(self, d, locals=[]):
        restored = self.remove_parentheses(self.restore_expression(d))
        # add self to all variables
        assigned = [assigned['name'] for assigned in self.ast['mod_file']['assigned_block'] if assigned['name'] not in []]
        parameters = [param['name'] for param in self.ast['mod_file']['parameter_block']]
        functions = []
        if self.ast['mod_file'].get('function_blocks') is not None:
            functions = [function['signature']['f_name'] for function in self.ast['mod_file']['function_blocks']]
        procedure_locals = []
        for procedure in self.ast['mod_file']['procedure_blocks']:
            procedure_locals.extend(procedure['locals'])

        attrs = assigned + parameters + functions + procedure_locals
        
        if locals:
            attrs = [attr for attr in attrs if attr not in locals]
        
        for attr in attrs:
            restored = re.sub(r'\b' + attr + r'\b', 'self.' + attr, restored)

        return restored
        
    def find_tau(self, state_var: str):
        for assigned in self.ast['mod_file']['assigned_block']:
            if state_var in assigned['name'].lower() and 'tau' in assigned['name'].lower():
                return assigned['name']
        #check procedures assigned
        for procedure in self.ast['mod_file']['procedure_blocks']:
            if procedure.get('assignment_statements'):
                for statement in procedure['assignment_statements']:
                    if state_var in statement['assigned_var'].lower() and 'tau' in statement['assigned_var'].lower():
                        return statement['assigned_var']
        for parameter in self.ast['mod_file']['parameter_block']:
            if state_var in parameter['name'].lower() and 'tau' in parameter['name'].lower():
                return parameter['name']
        raise Exception(f'Could not find tau for {state_var}')

    def find_inf(self, state_var: str):
        for assigned in self.ast['mod_file']['assigned_block']:
            if state_var in assigned['name'].lower() and 'inf' in assigned['name'].lower():
                return assigned['name']
        #check procedures assigned
        for procedure in self.ast['mod_file']['procedure_blocks']:
            if procedure.get('assignment_statements'):
                for statement in procedure['assignment_statements']:
                    if state_var in statement['assigned_var'].lower() and 'inf' in statement['assigned_var'].lower():
                        return statement['assigned_var']
        raise Exception(f'Could not find inf for {state_var}')

    def replace_constants_with_values(self):

        def replace_in_nested_dict(input_dict, target, replacement):
            if isinstance(input_dict, dict):
                for key, value in input_dict.items():
                    if isinstance(value, dict):
                        replace_in_nested_dict(value, target, replacement)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                replace_in_nested_dict(item, target, replacement)
                            elif item == target:
                                value[value.index(item)] = replacement
                    elif value == target:
                        input_dict[key] = replacement
            return input_dict

        if 'FARADAY' in self.ast['mod_file']['units_block']:
            if self.ast['mod_file'].get('function_blocks'):
                for i, block in enumerate(self.ast['mod_file']['function_blocks']):
                    self.ast['mod_file']['function_blocks'][i] = replace_in_nested_dict(block, 'FARADAY', 96485.309)
                    self.ast['mod_file']['function_blocks'][i] = replace_in_nested_dict(block, 'R', 8.313424)

            if self.ast['mod_file'].get('procedure_blocks'):
                for i, block in enumerate(self.ast['mod_file']['procedure_blocks']):
                    self.ast['mod_file']['procedure_blocks'][i] = replace_in_nested_dict(block, 'FARADAY', 96485.309)
                    self.ast['mod_file']['procedure_blocks'][i] = replace_in_nested_dict(block, 'R', 8.313424)

    def is_voltage_dependent(self):
        for assigned in self.ast['mod_file']['assigned_block']:
            if 'v' in assigned['name'].lower():
                return True
        return False

    def is_ca_dependent(self):
        for assigned in self.ast['mod_file']['assigned_block']:
            if 'cai' in assigned['name'].lower():
                return True
        return False

    def find_power(self, expression, state_var, power=0):
        if isinstance(expression, dict):
            for operator, operands in expression.items():
                if operator == 'pow' and operands[0] == state_var:
                    power = max(power, int(operands[1]))
                else:
                    power = self.find_power(operands, state_var, power)
        elif isinstance(expression, list):
            for operand in expression:
                power = self.find_power(operand, state_var, power)
        elif expression == state_var:
            power += 1  
        return power

    def update_state_vars_with_power(self):
        if self.ast['mod_file']['breakpoint_block'].get('statements'):
            _expr = self.ast['mod_file']['breakpoint_block']['statements'][0]['expression']
            state_vars = {}
            for state_var in self.ast['mod_file']['state_block']:    
                power = self.find_power(_expr, state_var)
                self.ast['mod_file']['state_block']
                state_vars[state_var] = power
            self.ast['mod_file']['state_block'] = state_vars
        else:
            print(f"The breakpoint block for {self.ast['mod_file']['neuron_block']['suffix']} does not have any statements.")

    @property
    def state_vars(self):
        return {
            state_var: {'inf': self.find_inf(state_var), 'tau': self.find_tau(state_var), 'power': power}
            for state_var, power in self.ast['mod_file']['state_block'].items()
        }

    @property
    def ion(self):
        if self.ast['mod_file']['neuron_block'].get('useion'):
            ions = [ion['ion'] for ion in self.ast['mod_file']['neuron_block']['useion'] if ion.get('write', '')]
            if len(ions) == 1:
                return ions[0]
            elif len(ions) == 0:
                return None
            else:
                raise Exception('Multiple ions not supported')
        else:
            return None

    def ast_to_python(self):
        # Convert the string to a dictionary
        
        ast = self.ast
        # title = ast['mod_file']['title'].strip().replace(' ', '_')
        suffix = ast['mod_file']['neuron_block']['suffix']
        class_name = suffix.capitalize()

        
        if self.is_ca_dependent():
            parent_class_name = 'CustomCalciumDependentIonChannel'
        elif self.is_voltage_dependent():
            parent_class_name = 'CustomVoltageDependentIonChannel'
        else:
            raise Exception('Channel must be voltage or calcium dependent')
        

        # Imports
        python_code = "import numpy as np\n"
        python_code += f"try:\n    from ..channels import {parent_class_name}\n"
        python_code += f"except:\n    from channels import {parent_class_name}\n\n"


        # Start writing the Python class
        
        python_code += f"class {self.name}({parent_class_name}):\n"
        
        python_code += "    def __init__(self, cell=None):\n"

        # Super
        python_code += f"        super().__init__(name='{self.name}', suffix='{suffix}', cell=cell)\n"

        # Add name and suffix
        # python_code += f"        self.name = '{self.name}'\n"
        # python_code += f"        self.suffix = '{suffix}'\n"

        # Range params are not the same as range vars and do not include the assigned variables
        if ast['mod_file']['neuron_block'].get('nonspecific_current') is not None:
            python_code += "        self.nonspecific_current = '" + ast['mod_file']['neuron_block']['nonspecific_current'] + "'\n"
        if ast['mod_file']['neuron_block'].get('useion') is not None:
            python_code += "        self.ion = '" + str(self.ion) + "'\n"
        
        python_code += "        self.range_params = [\n" 
        for range_var in ast['mod_file']['neuron_block']['range']:
            if range_var in [param['name'] for param in ast['mod_file']['parameter_block']]:
                python_code += f"            '{range_var}',\n"
        python_code += "        ]\n"

        # Add parameters
        for param in ast['mod_file']['parameter_block']:
            unit = param.get('unit', '')
            python_code += f"        self.{param['name']} = {param['value']}" + f" # {unit}\n"
        python_code += f"        self.celsius = 37 # degC\n"

        # Add independent variable
        # python_code += f"        self.{self.find_independent_variable()} = np.linspace(-100, 100, 1000)\n"
        if self.is_voltage_dependent():
            python_code += f"        self.v = np.linspace(-100, 100, 1000)\n"
        if self.is_ca_dependent():
            python_code += f"        self.cai = np.logspace(-5, 5, 1000)\n"

        # Add state variables
        state_vars = '        self.state_vars = {\n'
        for state_var, power in ast['mod_file']['state_block'].items():
            state_vars += f'            "{state_var}": {{\n'
            state_vars += f'                "inf": "{self.find_inf(state_var)}",\n'
            state_vars += f'                "tau": "{self.find_tau(state_var)}",\n'
            state_vars += f'                "power": {power}\n'
            state_vars += f'            }},\n'
        state_vars += '        }\n'

        python_code += state_vars
            
        # Add function blocks
                    
        if ast['mod_file'].get('function_blocks') is not None:
            for function in ast['mod_file']['function_blocks']:

                # Add signature
                python_code += f"\n    def {function['signature']['f_name']}(self"
                if function['signature'].get('params') is not None:
                    for param in function['signature']['params']:
                        python_code += f", {param['name']}"
                python_code += f"):\n"

                _locals = [function['signature']['f_name']]
                if function['signature'].get('params') is not None:
                    _locals += [p['name'] for p in function['signature']['params']]
                if function.get('locals') is not None:
                    _locals += function['locals']
                
                    

                for statement in function['statements']:
                    if function.get('assignment_statements') and statement in function['assignment_statements']:
                        python_code += f"        {statement['assigned_var']} = {self.extend_expression(statement['expression'], locals=_locals)}\n"
                    elif function.get('if_else_statements') and statement in function['if_else_statements']:
                        if_else_statement = statement
                        _condition = self.extend_expression(if_else_statement['condition'])

                        else_expressions = {}
                        if if_else_statement.get('else_statements') is not None:
                            for _else_statement in if_else_statement['else_statements']:
                                else_expressions[_else_statement['assigned_var']] = self.extend_expression(_else_statement['expression'], locals=_locals)

                        for _if_statement in if_else_statement['if_statements']:
                            _if_expression = self.extend_expression(_if_statement['expression'], locals=_locals)
                            _else_expression = else_expressions.get(_if_statement['assigned_var'], f'self.{_if_statement["assigned_var"]}' 
                            if _if_statement['assigned_var'] not in _locals else _if_statement['assigned_var'])

                            python_code += f"        conditions = [{_condition},\n                      ~({_condition})]\n"
                            python_code += f"        choices = [{_if_expression},\n                   {_else_expression}]\n"
                            python_code += f"        {_if_statement['assigned_var']} = np.select(conditions, choices)\n"


                # for if_else_statement in function['if_else_statements']:
                #     python_code += f"        if all({self.restore_expression(if_else_statement['condition'])}):\n"
                #     for statement in if_else_statement['if_statements']:
                #         python_code += f"            {statement['assigned_var']} = {self.restore_expression(statement['expression'])}\n"
                #     python_code += "        else:\n"
                #     for statement in if_else_statement['else_statements']:
                #         python_code += f"            {statement['assigned_var']} = {self.restore_expression(statement['expression'])}\n"

                # # Add statements
                # for statement in function['statements']:
                #     python_code += f"        {statement['assigned_var']} = {self.extend_expression(statement['expression'], locals=_locals)}\n"

                # Add return statement
                python_code += f"        return {self.restore_expression(function['signature']['f_name'])}\n"
                

        # Add procedure blocks
        for procedure in ast['mod_file']['procedure_blocks']:
            # Add signature
            python_code += f"\n    def {procedure['signature']['f_name']}(self"
            if procedure['signature'].get('params') is not None:
                for param in procedure['signature']['params']:
                    python_code += f", {param['name']}"
            python_code += f"):\n"

            # _locals = [local for local in procedure['locals']] + [p['name'] for p in procedure['signature']['params']]
            if procedure['signature'].get('params') is not None:
                _locals = [p['name'] for p in procedure['signature']['params']]
            else:
                _locals = []

            # Add statements
            for statement in procedure['statements']:
                if procedure.get('assignment_statements') and statement in procedure['assignment_statements']:
                    python_code += f"        self.{statement['assigned_var']} = {self.extend_expression(statement['expression'], locals=_locals)}\n"
                elif procedure.get('if_else_statements') and statement in procedure['if_else_statements']:
                    if_else_statement = statement
                    # python_code += f"        if all({self.extend_expression(if_else_statement['condition'])}):\n"
                    _condition = self.extend_expression(if_else_statement['condition'])
                    if len(if_else_statement['if_statements']) > 1:
                        raise Exception('Multiple statements in if block not supported')
                    _if_statement = if_else_statement['if_statements'][0]
                    _if_expression = self.extend_expression(_if_statement['expression'], locals=_locals)
                    if if_else_statement.get('else_statements') is not None:
                        _else_statement = if_else_statement['else_statements'][0]
                        _else_expression = self.extend_expression(_else_statement['expression'], locals=_locals)
                    else:
                        _else_expression = f'self.{_if_statement["assigned_var"]}'
                        # _else_expression = self.extend_expression(statement['expression'], locals=_locals)
                        # python_code += f"            self.{statement['assigned_var']} = {self.extend_expression(statement['expression'], locals=_locals)}\n"
                        # python_code += f"        self.{statement['assigned_var']}[{_condition}] = {_expression}\n"
                    python_code += f"        conditions = [{_condition},\n                      ~({_condition})]\n"
                    python_code += f"        choices = [{_if_expression},\n                   {_else_expression}]\n"
                    python_code += f"        self.{_if_statement['assigned_var']} = np.select(conditions, choices)\n"
                    
                    # if if_else_statement.get('else_statements') is not None:
                    #     # python_code += "        else:\n"
                    #     _else_expression = self.extend_expression(statement['expression'], locals=_locals)
                    #     for statement in if_else_statement['else_statements']:
                    #         # python_code += f"            {statement['assigned_var']} = {self.extend_expression(statement['expression'], locals=_locals)}\n"
                    #         python_code += f"        self.{statement['assigned_var']}[not {_condition}] = {_expression}\n"
        
        # Add update function depending on the procedure blocks

        python_code += "\n    def update(self, x_range"
        
        # if procedure['signature'].get('params') is not None:
        #     for param in procedure['signature']['params']:
        #         python_code += f"{param['name']}, "
        python_code += "):\n"
        python_code += "        super().update(x_range)\n"
        for procedure in ast['mod_file']['procedure_blocks']:
            if procedure['signature'].get('params') is not None:
                for param in procedure['signature']['params']:
                    python_code += f"        {param['name']} = x_range\n"
        if self.is_voltage_dependent():
            python_code += f"        self.x_range = x_range\n"
        elif self.is_ca_dependent():
            python_code += f"        self.cai = x_range\n"
        for procedure in ast['mod_file']['procedure_blocks']:
            python_code += f"        self.{procedure['signature']['f_name']}("
            if procedure['signature'].get('params') is not None:
                for param in procedure['signature']['params']:
                    python_code += f"{param['name']}, "
            python_code += ")\n"
        python_code += "        self.update_constant_state_vars(x_range)\n"
        

        return python_code

    def write_python(self, py_file=None):
        # self.parse(mod_file)
        with open(py_file, 'w+') as f:
            f.write(self.ast_to_python())
            print(f'Wrote {py_file}')



parser = ModParser(MOD)
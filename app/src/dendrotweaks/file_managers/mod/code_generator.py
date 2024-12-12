import re
from jinja2 import Template

from jinja2 import Environment, FileSystemLoader

# Configure the Jinja2 environment
# env = Environment(
#     loader=FileSystemLoader('static/data/templates'),  # Load templates from the 'templates' directory
#     trim_blocks=False,                      # Trim newlines after Jinja blocks
#     lstrip_blocks=False,                     # Strip leading whitespace from Jinja blocks
# )

EQUILIBRIUM_POTENTIALS = {
    'na': 60,
    'k': -80,
    'ca': 140
}


class CodeGenerator():
    """ Generates Python code from the AST """

    def __init__(self, path_to_template, lib):
        self.path_to_template = path_to_template
        self._py_code = None
        self.lib = lib

    def info(self):
        print(f"\n{'='*20}\nGENERATOR\n")
        print(f"Template: {self.path_to_template}")
        print(f"Library: {self.lib}")
        print(f"Code is generated: {bool(self._py_code)}")
        

    # MAIN METHOD

    def generate(self, ast):
        # Read the template file
        with open(self.path_to_template, 'r') as file:
            template_string = file.read()

        # # Create a Jinja2 template from the string
        template = Template(template_string)
        # template = env.get_template(self.path_to_template)

        # rename procedure
        if len(ast.procedures) != 1:
            raise ValueError("Only one procedure is supported")
        ast.procedures[0].name = 'compute_kinetic_variables'

        # Define the variables for the template
        variables = {
            'title': ast.title,
            # 'comment': ast.comment,
            'class_name': ast.suffix,
            'suffix': ast.suffix,
            'ion': ast.ion,
            'independent_var_name': ast.independent_var_name,
            'channel_params': ast.params,
            'range_params': ast.range_params,
            'state_vars': ast.state_vars,
            'functions': [self._extend_function(f, ast) for f in ast.functions],
            'procedures': [self._extend_function(p, ast,
                                                 prefix='self.{}',
                                                 param_prefix='self.channel_params["{}_{}"]')
                           for p in ast.procedures],
            'procedure_calls': '\n'.join([self._generate_procedure_call(p, ast.state_vars)
                                          for p in ast.procedures]
                                         ),
            'E_ion': EQUILIBRIUM_POTENTIALS[ast.ion]
        }

        # Render the template with the variables
        self._py_code = template.render(variables)

    # HELPER METHODS

    def _generate_signature(self, function):
        """
        Generate the signature string for a function using a Jinja2 template.
        The function AST representation is used to retrieve the function name
        and parameters:
        >>> def f_name(self, arg1, arg2, ...):

        Parameters
        ----------
        function : dict
            The function AST dictionary
        """
        signature = function.get('signature')
        signature_template = """
        def {{ f_name }}(self{% if args %}, {{ args | join(', ') }}{% endif %}):
        """
        template = Template(signature_template.strip())
        return template.render(
            f_name=signature['f_name'],
            args=[arg['name'] for arg in signature.get('args', [])]
        )

    def _generate_procedure_call(self, procedure, state_vars):
        signature = procedure.get('signature')
        procedure_call_template = """{%- for state_var in state_vars -%}
        {{ state_var }}Inf, {{ state_var }}Tau{% if not loop.last %},{% endif -%}
        {% endfor %} = self.{{ f_name }}({% if args %}{{ args | join(', ') }}{% endif %})
        """
        template = Template(procedure_call_template.strip())

        return template.render(
            f_name=signature['f_name'],
            args=[arg['name'] for arg in signature.get('args', [])],
            state_vars=list(state_vars.keys())
        )

    def _generate_body(self, function, state_vars, indent=8):
        python_code = ""

        # Add statements
        for statement in function['statements']:
            # If the statement is an assignment statement
            if function.get('assignment_statements') and statement in function['assignment_statements']:
                python_code += (f"{statement['assigned_var']} = "
                                f"{self.restore_expression(statement['expression'])}"
                                "\n")
            # If the statement is an if-else statement
            elif function['if_else_statements'] and statement in function['if_else_statements']:
                if_else_statement = statement
                condition = self.restore_expression(if_else_statement['condition'])
                else_expressions = {}
                if if_else_statement.get('else_statements') is not None:
                    for else_statement in if_else_statement['else_statements']:
                        else_expressions[else_statement['assigned_var']] = self.restore_expression(else_statement['expression'])
                for if_statement in if_else_statement['if_statements']:
                    if_expression = self.restore_expression(if_statement['expression'])

                    else_expression = else_expressions.get(if_statement['assigned_var'],
                                                           f'{if_statement["assigned_var"]}' if if_statement['assigned_var'] not in function.local_vars
                                                           else if_statement['assigned_var'])
                    python_code += (
                        f"conditions = [{condition},\n"
                        f"~({condition})]\n"
                    )
                    python_code += (
                        f"choices = [{if_expression},\n"
                        f"{else_expression}]\n"
                    )
                    python_code += (
                        f"{if_statement['assigned_var']}"
                        " = "
                        f"{self.lib}.select(conditions, choices)\n"
                    )

        # Add the return statement
        python_code += self._generate_return(function, state_vars)

        # Add indentation
        python_code = '\n'.join(
            ' ' * indent + line for line in python_code.splitlines())
        return python_code

    def _generate_return(self, function, state_vars):
        if function.has_return:
            return f"return {function.name}"
        else:
            return 'return ' + ', '.join([
                f"{state_var}Inf, {state_var}Tau"
                for state_var in state_vars
            ])
            

    def _extend_function(self, function, ast, prefix='self.{}', param_prefix='self.channel_params["{}_{}"]'):

        # 1. Generate the signature
        signature_str = self._generate_signature(function)

        # 2. Generate the list of class methods
        function_names = []
        if ast.functions:
            function_names = [function.name for function in ast.functions]

        attributes = ['tadj', 'celsius'] + function_names

        if function.local_vars:
            attributes = [
                attr for attr in attributes if attr not in function.local_vars]
            params = [
                param for param in ast.params if param not in function.local_vars]

        # 3. Generate the body
        body_str = self._generate_body(function, ast.state_vars)

        if prefix:
            for attr in attributes:
                body_str = re.sub(r'\b' + attr + r'\b',
                                  prefix.format(attr),
                                  body_str)

        # 4. Filter out the parameters that are not used in the body
        params = [param for param in params
                  if re.search(r'\b' + re.escape(param) + r'\b', body_str)]
        # if param_prefix:
        #     for param in params:
        #         body_str = re.sub(r'\b' + param + r'\b',
        #                                     param_prefix.format(ast.suffix.capitalize(),
        #                                     param), body_str)

        return {'signature': signature_str,
                'params': params,
                'body': body_str.strip()}

    # WRITING METHODS

    def write(self, path_to_file):
        content = self._py_code
        with open(path_to_file, 'w') as f:
            f.write(content)
            print(f"Saved content to {path_to_file}")


    def restore_expression(self, d):
        """
        Recursively restore the expression from the AST dictionary
        and remove the outermost parentheses if they exist.

        Parameters
        ----------
        d : dict
            The AST dictionary representing the expression

        Returns
        -------
        str
            The restored expression

        Examples
        --------
        >>> d = {'exp': {'/': [{'-':['v', 'vhalf']}, 'q']}}
        >>> restore_expression(d)
        'exp((v - vhalf) / q)'
        """

        lib = self.lib

        def remove_parentheses(s):
            if s.startswith('(') and s.endswith(')'):
                return s[1:-1]
            return s

        def recursively_restore_expression(d):
            if isinstance(d, dict):
                for key, value in d.items():
                    if key in ['exp', 'log', 'log10', 'sin', 'cos', 'tan', 'sqrt']:
                        key = lib + '.' + key
                    if key == 'fabs':
                        key = lib + '.abs'
                    if key == 'pow':
                        key = lib + '.power'
                    if isinstance(value, list):
                        if len(value) == 1:
                            # note, parentheses were added
                            return key + '(' + recursively_restore_expression(value[0]) + ')'
                        elif key in ['+', '-', '*', '/', '^', '>', '<', '==']:
                            if key == '^':
                                key = '**'
                            return '(' + (' ' + key + ' ').join([recursively_restore_expression(v) for v in value]) + ')'
                        else:  # it's a function call
                            return key + '(' + ', '.join([recursively_restore_expression(v) for v in value]) + ')'
                    else:
                        return key + recursively_restore_expression(value)
            else:
                return str(d)

        return remove_parentheses(recursively_restore_expression(d))

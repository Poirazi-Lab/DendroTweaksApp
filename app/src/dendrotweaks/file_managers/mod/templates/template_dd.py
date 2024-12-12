# This Python channel class was automatically generated from a MOD file
# using DendroTweaks toolbox, dendrotweaks.dendrites.gr

from dendrotweaks.membrane.mechanisms import CustomIonChannel
import numpy as np

class {{ class_name }}(CustomIonChannel):
    """
    {{ title }}
    """

    def __init__(self, name="{{ class_name }}"):
        super().__init__(name=name)
        self._parameters = {
            {% for param, value in range_params.items() -%}
            "{{ param }}": {{ value }}
                {%- if not loop.last -%},
                {%- endif %}
            {% endfor -%}
        }
        self.channel_params = {
            {% for param, value in channel_params.items() -%}
            "{{ class_name }}_{{ param }}": {{ value }}
                {%- if not loop.last -%},
                {%- endif %}
            {% endfor -%}
        }
        self.channel_states = {
            {% for state in state_vars -%}
            "{{class_name}}_{{ state }}": 0.0
                {%- if not loop.last %},
                {%- endif %}
            {% endfor -%}
        }
        self._state_powers = {
            {% for state, power in state_vars.items() -%}
            "{{class_name}}_{{ state }}": {{ power }}
                {%- if not loop.last %},
                {%- endif %}
            {% endfor -%}
        }
        self.celsius = 37
        self.ion = "{{ ion }}"
        self.current_name = "i_{{ ion }}"

        self.independent_var_name = "{{ independent_var_name }}"
        

    # @property
    # def tadj(self):
    #     return self.tadj = q10 ** ((celsius - temp) / 10)

    def __getitem__(self, item):
        return self.channel_params[item]

    def __setitem__(self, item, value):
        self.channel_params[item] = value
        
    {%- for function in functions %}
    {{ function['signature'] }}
        {%- for param in function['params'] -%}
        {{ param }} = self.channel_params.get("{{ class_name }}_{{ param }}", 1)
        {% endfor %}
        {{ function['body'] }}
    {% if not loop.last %}
    {% endif %}{% endfor -%}
    {% for procedure in procedures %}
    {{ procedure['signature'] }}
        {% for param in procedure['params'] -%}
        {{ param }} = self.channel_params.get("{{ class_name }}_{{ param }}", 1)
        {% endfor %}
        {{ procedure['body'] }}
    {%- if not loop.last %}
    {% endif %}{% endfor %}


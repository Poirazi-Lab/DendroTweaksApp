import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Poirazi_Kdr_soma(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_Kdr_soma', suffix='kdr_soma', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0 # mho/cm2
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "n": {
                "inf": "ninf",
                "tau": "ntau",
                "power": 2
            },
        }

    def rates(self, v):
        self.ninf = 1 / (1 + np.exp(((v + 46.3) / -3)))
        self.ntau = 3.5

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

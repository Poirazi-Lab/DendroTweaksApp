import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Poirazi_nap(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_nap', suffix='nap', cell=cell)
        self.ion = 'na'
        self.range_params = [
            'gbar',
            'vhalf',
            'K',
        ]
        self.gbar = 0 # mho/cm2
        self.K = 4.5 # 1
        self.vhalf = -50.4 # mV
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "n": {
                "inf": "ninf",
                "tau": "ntau",
                "power": 3
            },
        }

    def rates(self, v):
        self.ninf = 1 / (1 + np.exp(((self.vhalf - v) / self.K)))
        self.ntau = 1

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

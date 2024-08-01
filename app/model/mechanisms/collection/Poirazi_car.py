import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Poirazi_car(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_car', suffix='car', cell=cell)
        self.ion = 'ca'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0 # mho/cm2
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "m": {
                "inf": "minf",
                "tau": "mtau",
                "power": 3
            },
            "h": {
                "inf": "hinf",
                "tau": "htau",
                "power": 1
            },
        }

    def rates(self, v):
        self.minf = 1 / (1 + np.exp(((v + 48.5) / -3)))
        self.mtau = 50
        self.hinf = 1 / (1 + np.exp(((v + 53) / 1)))
        self.htau = 5

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

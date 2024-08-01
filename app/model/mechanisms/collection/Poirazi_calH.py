import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Poirazi_calH(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_calH', suffix='calH', cell=cell)
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
        self.minf = 1 / (1 + np.exp(((v + 37) / -1)))
        self.hinf = 1 / (1 + np.exp(((v + 41) / 0.5)))
        self.mtau = 3.6
        self.htau = 29

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

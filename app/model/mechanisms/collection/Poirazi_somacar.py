import numpy as np
try:
    from ..channels import CustomCalciumDependentIonChannel
except:
    from channels import CustomCalciumDependentIonChannel

class Poirazi_somacar(CustomCalciumDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_somacar', suffix='somacar', cell=cell)
        self.ion = 'ca'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0 # mho/cm2
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.cai = np.logspace(-5, 5, 1000)
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
        self.minf = 1 / (1 + np.exp(((v + 60) / -3)))
        self.hinf = 1 / (1 + np.exp(((v + 62) / 1)))
        self.mtau = 100
        self.htau = 5

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

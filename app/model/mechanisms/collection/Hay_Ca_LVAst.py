import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Hay_Ca_LVAst(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_Ca_LVAst', suffix='Ca_LVAst', cell=cell)
        self.ion = 'ca'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0.0 # S/cm2
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "m": {
                "inf": "mInf",
                "tau": "mTau",
                "power": 2
            },
            "h": {
                "inf": "hInf",
                "tau": "hTau",
                "power": 1
            },
        }

    def rates(self):
        self.qt = 2.3 ** ((34 - 21) / 10)
        self.v = self.v + 10
        self.mInf = 1.0 / (1 + np.exp(((self.v - -(30.0)) / -(6))))
        self.mTau = (5.0 + (20.0 / (1 + np.exp(((self.v - -(25.0)) / 5))))) / self.qt
        self.hInf = 1.0 / (1 + np.exp(((self.v - -(80.0)) / 6.4)))
        self.hTau = (20.0 + (50.0 / (1 + np.exp(((self.v - -(40.0)) / 7))))) / self.qt
        self.v = self.v - 10

    def update(self, x_range):
        super().update(x_range)
        self.x_range = x_range
        self.rates()
        self.update_constant_state_vars(x_range)

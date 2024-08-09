import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Hay_K_Tst(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_K_Tst', suffix='K_Tst', cell=cell)
        self.ion = 'k'
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
                "power": 1
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
        self.mInf = 1 / (1 + np.exp((-((self.v + 0)) / 19)))
        self.mTau = (0.34 + (0.92 * np.exp((-(((self.v + 71) / 59)) ** 2)))) / self.qt
        self.hInf = 1 / (1 + np.exp((-((self.v + 66)) / -(10))))
        self.hTau = (8 + (49 * np.exp((-(((self.v + 73) / 23)) ** 2)))) / self.qt
        self.v = self.v - 10

    def update(self, x_range):
        super().update(x_range)
        self.x_range = x_range
        self.rates()
        self.update_constant_state_vars(x_range)

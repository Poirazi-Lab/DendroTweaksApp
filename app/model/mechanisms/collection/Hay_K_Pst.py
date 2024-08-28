import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Hay_K_Pst(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_K_Pst', suffix='K_Pst', cell=cell)
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
        self.mInf = 1 / (1 + np.exp((-((self.v + 1)) / 12)))
        conditions = [self.v < -(50),
                      ~(self.v < -(50))]
        choices = [(1.25 + (175.03 * np.exp((-(self.v) * -(0.026))))) / self.qt,
                   (1.25 + (13 * np.exp((-(self.v) * 0.026)))) / self.qt]
        self.mTau = np.select(conditions, choices)
        self.hInf = 1 / (1 + np.exp((-((self.v + 54)) / -(11))))
        self.hTau = (360 + ((1010 + (24 * (self.v + 55))) * np.exp((-(((self.v + 75) / 48)) ** 2)))) / self.qt
        self.v = self.v - 10

    def update(self, x_range):
        super().update(x_range)
        self.x_range = x_range
        self.rates()
        self.update_constant_state_vars(x_range)

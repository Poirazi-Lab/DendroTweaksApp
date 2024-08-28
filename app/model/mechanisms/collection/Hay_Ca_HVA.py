import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Hay_Ca_HVA(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_Ca_HVA', suffix='Ca_HVA', cell=cell)
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
        conditions = [self.v == -(27),
                      ~(self.v == -(27))]
        choices = [self.v + 0.0001,
                   self.v]
        self.v = np.select(conditions, choices)
        self.mAlpha = (0.055 * (-(27) - self.v)) / (np.exp(((-(27) - self.v) / 3.8)) - 1)
        self.mBeta = 0.94 * np.exp(((-(75) - self.v) / 17))
        self.mInf = self.mAlpha / (self.mAlpha + self.mBeta)
        self.mTau = 1 / (self.mAlpha + self.mBeta)
        self.hAlpha = 0.000457 * np.exp(((-(13) - self.v) / 50))
        self.hBeta = 0.0065 / (np.exp(((-(self.v) - 15) / 28)) + 1)
        self.hInf = self.hAlpha / (self.hAlpha + self.hBeta)
        self.hTau = 1 / (self.hAlpha + self.hBeta)

    def update(self, x_range):
        super().update(x_range)
        self.x_range = x_range
        self.rates()
        self.update_constant_state_vars(x_range)

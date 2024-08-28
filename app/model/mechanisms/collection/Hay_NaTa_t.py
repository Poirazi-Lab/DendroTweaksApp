import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Hay_NaTa_t(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_NaTa_t', suffix='NaTa_t', cell=cell)
        self.ion = 'na'
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
                "power": 3
            },
            "h": {
                "inf": "hInf",
                "tau": "hTau",
                "power": 1
            },
        }

    def rates(self):
        self.qt = 2.3 ** ((34 - 21) / 10)
        conditions = [self.v == -(38),
                      ~(self.v == -(38))]
        choices = [self.v + 0.0001,
                   self.v]
        self.v = np.select(conditions, choices)
        self.mAlpha = (0.182 * (self.v - -(38))) / (1 - np.exp((-((self.v - -(38))) / 6)))
        self.mBeta = (0.124 * (-(self.v) - 38)) / (1 - np.exp((-((-(self.v) - 38)) / 6)))
        self.mTau = (1 / (self.mAlpha + self.mBeta)) / self.qt
        self.mInf = self.mAlpha / (self.mAlpha + self.mBeta)
        conditions = [self.v == -(66),
                      ~(self.v == -(66))]
        choices = [self.v + 0.0001,
                   self.v]
        self.v = np.select(conditions, choices)
        self.hAlpha = (-(0.015) * (self.v - -(66))) / (1 - np.exp(((self.v - -(66)) / 6)))
        self.hBeta = (-(0.015) * (-(self.v) - 66)) / (1 - np.exp(((-(self.v) - 66) / 6)))
        self.hTau = (1 / (self.hAlpha + self.hBeta)) / self.qt
        self.hInf = self.hAlpha / (self.hAlpha + self.hBeta)

    def update(self, x_range):
        super().update(x_range)
        self.x_range = x_range
        self.rates()
        self.update_constant_state_vars(x_range)

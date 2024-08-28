import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Hay_Nap_Et2(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_Nap_Et2', suffix='Nap_Et2', cell=cell)
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
        self.mInf = 1.0 / (1 + np.exp(((self.v - -(52.6)) / -(4.6))))
        conditions = [self.v == -(38),
                      ~(self.v == -(38))]
        choices = [self.v + 0.0001,
                   self.v]
        self.v = np.select(conditions, choices)
        self.mAlpha = (0.182 * (self.v - -(38))) / (1 - np.exp((-((self.v - -(38))) / 6)))
        self.mBeta = (0.124 * (-(self.v) - 38)) / (1 - np.exp((-((-(self.v) - 38)) / 6)))
        self.mTau = (6 * (1 / (self.mAlpha + self.mBeta))) / self.qt
        conditions = [self.v == -(17),
                      ~(self.v == -(17))]
        choices = [self.v + 0.0001,
                   self.v]
        self.v = np.select(conditions, choices)
        conditions = [self.v == -(64.4),
                      ~(self.v == -(64.4))]
        choices = [self.v + 0.0001,
                   self.v]
        self.v = np.select(conditions, choices)
        self.hInf = 1.0 / (1 + np.exp(((self.v - -(48.8)) / 10)))
        self.hAlpha = (-(2.88e-06) * (self.v + 17)) / (1 - np.exp(((self.v + 17) / 4.63)))
        self.hBeta = (6.94e-06 * (self.v + 64.4)) / (1 - np.exp((-((self.v + 64.4)) / 2.63)))
        self.hTau = (1 / (self.hAlpha + self.hBeta)) / self.qt

    def update(self, x_range):
        super().update(x_range)
        self.x_range = x_range
        self.rates()
        self.update_constant_state_vars(x_range)

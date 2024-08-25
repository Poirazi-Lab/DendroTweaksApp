import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Hay_Im(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_Im', suffix='Im', cell=cell)
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
        }

    def rates(self):
        self.qt = 2.3 ** ((34 - 21) / 10)
        self.mAlpha = 0.0033 * np.exp(((2.5 * 0.04) * (self.v - -(35))))
        self.mBeta = 0.0033 * np.exp(((-(2.5) * 0.04) * (self.v - -(35))))
        self.mInf = self.mAlpha / (self.mAlpha + self.mBeta)
        self.mTau = (1 / (self.mAlpha + self.mBeta)) / self.qt

    def update(self, x_range):
        super().update(x_range)
        self.x_range = x_range
        self.rates()
        self.update_constant_state_vars(x_range)

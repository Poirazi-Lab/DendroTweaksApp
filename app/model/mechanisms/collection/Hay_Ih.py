import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Hay_Ih(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_Ih', suffix='Ih', cell=cell)
        self.nonspecific_current = 'ihcn'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0.0 # S/cm2
        self.ehcn = -45.0 # mV
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
        conditions = [self.v == -(154.9),
                      ~(self.v == -(154.9))]
        choices = [self.v + 0.0001,
                   self.v]
        self.v = np.select(conditions, choices)
        self.mAlpha = ((0.001 * 6.43) * (self.v + 154.9)) / (np.exp(((self.v + 154.9) / 11.9)) - 1)
        self.mBeta = (0.001 * 193) * np.exp((self.v / 33.1))
        self.mInf = self.mAlpha / (self.mAlpha + self.mBeta)
        self.mTau = 1 / (self.mAlpha + self.mBeta)

    def update(self, x_range):
        super().update(x_range)
        self.x_range = x_range
        self.rates()
        self.update_constant_state_vars(x_range)

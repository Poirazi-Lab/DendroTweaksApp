import numpy as np
try:
    from ..channels import CustomCalciumDependentIonChannel
except:
    from channels import CustomCalciumDependentIonChannel

class Hay_SK_E2(CustomCalciumDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Hay_SK_E2', suffix='SK_E2', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0.0 # mho/cm2
        self.zTau = 1 # ms
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.cai = np.logspace(-5, 5, 1000)
        self.state_vars = {
            "z": {
                "inf": "zInf",
                "tau": "zTau",
                "power": 1
            },
        }

    def rates(self, cai):
        conditions = [self.cai < 1e-07,
                      ~(self.cai < 1e-07)]
        choices = [cai + 1e-07,
                   self.cai]
        self.cai = np.select(conditions, choices)
        self.zInf = 1 / (1 + ((0.00043 / cai) ** 4.8))

    def update(self, x_range):
        super().update(x_range)
        cai = x_range
        self.x_range = x_range
        self.rates(cai, )
        self.update_constant_state_vars(x_range)

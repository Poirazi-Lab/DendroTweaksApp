import numpy as np
try:
    from ..channels import CustomCalciumDependentIonChannel
except:
    from channels import CustomCalciumDependentIonChannel

class Poirazi_kca(CustomCalciumDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_kca', suffix='kca', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0.0 # mho/cm2
        self.beta = 0.03 # 1/ms
        self.cac = 0.025 # mM
        self.taumin = 0.5 # ms
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.cai = np.logspace(-5, 5, 1000)
        self.state_vars = {
            "m": {
                "inf": "m_inf",
                "tau": "tau_m",
                "power": 3
            },
        }

    def rates(self, v, cai):
        self.tadj = 3 ** ((self.celsius - 22.0) / 10)
        self.car = (cai / self.cac) ** 2
        self.m_inf = self.car / (1 + self.car)
        self.tau_m = ((1 / self.beta) / (1 + self.car)) / self.tadj
        conditions = [self.tau_m < self.taumin,
                      ~(self.tau_m < self.taumin)]
        choices = [self.taumin,
                   self.tau_m]
        self.tau_m = np.select(conditions, choices)

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        cai = x_range
        self.x_range = x_range
        self.rates(v, cai, )
        self.update_constant_state_vars(x_range)

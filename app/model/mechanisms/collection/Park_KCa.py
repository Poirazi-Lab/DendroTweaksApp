import numpy as np
try:
    from ..channels import CustomCalciumDependentIonChannel
except:
    from channels import CustomCalciumDependentIonChannel

class Park_KCa(CustomCalciumDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Park_KCa', suffix='kca', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0.0 # S/cm2
        self.caix = 1 # 1
        self.Ra = 0.01 # /ms
        self.Rb = 0.02 # /ms
        self.temp = 23 # degC
        self.q10 = 2.3 # 1
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.cai = np.logspace(-5, 5, 1000)
        self.state_vars = {
            "n": {
                "inf": "ninf",
                "tau": "ntau",
                "power": 1
            },
        }

    def rates(self, cai):
        self.tadj = self.q10 ** ((self.celsius - self.temp) / 10)
        self.alpn = self.Ra * ((1 * cai) ** self.caix)
        self.betn = self.Rb
        self.ntau = 1 / (self.tadj * (self.alpn + self.betn))
        self.ninf = self.alpn / (self.alpn + self.betn)

    def update(self, x_range):
        super().update(x_range)
        cai = x_range
        self.x_range = x_range
        self.rates(cai, )
        self.update_constant_state_vars(x_range)

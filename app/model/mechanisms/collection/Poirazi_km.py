import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Poirazi_km(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_km', suffix='kmp', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0 # pS/um2
        self.tha = -30 # mV
        self.qa = 9 # mV
        self.Ra = 0.001 # /ms
        self.Rb = 0.001 # /ms
        self.temp = 23 # degC
        self.q10 = 2.3 # 
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "n": {
                "inf": "ninf",
                "tau": "ntau",
                "power": 1
            },
        }

    def rates(self, v):
        self.tadj = self.q10 ** ((self.celsius - self.temp) / 10)
        self.a = (self.Ra * (v - self.tha)) / (1 - np.exp((-((v - self.tha)) / self.qa)))
        self.b = (-(self.Rb) * (v - self.tha)) / (1 - np.exp(((v - self.tha) / self.qa)))
        self.ntau = 1 / (self.a + self.b)
        self.ninf = self.a * self.ntau

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

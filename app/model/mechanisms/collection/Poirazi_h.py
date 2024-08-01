import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Poirazi_h(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_h', suffix='h', cell=cell)
        self.nonspecific_current = 'i'
        self.range_params = [
            'vhalf',
            'K',
            'e',
        ]
        self.gbar = 0.0 # mho/cm2
        self.e = -10 # mV
        self.K = 8.5 # mV
        self.vhalf = -90 # mV
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "n": {
                "inf": "ninf",
                "tau": "taun",
                "power": 1
            },
        }

    def rates(self, v):
        self.ninf = 1 - (1 / (1 + np.exp(((self.vhalf - v) / self.K))))
        conditions = [self.v > -(30),
                      ~(self.v > -(30))]
        choices = [1,
                   2 * ((1 / (np.exp(((v + 145) / -(17.5))) + np.exp(((v + 16.8) / 16.5)))) + 5)]
        self.taun = np.select(conditions, choices)

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

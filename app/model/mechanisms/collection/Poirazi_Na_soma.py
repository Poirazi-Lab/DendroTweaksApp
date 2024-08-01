import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Poirazi_Na_soma(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_Na_soma', suffix='nav_soma', cell=cell)
        self.ion = 'na'
        self.range_params = [
            'gbar',
            'ar2',
        ]
        self.gbar = 0 # S/cm2
        self.a0r = 0.0003 # ms
        self.b0r = 0.0003 # ms
        self.zetar = 12 # 
        self.gmr = 0.2 # 
        self.ar2 = 1.0 # 
        self.taumin = 3 # ms
        self.vvs = 2 # mV
        self.vhalfr = -60 # mV
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "m": {
                "inf": "minf",
                "tau": "mtau",
                "power": 2
            },
            "h": {
                "inf": "hinf",
                "tau": "htau",
                "power": 1
            },
            "s": {
                "inf": "sinf",
                "tau": "stau",
                "power": 1
            },
        }

    def alpv(self, v, vh):
        alpv = (1 + (self.ar2 * np.exp(((v - vh) / self.vvs)))) / (1 + np.exp(((v - vh) / self.vvs)))
        return alpv

    def alpr(self, v):
        alpr = np.exp(((((0.001 * self.zetar) * (v - self.vhalfr)) * 96480.0) / (8.315 * (273.16 + self.celsius))))
        return alpr

    def betr(self, v):
        betr = np.exp((((((0.001 * self.zetar) * self.gmr) * (v - self.vhalfr)) * 96480.0) / (8.315 * (273.16 + self.celsius))))
        return betr

    def rates(self, v):
        self.minf = 1 / (1 + np.exp(((v + 44) / -3)))
        self.mtau = 0.05
        self.hinf = 1 / (1 + np.exp(((v + 49) / 3.5)))
        self.htau = 1
        self.sinf = self.alpv(v, self.vhalfr)
        self.tmp = self.betr(v) / (self.a0r + (self.b0r * self.alpr(v)))
        conditions = [self.tmp < self.taumin,
                      ~(self.tmp < self.taumin)]
        choices = [self.taumin,
                   self.tmp]
        self.tmp = np.select(conditions, choices)
        self.stau = self.tmp

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

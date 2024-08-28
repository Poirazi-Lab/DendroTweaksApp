import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Park_Kv_standard(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Park_Kv_standard', suffix='kvs', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
            'vhalf_n',
            'sigma_n',
            'k_n',
            'delta_n',
            'tau0_n',
        ]
        self.gbar = 0.0 # S/cm2
        self.vhalf_n = 14.164 # mV
        self.sigma_n = 9.0 # mV
        self.k_n = 0.123 # 1/ms
        self.delta_n = 0.731 # 1
        self.tau0_n = 0.881 # ms
        self.temp = 23 # degC
        self.q10 = 2.3 # 1
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "n": {
                "inf": "n_inf",
                "tau": "tau_n",
                "power": 1
            },
        }

    def alpha_prime(self, v, k, delta, vhalf, sigma):
        alpha_prime = k * np.exp(((delta * (v - vhalf)) / sigma))
        return alpha_prime

    def beta_prime(self, v, k, delta, vhalf, sigma):
        beta_prime = k * np.exp(((-((1 - delta)) * (v - vhalf)) / sigma))
        return beta_prime

    def rates(self, v):
        self.tadj = self.q10 ** ((self.celsius - self.temp) / 10)
        self.n_inf = 1 / (1 + np.exp((-((v - self.vhalf_n)) / self.sigma_n)))
        self.alpha_n = self.alpha_prime(v, self.k_n, self.delta_n, self.vhalf_n, self.sigma_n)
        self.beta_n = self.beta_prime(v, self.k_n, self.delta_n, self.vhalf_n, self.sigma_n)
        self.tau_n = ((1 / (self.alpha_n + self.beta_n)) + self.tau0_n) / self.tadj

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)

# This Python channel class was automatically generated from a MOD file
# using DendroTweaks toolbox, dendrotweaks.dendrites.gr

from dendrotweaks.mechanisms.mechanisms import CustomIonChannel
import numpy as np

class Kv(CustomIonChannel):
    """
    Kv_Park_ref
    """

    def __init__(self, name="Kv"):
        super().__init__(name=name)
        self.channel_params = {
            "Kv_gbar": 0.0,
            "Kv_Ra": 0.02,
            "Kv_Rb": 0.006,
            "Kv_v12": 25,
            "Kv_q": 9,
            "Kv_temp": 23,
            "Kv_q10": 2.3
            }
        self.channel_states = {
            "Kv_n": 0.0
            }
        self._state_powers = {
            "Kv_n": 1
            }
        self.celsius = 37
        self.ion = "k"
        self.current_name = "i_k"

        self.independent_var_name = "v"
        

    # @property
    # def tadj(self):
    #     return self.tadj = q10 ** ((celsius - temp) / 10)

    def __getitem__(self, item):
        return self.channel_params[item]

    def __setitem__(self, item, value):
        self.channel_params[item] = value
    def rateconst(self, v, r, th, q):
        rateconst = (r * (v - th)) / (1 - np.exp((-((v - th)) / q)))
        return rateconst
    
    def compute_kinetic_variables(self, v):
        Ra = self.channel_params.get("Kv_Ra", 1)
        Rb = self.channel_params.get("Kv_Rb", 1)
        v12 = self.channel_params.get("Kv_v12", 1)
        q = self.channel_params.get("Kv_q", 1)
        temp = self.channel_params.get("Kv_temp", 1)
        q10 = self.channel_params.get("Kv_q10", 1)
        
        self.tadj = q10 ** ((self.celsius - temp) / 10)
        alpn = self.rateconst(v, Ra, v12, q)
        betn = self.rateconst(v, -(Rb), v12, -(q))
        nTau = 1 / (self.tadj * (alpn + betn))
        nInf = alpn / (alpn + betn)
        return nInf, nTau

# This Python channel class was automatically generated from a MOD file
# using DendroTweaks toolbox, dendrotweaks.dendrites.gr

from dendrotweaks.mechanisms.mechanisms import CustomIonChannel
import numpy as np

class Na(CustomIonChannel):
    """
    Na channel
    """

    def __init__(self, name="Na"):
        super().__init__(name=name)
        self.channel_params = {
            "Na_gbar": 0.0,
            "Na_Rma": 0.182,
            "Na_Rmb": 0.14,
            "Na_v12m": -30,
            "Na_qm": 9.8,
            "Na_Rhb": 0.0091,
            "Na_Rha": 0.024,
            "Na_v12ha": -45,
            "Na_v12hb": -70,
            "Na_qh": 5,
            "Na_v12hinf": -60,
            "Na_qhinf": 6.2,
            "Na_temp": 23,
            "Na_q10": 2.3
            }
        self.channel_states = {
            "Na_m": 0.0,
            "Na_h": 0.0
            }
        self._state_powers = {
            "Na_m": 3,
            "Na_h": 1
            }
        self.celsius = 37
        self.ion = "na"
        self.current_name = "i_na"

        self.independent_var_name = "v"
        

    # @property
    # def tadj(self):
    #     return self.tadj = q10 ** ((celsius - temp) / 10)

    def __getitem__(self, item):
        return self.channel_params[item]

    def __setitem__(self, item, value):
        self.channel_params[item] = value
    def rateconst2(self, v, r, v12, q):
        conditions = [np.abs(((v - v12) / q)) > 1e-06,
        ~(np.abs(((v - v12) / q)) > 1e-06)]
        choices = [(r * (v - v12)) / (1 - np.exp((-((v - v12)) / q))),
        r * q]
        rateconst2 = np.select(conditions, choices)
        return rateconst2
    
    
    def rateconst(self, v, r, v12, q):
        conditions = [np.abs(((v - v12) / q)) > 1e-06,
        ~(np.abs(((v - v12) / q)) > 1e-06)]
        choices = [(r * (v - v12)) / (1 - np.exp((-((v - v12)) / q))),
        r * q]
        rateconst = np.select(conditions, choices)
        return rateconst
    
    def compute_kinetic_variables(self, v):
        Rma = self.channel_params.get("Na_Rma", 1)
        Rmb = self.channel_params.get("Na_Rmb", 1)
        v12m = self.channel_params.get("Na_v12m", 1)
        qm = self.channel_params.get("Na_qm", 1)
        Rhb = self.channel_params.get("Na_Rhb", 1)
        Rha = self.channel_params.get("Na_Rha", 1)
        v12ha = self.channel_params.get("Na_v12ha", 1)
        v12hb = self.channel_params.get("Na_v12hb", 1)
        qh = self.channel_params.get("Na_qh", 1)
        v12hinf = self.channel_params.get("Na_v12hinf", 1)
        qhinf = self.channel_params.get("Na_qhinf", 1)
        temp = self.channel_params.get("Na_temp", 1)
        q10 = self.channel_params.get("Na_q10", 1)
        
        self.tadj = q10 ** ((self.celsius - temp) / 10)
        alpm = self.rateconst(v, Rma, v12m, qm)
        betm = self.rateconst(-(v), Rmb, -(v12m), qm)
        alph = self.rateconst(v, Rha, v12ha, qh)
        beth = self.rateconst(-(v), Rhb, -(v12hb), qh)
        mTau = 1 / (self.tadj * (alpm + betm))
        mInf = alpm / (alpm + betm)
        hTau = 1 / (self.tadj * (alph + beth))
        hInf = 1 / (1 + np.exp(((v - v12hinf) / qhinf)))
        return mInf, mTau, hInf, hTau

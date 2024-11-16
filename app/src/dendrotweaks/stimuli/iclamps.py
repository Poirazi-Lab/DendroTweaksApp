from neuron import h
h.load_file('stdrun.hoc')

class IClamp():

    def __init__(self, seg, amp=0, delay=100, dur=100):
        self.seg = seg
        self._iclamp = h.IClamp(seg._ref)
        self._iclamp.amp = amp
        self._iclamp.delay = delay
        self._iclamp.dur = dur
        
    @property
    def amp(self):
        return self._iclamp.amp

    @amp.setter
    def amp(self, new_amp):
        self._iclamp.amp = new_amp


    @property
    def delay(self):
        return self._iclamp.delay

    @delay.setter
    def delay(self, new_delay):
        self._iclamp.delay = new_delay

    @property
    def dur(self):
        return self._iclamp.dur

    @dur.setter
    def dur(self, new_dur):
        self._iclamp.dur = new_dur
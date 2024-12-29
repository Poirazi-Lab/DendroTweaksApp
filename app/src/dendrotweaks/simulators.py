from collections import defaultdict

class Simulator:
    def __init__(self):
        pass


class NEURONSimulator(Simulator):
    """
    A class to represent a NEURON simulator.
    """

    def __init__(self, celsius=37, v_init=-70, dt=0.025, cvode=False):
        super().__init__()
        from neuron import h
        from neuron.units import ms, mV
        self.h = h
        self.h.load_file('stdrun.hoc')
        # self.h.load_file('import3d.hoc')
        # self.h.load_file('nrngui.hoc')
        # self.h.load_file('import3d')

        self.celsius = celsius
        self.v_init = v_init * mV

        self.dt = dt
        self._cvode = cvode

        self._recordings = defaultdict(dict)
        # self.t = []

    @property
    def recordings(self):
        return [rec for sec in self._recordings.values() for rec in sec.values()]

    def add_recording(self, sec, loc, var='v'):
        if self._recordings.get(sec):
            if self._recordings[sec].get(loc):
                self.remove_recording(sec, loc)
        seg = sec(loc)
        self._recordings[sec][loc] = self.h.Vector().record(getattr(seg, f'_ref_{var}'))

    def remove_recording(self, sec, loc, var='v'):
        if self._recordings.get(sec):
            if self._recordings[sec].get(loc):
                self._recordings[sec][loc] = None
                self._recordings[sec].pop(seg)
            if not self._recordings[sec]:
                self._recordings.pop(sec)

    def remove_all_recordings(self):
        for sec in self._recordings.keys():
            for loc in self._recordings[sec].keys():
                self.remove_recording(sec, loc)
        # self.recordings = {}

    def _init_simulation(self):
        self.h.CVode().active(self._cvode)
        self.h.celsius = self.celsius
        self.h.dt = self.dt
        self.h.stdinit()
        self.h.init()
        self.h.finitialize(self.v_init)
        if self.h.cvode.active():
            self.h.cvode.re_init()
        else:
            self.h.fcurrent()
        self.h.frecord_init()

    def run(self, duration=300):

        from neuron.units import ms, mV

        vs = self.recordings
        Is = []

        # for v in self.recordings.values():
        #     # v = h.Vector().record(seg._ref_v)
        #     vs.append(v)

        t = self.h.Vector().record(self.h._ref_t)
        self.t = t

        # if self.ch is None:
        #     pass
        # else:
        #     for seg in self.recordings.keys():
        #         if getattr(seg, f'_ref_i_{self.ch.suffix}', None) is None:
        #             logger.warning(
        #                 f'No current recorded for {self.ch.suffix} at {seg}. Make i a RANGE variable in mod file.')
        #             continue
        #         I = h.Vector().record(getattr(seg, f'_ref_i_{self.ch.suffix}'))
        #         Is.append(I)

        self._init_simulation()

        self.h.continuerun(duration * ms)

        return [t.to_python() for _ in vs], [v.to_python() for v in vs], [i.to_python() for i in Is]

    def to_dict(self):
        return {
            'temperature': self.celsius,
            'v_init': self.v_init,
            'dt': self.dt,
        }


class JaxleySimulator(Simulator):
    """
    A class to represent a Jaxley simulator.
    """

    def __init__(self):
        super().__init__()
        ...

    

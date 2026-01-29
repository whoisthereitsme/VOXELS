from __future__ import annotations
import time



class Timer:
    def __init__(self) -> None:
        self.coarse_ns = 2_000_000
        self.spin_ns = 1_000_000

        self.start()

    def nowns(self) -> int:  # can be used as Timer().nowns()
        return time.perf_counter_ns()
    
    @staticmethod   # can be used as Timer.now()
    def now() -> float:
        return time.perf_counter_ns()

    def start(self) -> int:
        self.started = self.nowns()
        self.t0 = self.started
        self.delta = []
        self.times = []
        return self.t0
    
    def lap(self) -> int:
        t1 = self.nowns()
        t0 = self.t0
        self.t0 = t1
        dt = round((t1 - t0) / 1e9, 6) # seconds
        self.delta.append(dt)
        self.times.append(t1)
        return dt       # time since last lap in seconds
    
    def stop(self) -> int:
        self.lap()
        first = self.started
        last = self.times[-1]
        t = round((last - first) / 1e9, 6) # seconds with 6 decimal places (microseconds) 
        return t        # total since started
    
    def print(self, msg:str=None) -> None:
        self.lap()
        txt = f"lap {len(self.delta)}: {self.delta[-1]} seconds, total {round((self.times[-1] - self.started) / 1e9, 6)} seconds"
        if msg is not None:
            txt = f"{msg}: {txt}"
        print(txt)

    def waitns(self, deadline_ns: int) -> None:
        coarse_ns = self.coarse_ns
        spin_ns = self.spin_ns

        while True:
            n = self.nowns()
            remaining = deadline_ns - n
            if remaining <= 0:
                return

            # FAR: sleep until within coarse_ns
            if remaining > coarse_ns:
                time.sleep((remaining - coarse_ns) / 1e9)
                continue

            # NEAR: yield until within spin_ns
            if remaining > spin_ns:
                time.sleep(0)
                continue

            # FINAL: busy-spin
            while self.nowns() < deadline_ns:
                pass
            return

    def wait(self, seconds: float) -> None:
        if seconds <= 0:
            return
        self.waitns(self.nowns() + int(seconds * 1e9))

    def reset(self) -> int:
        t = self.stop()
        self.start()
        return t  # total since started before reset


now = Timer.now # now: now() returns the current time in nanoseconds

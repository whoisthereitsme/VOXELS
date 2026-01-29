import threading
from typing import Any, Callable, Optional
import heapq
from .timer import Timer, now
from .event import Event, Handler



class Schedule:
    def __init__(self) -> None:
        self._timer = Timer()

        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._pq: list[Event] = []
        self._seq = 0

        self._worker: Optional[threading.Thread] = None
        self._stop = False
        self._running = False

        self.start()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._stop = False
            self._worker = threading.Thread(target=self._run, name="SchedulerWorker", daemon=True)
            self._running = True
            self._worker.start()

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._stop = True
            self._cv.notify_all()

        if self._worker:
            self._worker.join(timeout=2.0)

        with self._lock:
            self._running = False
            self._worker = None

    # --------------------
    # Scheduling API
    # --------------------

    def schedule(self, ns: int=None, fn: Callable[..., Any]=None, *args: Any, **kwargs: Any) -> Handler:
        with self._lock:
            self._seq += 1
            ev = Event(due_ns=ns, seq=self._seq, callback=fn, args=args, kwargs=kwargs)
            heapq.heappush(self._pq, ev)
            self._cv.notify_all()
            return Handler(self, ev)

    def new(self, seconds:float=None, fn:Callable[..., Any]=None, delay=False, *args: Any, **kwargs: Any) -> Handler:
        if delay==True:
            ns = now() + int(seconds * 1e9)
        if delay==False:
            ns = int(seconds * 1e9)
        return self.schedule(ns=ns, fn=fn, *args, **kwargs)
    

    def cancel(self, handle: Handler) -> bool:
        with self._lock:
            if handle._event.cancelled:
                return False
            handle._event.cancelled = True
            self._cv.notify_all()
            return True

    def _run(self) -> None:
        while True:
            with self._lock:
                # Wait until there is work or stop requested
                while not self._pq and not self._stop:
                    self._cv.wait()

                if self._stop:
                    return

                # Drop cancelled events at head
                while self._pq and self._pq[0].cancelled:
                    heapq.heappop(self._pq)

                if not self._pq:
                    continue

                ev = self._pq[0]
                due = ev.due_ns

            # 2) Wait until deadline (no lock held)
            self._timer.wait_until_ns(due)

            # 3) Pop-and-execute if still valid
            with self._lock:
                if self._stop:
                    return

                # Head may have changed; re-check
                if not self._pq:
                    continue
                if self._pq[0] is not ev:
                    continue

                heapq.heappop(self._pq)
                if ev.cancelled:
                    continue

            # Execute callback outside lock
            try:
                ev.callback(*ev.args, **ev.kwargs)
            except Exception as e:
                # Keep scheduler alive; replace with logging if desired
                print(f"[Schedule] callback error: {e!r}")






















# ============================================================
# Example usage
# ============================================================

if __name__ == "__main__":
    import time

    sched = Schedule()
    def hello(who:str=None, n:int=1) -> None:
        print(f"{time.perf_counter():.3f} hello {who} x{n}")
    def test(who:str=None,  n:int=1) -> None:
        print(who, n*n)

    h1 = sched.new(seconds=0.050, fn=test, who="A", n=2, delay=True)
    h2 = sched.new(seconds=0.120, fn=hello, who="B", n=3, delay=True)
    h3 = sched.new(seconds=0.080, fn=test, who="C", n=1, delay=True)
    h2.cancel()
    futuretime = time.perf_counter() + 0.100
    h4 = sched.new(seconds=futuretime, fn=hello, who="D", n=4, delay=False)
    h5 = sched.new(seconds=futuretime, fn=test, who="E", n=5, delay=False)
    h6 = sched.new(seconds=futuretime, fn=hello, who="F", n=6, delay=False)


    time.sleep(0.2)
    sched.stop()

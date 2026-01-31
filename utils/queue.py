from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from utils.mdx import MDX
    from utils.bvh import BVH
    from utils.job import Job



from queue import Empty, SimpleQueue
import threading





class Queue:
    def __init__(self, cls:MDX|BVH=None) -> None:
        self.cls: MDX|BVH = cls

        self.init()
        self.start()

    def init(self) -> None:
        self.results: dict[str, dict[int, Job]] = {"insert":{}, "remove":{}, "search":{}}
        self.pending: dict[str, dict[int, Job]] = {"insert":{}, "remove":{}, "search":{}}
        self.insertjobs, self.insertresp = SimpleQueue(), SimpleQueue()
        self.removejobs, self.removeresp = SimpleQueue(), SimpleQueue()
        self.searchjobs, self.searchresp = SimpleQueue(), SimpleQueue()

        self.threadinsert = threading.Thread(target=self.runinsert, daemon=True)
        self.threadremove = threading.Thread(target=self.runremove, daemon=True)
        self.threadsearch = threading.Thread(target=self.runsearch, daemon=True)
        self.threadresult = threading.Thread(target=self.runresult, daemon=True)

    def start(self) -> None:    
        self.running = True
        self.threadinsert.start()
        self.threadremove.start()
        self.threadsearch.start()
        self.threadresult.start()

    def stop(self) -> None:    
        self.running = False
        self.threadinsert.join()
        self.threadremove.join()
        self.threadsearch.join()
        self.threadresult.join()

    def runinsert(self) -> None:
         while self.running==True:
            job: Job = self.insertjobs.get()
            res: Job = self.cls.insert(job=job)
            self.insertresp.put(res)

    def runremove(self) -> None:
         while self.running==True:
            job: Job = self.removejobs.get()
            res: Job = self.cls.remove(job=job)
            self.removeresp.put(res)

    def runsearch(self) -> None:
         while self.running==True:
            job: Job = self.searchjobs.get()
            result:Job = self.cls.search(job=job)
            self.searchresp.put(result)

    def runresult(self) -> None:
        def save(job:Job=None) -> None:
            self.results[job.job][job.id] = job   

        def tryit(fn:callable=None) -> Job | None:
            try:
                job: Job = fn()
                save(job=job)       # fn() raises the Empty exception if no item was available within that time.
            except Empty:
                pass
            except Exception as e:
                print(f"[ERROR] Queue.runresult(): unexpected error:\n{e!r}")
        
        while self.running==True:
            workload = self.workload()
            if workload == 0:
                wait = 0.001
            else:
                wait = 0.0
            block = True if wait > 0.0 else False
            tryit(fn=lambda call=self.insertresp.get, time=wait, block=block: call(timeout=time, block=block)) # raises the Empty exception if no item was available within that time.
            tryit(fn=lambda call=self.removeresp.get, time=0.00, block=False: call(timeout=time, block=block)) # raises the Empty exception if no item was available within that time.
            tryit(fn=lambda call=self.searchresp.get, time=0.00, block=False: call(timeout=time, block=block)) # raises the Empty exception if no item was available within that time.


    def insert(self, job:Job=None) -> None:
        self.insertjobs.put(job)

    def remove(self, job:Job=None) -> None:
        self.removejobs.put(job)

    def search(self, job:Job=None) -> None:
        self.searchjobs.put(job)

    def job(self, job:Job=None) -> None:
        # at this point the job is allready distributed to the right class in ROWS.job(job=job) -> send to either mdx or bvh queue
        # so here i only need to send it to the right method in this queue
        # NOTE the validation of the right params is done in Job.validate() so here its safe to just call the right method
        if job.job in ("insert","remove","search")  :
            self.pending[job.job][job.id] = job   # keep track of pending jobs
        if job.job == "insert":
            self.insert(job=job)
        if job.job == "remove":
            self.remove(job=job)
        if job.job == "search":
            self.search(job=job)
        
    def workload(self) -> int:
        pending = sum(len(v) for v in self.pending.values())
        results = sum(len(v) for v in self.results.values())
        return pending - results

    def get(self, task:str=None, id:int=None) -> Job|None:
        if task not in ("insert","remove","search"):
            raise ValueError("Queue.get(): task must be 'insert','remove' or 'search'")
        if id is None:
            raise ValueError("Queue.get(): id must be provided")
        job: Job = self.results[task].pop(id, None)
        if job is not None:
            self.pending[task].pop(id, None)   # remove from pending as well
        return job # return the whole job instence so the caller can check if its ready and get the result -> job can be None too!!!



# self.bvh = Queue(cls=self.bvh)
# self.mdx = Queue(cls=self.mdx)
# usage:
# self.job(job=job)  # job is an instence of Job -> distributes to the right queue
# result = self.get(task="search", id=some_id)  # for search jobs only
# result = self.get(task="insert", id=some_id)  # for insert jobs only
# result = self.get(task="remove", id=some_id)  # for remove jobs only
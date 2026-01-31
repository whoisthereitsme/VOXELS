from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from utils.types import Row
    from utils.mdx import MDX
    from utils.bvh import BVH
    from utils.types import POS


from queue import SimpleQueue
import threading




class Queue:
    def __init__(self, cls:MDX|BVH=None, lock:threading.Lock=None) -> None:
        self.cls: MDX|BVH = cls

        self.init()
        self.start()

    def init(self) -> None:
        self.queueinsert: SimpleQueue = SimpleQueue()
        self.queueremove: SimpleQueue = SimpleQueue()
        self.queuesearch: SimpleQueue = SimpleQueue()
        self.queueanswer: SimpleQueue = SimpleQueue()
        self.threadinsert = threading.Thread(target=self.runinsert, daemon=True)
        self.threadremove = threading.Thread(target=self.runremove, daemon=True)
        self.threadsearch = threading.Thread(target=self.runsearch, daemon=True)

    def start(self) -> None:    
        self.threadinsert.start()
        self.threadremove.start()
        self.threadsearch.start()

    def stop(self) -> None:    
        self.threadinsert.join()
        self.threadremove.join()
        self.threadsearch.join()

    def runinsert(self) -> None:
         while True:
            self.cls.insert(row=self.queueinsert.get())

    def runremove(self) -> None:
         while True:
            self.cls.remove(row=self.queueremove.get())

    def runsearch(self) -> None:
         while True:
            self.queueanswer.put(self.cls.search(pos=self.queuesearch.get()))
            
    def insert(self, row:Row=None) -> None:
        self.queueinsert.put(row)

    def remove(self, row:Row=None) -> None:
        self.queueremove.put(row)

    def search(self, pos:POS=None) -> any:
        self.queuesearch.put(pos)
        return self.queueanswer.get()

    def add(self, row:Row=None, pos:POS=None, insert:bool=False, remove:bool=False) -> None:
        if row is not None and insert==True:
            self.insert(row=row)
        if row is not None and remove==True:
            self.remove(row=row)
        if pos is not None and insert==False and remove==False:
            self.search(pos=pos)

    def get(self) -> Row:
        return self.queueanswer.get()

# and then i ROWS 
# self.bvh = Queue(cls=self.bvh)
# self.mdx = Queue(cls=self.mdx)
# usage
# self.bvh.add(row=row, insert=True)
# self.bvh.add(row=row, remove=True)
# self.mdx.add(row=row, insert=True)
# self.mdx.add(row=row, remove=True)

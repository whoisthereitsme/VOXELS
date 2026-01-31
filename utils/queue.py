from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from utils.types import Row
    from utils.mdx import MDX
    from utils.bvh import BVH



from queue import SimpleQueue
import threading




class Queue:
    def __init__(self, cls:MDX|BVH=None, lock:threading.Lock=None) -> None:
        self.cls: MDX|BVH = cls
        self.lock = lock

        self.init()

    def init(self) -> None:
        self.queueinsert: SimpleQueue = SimpleQueue()
        self.queueremove: SimpleQueue = SimpleQueue()
        threading.Thread(target=self.runinsert, daemon=True).start()
        threading.Thread(target=self.runremove, daemon=True).start()

    def runinsert(self) -> None:
         while True:
            self.cls.insert(row=self.queueinsert.get())

    def runremove(self) -> None:
         while True:
            self.cls.remove(row=self.queueremove.get())

    def insert(self, row:Row=None) -> None:
        self.queueinsert.put(row)

    def remove(self, row:Row=None) -> None:
        self.queueremove.put(row)

    def add(self, row:Row=None, insert:bool=False, remove:bool=False) -> None:
        if insert==True:
            self.insert(row=row)
        if remove==True:
            self.remove(row=row)

# and then i ROWS 
# self.bvh = Queue(cls=self.bvh)
# self.mdx = Queue(cls=self.mdx)
# usage
# self.bvh.add(row=row, insert=True)
# self.bvh.add(row=row, remove=True)
# self.mdx.add(row=row, insert=True)
# self.mdx.add(row=row, remove=True)

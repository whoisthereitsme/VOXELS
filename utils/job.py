from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from utils.types import Row
    from utils.types import POS



class Job: 
    id = 0
    def __init__(self, row:Row=None, axis:int=None, pos:POS=None, job:str=None, cls:str=None) -> None:
        """
        - JOBS=["insert", "remove", "search"]
        - CLSS=["mdx", "bvh"]
        - ARGS=DEPENDS ON JOB AND CLASS
         
        - 1. [bhv args = row] --- [mdx args = row] for insert
        - 2. [bhv args = row] --- [mdx args = row] for remove
        - 3. [bhv args = pos] --- [mdx args = row, axis] for search

        """
        self.row: Row = row
        self.axis: int = axis
        self.pos: POS = pos
        self.job: str = job    # "insert","remove","search"
        self.cls: str = cls      # "mdx","bvh"

        self.init()

    def init(self) -> None:
        self.id: int = self.getid()
        self.result: Row = None
        self.ready: bool = False

        self.validate()

    def getid(self) -> int:
        id: int = Job.id
        Job.id += 1
        return id

    def validate(self) -> None:
        # CHECK VALIDITY OF JOB AND CLASS
        if self.job not in ("insert", "remove", "search"):
            raise ValueError("Task.job must be 'insert','remove','search'")
        if self.cls not in ("mdx","bvh"):
            raise ValueError("Task.cls must be 'mdx','bvh'")
        
        # CHECK REQUIRED PARAMS FOR JOB AND CLASS -> WITHOUT THE RIGHT PARAMS THE JOB CANNOT BE DONE
        if self.job in ("insert","remove") and self.row is None:        # insert/remove needs row
            raise ValueError("Task.row is required for insert/remove jobs")
        if self.job == "search":
            if self.cls == "mdx" and (self.row is None or self.axis is None):   # mdx search needs row and axis
                raise ValueError("Task.row and Task.axis are required for mdx search jobs")
            if self.cls == "bvh" and self.pos is None:                          # bvh search needs pos
                raise ValueError("Task.pos is required for bvh search jobs")
        

    def finish(self, row:Row=None) -> None:      # only needed for search tasks -> insert/remove dont return anything buit can be marked as done anyway
        if self.result is None:
            row = self.row   # for insert/remove tasks we can return the row that was inserted/removed as result (its relevant info and its the same type as search result)
        self.result:Row = row 
        self.ready = True   

    def get(self) -> Row|None:  # return result if ready
        if self.ready==True:
            return self.result  # at this point result is a Row instence
        return None             # not ready yet


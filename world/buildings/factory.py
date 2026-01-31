from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from world.rows import ROWS



from .warehouse import Warehouse
from utils.types import POS



class Recipe:
    def __init__(self, ins:dict[str,int]=None, outs:dict[str,int]=None, ticks:int=0) -> None:
        self.ins:dict[str,int] = ins if ins is not None else {}
        self.outs:dict[str,int] = outs if outs is not None else {}

        self.ticks:int = ticks

        self.init()

    def init(self) -> None:
        self.tick = 0

    def ready(self) -> Recipe|None:
        self.tick += 1
        if self.tick >= self.ticks:
            self.tick = 0
            return self
        return None    



class Factory:    
    def __init__(self, rows:ROWS=None, pos:POS=None, recipe:Recipe=None, warehouse:Warehouse=None) -> None:
        self.rows:ROWS      = rows
        self.pos:POS        = pos 
        self.recipe:Recipe  = recipe
        self.warehouse:Warehouse = warehouse

    def update(self) -> None:
        if self.canproduce():
            self.produce(self.recipe)

    def canproduce(self) -> bool:
        canproduce = False
        if self.recipe.ready():
            if self.enoughmats():
                canproduce = True
        return canproduce
    
    def enoughmats(self, mat:str=None, amount:int=None) -> bool:
        enough: bool = True
        for mat, amount in self.recipe.ins.items():
            if self.warehouse.rows.materials.get(mat, 0) < amount:
                enough = False
                break
        return enough
              
            















class MATERIALS:
    TYPES = {
        "INVIS": 0,     # start at 16384                # invisible
        "TRANS": 1,     # start at 32768                # transparent
        "SOLID": 2,     # start at 65536                # solid
        "ROCKS": 3,     # start at 4294967296           # indestructible
    }

    DATA  = {
        "AIR":      (16384+0,     TYPES["INVIS"]),

        "WATER":    (32768+0,     TYPES["TRANS"]), 
        "LAVA":     (32768+1,     TYPES["TRANS"]),
        "GLASS":    (32768+2,     TYPES["TRANS"]),

        "STONE":    (65536+0,     TYPES["SOLID"]),
        "OBSIDIAN": (65536+1,     TYPES["SOLID"]),

        "BEDROCK":  (4294967296+0,TYPES["ROCKS"]),
    }

    IDX = {name: i for i, name in enumerate(DATA.keys())}

    NUM = len(DATA)

class Material:
    def __init__(self, name:str=None) -> None:
        self.id, self.type = MATERIALS.DATA.get(name, (None, None)) 
        self.idx = MATERIALS.IDX.get(name, None) 
        if self.id is None or self.type is None or self.idx is None:
            raise ValueError(f"Invalid material name: {name}")

    def isrocks(self) -> bool:
        return self.type == MATERIALS.TYPES["ROCKS"]

    def issolid(self) -> bool:
        return self.type == MATERIALS.TYPES["SOLID"]
    
    def istrans(self) -> bool:
        return self.type == MATERIALS.TYPES["TRANS"]
    
    def isinvisible(self) -> bool:
        return self.type == MATERIALS.TYPES["INVIS"]
    
    def isindestructible(self) -> bool:
        return self.type == MATERIALS.TYPES["ROCKS"]

class Materials:
    idx2name = {idx: name for name, idx in MATERIALS.IDX.items()}
    name2idx = MATERIALS.IDX

    name2id  = {name: pair[0] for name, pair in MATERIALS.DATA.items()}
    id2name  = {pair[0]: name for name, pair in MATERIALS.DATA.items()}

    # the one you actually need:
    id2idx   = {pair[0]: MATERIALS.IDX[name] for name, pair in MATERIALS.DATA.items()}
    idx2id   = {MATERIALS.IDX[name]: pair[0] for name, pair in MATERIALS.DATA.items()}


    def __init__(self) -> None:
        for name in MATERIALS.DATA.keys():
            setattr(self, name.lower(), Material(name=name))

    def idx(self, name: str = None, id: int = None) -> int:
        if (name is None) == (id is None):
            raise ValueError("Provide exactly one of name or id")
        return self.name2idx[name] if name is not None else self.id2idx[id]

    def id(self, name: str = None, idx: int = None) -> int:
        if (name is None) == (idx is None):
            raise ValueError("Provide exactly one of name or idx")
        return self.name2id[name] if name is not None else self.idx2id[idx]

    def name(self, id: int = None, idx: int = None) -> str:
        if (id is None) == (idx is None):
            raise ValueError("Provide exactly one of id or idx")
        return self.id2name[id] if id is not None else self.idx2name[idx]


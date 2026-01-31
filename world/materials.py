














class MATERIALS:
    """
    PRIVATE:
    -> Use the Materials class for lookups.
    """
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

    MID = {name: i for i, name in enumerate(DATA.keys())}
    NUM = len(DATA)

class Material:
    """
    PRIVATE:
    -> Use the Materials class for lookups.
    """
    def __init__(self, name:str=None) -> None:
        self.idx, self.type = MATERIALS.DATA.get(name, (None, None)) 
        self.mid = MATERIALS.MID.get(name, None) 
        if self.mid is None or self.type is None or self.idx is None:
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
    """
    PRIVATE:
    -> Various material lookup dictionaries for name, mid, and idx.
    """
    mid2name = {idx: name for name, idx in MATERIALS.MID.items()}
    name2mid = MATERIALS.MID
    name2idx  = {name: pair[0] for name, pair in MATERIALS.DATA.items()}
    idx2name  = {pair[0]: name for name, pair in MATERIALS.DATA.items()}
    idx2mid   = {pair[0]: MATERIALS.MID[name] for name, pair in MATERIALS.DATA.items()}
    mid2idx   = {MATERIALS.MID[name]: pair[0] for name, pair in MATERIALS.DATA.items()}
    """
    PRIVATE END
    """

    def __init__(self) -> None:
        for name in MATERIALS.DATA.keys():
            setattr(self, name.lower(), Material(name=name))

    def idx(self, name:str=None, mid:int=None) -> int:
        """
        PUBLIC:
        -> Get the material index (idx) given either the material name or mid.
        -> Provide exactly one of name or mid.
        """
        if (name is None) == (mid is None):
            raise ValueError("Provide exactly one of name or mid")
        return self.name2idx[name] if name is not None else self.mid2idx[mid]

    def mid(self, name:str=None, idx:int=None) -> int:
        """
        PUBLIC:
        -> Get the material ID (mid) given either the material name or idx.
        -> Provide exactly one of name or idx.
        """
        if (name is None) == (idx is None):
            raise ValueError("Provide exactly one of name or idx")
        return self.name2mid[name] if name is not None else self.idx2mid[idx]

    def name(self, mid:int=None, idx:int=None) -> str:
        """
        PUBLIC:
        -> Get the material name given either the material ID (mid) or idx.
        -> Provide exactly one of mid or idx.
        """
        if (mid is None) == (idx is None):
            raise ValueError("Provide exactly one of mid or idx")
        return self.mid2name[mid] if mid is not None else self.idx2name[idx]
    
    def names(self) -> list[str]:
        """
        PUBLIC:
        -> Get a list of all material names.
        """
        return list(MATERIALS.DATA.keys())
    
    def idxs(self) -> list[int]:
        """
        PUBLIC:
        -> Get a list of all material indices (idx).
        """
        return [pair[0] for pair in MATERIALS.DATA.values()]
    
    def mids(self) -> list[int]:
        """
        PUBLIC:
        -> Get a list of all material IDs (mid).
        """
        return list(MATERIALS.MID.values())

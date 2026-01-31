from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


import numpy as np
from world.materials import Materials, MATERIALS
from world.row import ROW
from utils.bvh import BVH
from utils.mdx import MDX
from utils.types import POS, SIZE, NDARR, REQS






class ROWS:
    """
    PUBLIC (human interface):
    - insert(p0:POS, p1:POS, mat:str, dirty:bool=True, alive:bool=True)
    - split(pos:POS, pos1:POS=None, mat:str=None)
    - merge(rows:NDARR=None)
    - volume(mat:str=None)
    - get(mat:str, rid:int)

    INTERNAL (row-first):
    - mid(row)
    - rid(row)
    - slot(row)
    - set(row, newrid:int=None, newmat:str=None)
    - reset(row)
    - remove(row)
    - merge2(row0, row1)
    """

    SIZE=65536

    def __init__(self)->None:
        self.mat=Materials()
        self.bvh=BVH(rows=self)
        self.mdx=MDX(rows=self)

        self.total=0
        self.array,self.arids=self.reqs(n=ROWS.SIZE)
        self.shape=self.array.shape
        self.nbytes=self.array.nbytes
        self.gbytes=self.nbytes/(1024**3)

        self.p0=(ROW.XMIN,ROW.YMIN,ROW.ZMIN)
        self.p1=(ROW.XMAX,ROW.YMAX,ROW.ZMAX)

        self.insert(p0=self.p0,p1=self.p1,mat="STONE")
        self.dim=self.size()
        self.vol=self.volume()

    # ============================================================
    # allocation / counters
    # ============================================================

    def reqs(self, n:int=None)->REQS:
        array=np.full((MATERIALS.NUM,n,*ROW.SHAPE),fill_value=ROW.SENTINEL,dtype=ROW.DTYPE)
        arids:dict[int,int]={mid:0 for mid in range(MATERIALS.NUM)}
        return (array,arids)

    def newn(self, mat:str=None)->int:
        mid=int(self.mat.mid(name=mat))
        n=self.arids[mid]
        self.arids[mid]+=1
        self.total+=1
        return int(n)

    def deln(self, mat:str=None)->int:
        mid=int(self.mat.mid(name=mat))
        if self.arids[mid]<=0:
            raise ValueError("no rows to free")
        self.arids[mid]-=1
        self.total-=1
        return int(self.arids[mid])

    def nrows(self, mat:str=None, mid:int=None)->int:
        if mid is None:
            if mat is None:
                raise ValueError("nrows requires mat or mid")
            mid=int(self.mat.mid(name=mat))
        return int(self.arids[int(mid)])

    # ============================================================
    # id helpers (row-only)
    # ============================================================

    def mid(self, row:NDARR=None)->int:
        if row is None:
            raise ValueError("mid requires row")
        return int(ROW.MID(row=row))

    def rid(self, row:NDARR=None)->int:
        if row is None:
            raise ValueError("rid requires row")
        return int(ROW.RID(row=row))

    # ============================================================
    # storage helpers (writes only here)
    # ============================================================

    def slot(self, row:NDARR=None)->NDARR:
        if row is None:
            raise ValueError("slot requires row")
        mid=self.mid(row=row)
        rid=self.rid(row=row)
        return self.array[mid][rid]

    def get(self, mat:str=None, rid:int=None)->NDARR:
        if mat is None or rid is None:
            raise ValueError("get requires mat and rid")
        mid=int(self.mat.mid(name=mat))
        return self.array[mid][int(rid)]

    def set(self, row:NDARR=None, newrid:int=None, newmat:str=None)->NDARR:
        if row is None:
            raise ValueError("set requires row")

        mid = int(ROW.MID(row=row))
        rid = int(ROW.RID(row=row))

        if mid == int(ROW.SENTINEL) or rid == int(ROW.SENTINEL):
            raise RuntimeError("set called on invalidated row")

        if newrid is not None:
            rid = int(newrid)
            row[*ROW.IDS_RID] = np.uint64(rid)

        if newmat is not None:
            mid = int(self.mat.mid(name=newmat))
            row[*ROW.IDS_MID] = np.uint64(mid)

        slot = self.array[mid][rid]
        slot[:] = row
        return slot

    def reset(self, row:NDARR=None)->None:
        if row is None:
            raise ValueError("reset requires row")
        self.slot(row=row)[:]=ROW.ARRAY

    # ============================================================
    # core ops (row-first internals)
    # ============================================================

    def insert(self, p0:POS=None, p1:POS=None, mat:str=None, dirty:bool=True, alive:bool=True)->NDARR:
        if mat is None:
            raise ValueError("insert requires mat")
        rid=self.newn(mat=mat)
        row=ROW.new(p0=p0,p1=p1,mat=mat,rid=rid,dirty=dirty,alive=alive)
        stored=self.set(row=row)
        self.bvh.insert(row=stored)
        self.mdx.insert(row=stored)
        return stored

    def remove(self, row:NDARR=None):
        if row is None:
            raise ValueError("remove requires row")

        mid = self.mid(row=row)
        rid = self.rid(row=row)
        mat_name = self.mat.name(mid=mid)

        n = self.nrows(mid=mid)
        last = n - 1

        # remove target
        self.bvh.remove(mat=mat_name, rid=rid)
        self.mdx.remove(mat=mat_name, rid=rid)

        if rid != last:
            moved = self.array[mid][last]
            moved_mid = mid
            moved_rid = last
            self.bvh.remove(mat=mat_name, rid=moved_rid)
            self.mdx.remove(mat=mat_name, rid=moved_rid)
            moved[*ROW.IDS_RID] = np.uint64(rid)
            self.array[mid][rid][:] = moved

            self.bvh.insert(row=self.array[mid][rid])
            self.mdx.insert(row=self.array[mid][rid])

        # now it is safe to invalidate
        self.array[mid][last][:] = ROW.ARRAY
        self.deln(mat=mat_name)



    # ============================================================
    # queries
    # ============================================================

    def size(self)->SIZE:
        return (self.p1[0]-self.p0[0],self.p1[1]-self.p0[1],self.p1[2]-self.p0[2])

    def volume(self, mat:str=None)->int:
        if mat is None:
            total=0
            for mid in range(MATERIALS.NUM):
                total+=self.volume(mat=self.mat.name(mid=mid))
            return total

        mid=int(self.mat.mid(name=mat))
        total=0
        n=self.nrows(mid=mid)
        for rid in range(n):
            total+=ROW.VOLUME(row=self.array[mid][rid])
        return total

    def search(self, pos:POS=None)->tuple[str,int,NDARR]:
        mat,rid,row=self.bvh.search(pos=pos)
        return (mat,rid,row)

    # ============================================================
    # split (human interface, but internal work is row-first)
    # ============================================================

    def splitrow(self, pos:POS=None, p2:POS=None, mat:str=None)->REQS:
        if pos is None or p2 is None or mat is None:
            raise ValueError("splitrow requires pos,p2,mat")

        mat0,_,hitrow=self.search(pos=pos)

        r0=ROW.P0(row=hitrow)
        r1=ROW.P1(row=hitrow)

        x0,y0,z0=r0
        x3,y3,z3=r1
        x1,y1,z1=pos
        x2,y2,z2=p2

        x1=max(x0,min(x1,x3)); x2=max(x0,min(x2,x3))
        y1=max(y0,min(y1,y3)); y2=max(y0,min(y2,y3))
        z1=max(z0,min(z1,z3)); z2=max(z0,min(z2,z3))

        xs=((x0,x1),(x1,x2),(x2,x3))
        ys=((y0,y1),(y1,y2),(y2,y3))
        zs=((z0,z1),(z1,z2),(z2,z3))

        array,arids=self.reqs(n=27)

        for i,(X0,X1) in enumerate(xs):
            for j,(Y0,Y1) in enumerate(ys):
                for k,(Z0,Z1) in enumerate(zs):
                    if (X1-X0)<=0 or (Y1-Y0)<=0 or (Z1-Z0)<=0:
                        continue

                    center=(i==1 and j==1 and k==1)
                    use_mat=mat if center else mat0

                    newrow=self.insert(p0=(X0,Y0,Z0),p1=(X1,Y1,Z1),mat=use_mat)
                    mid_new=self.mid(row=newrow)

                    array[mid_new][arids[mid_new]]=newrow
                    arids[mid_new]+=1

        self.remove(row=hitrow)
        return (array,arids)

    def split1(self, pos:POS=None, mat:str=None)->REQS:
        if pos is None or mat is None:
            raise ValueError("split1 requires pos,mat")
        p2=(pos[0]+1,pos[1]+1,pos[2]+1)
        batch,_=self.splitrow(pos=pos,p2=p2,mat=mat)
        merged,marids=self.merge(rows=batch)
        return (merged,marids)

    def split2(self, p0:POS=None, p1:POS=None, mat:str=None)->REQS:
        def intersect(a0:POS=None,a1:POS=None,b0:POS=None,b1:POS=None)->tuple[POS,POS]|None:
            q0=(max(a0[0],b0[0]),max(a0[1],b0[1]),max(a0[2],b0[2]))
            q1=(min(a1[0],b1[0]),min(a1[1],b1[1]),min(a1[2],b1[2]))
            if q0[0]>=q1[0] or q0[1]>=q1[1] or q0[2]>=q1[2]:
                return None
            return (q0,q1)

        if p0 is None or p1 is None or mat is None:
            raise ValueError("split2 requires p0,p1,mat")

        p0,p1=ROW.SORT(p0=p0,p1=p1)
        if p0[0]>=p1[0] or p0[1]>=p1[1] or p0[2]>=p1[2]:
            return self.reqs(n=0)

        acc:list[list[NDARR]]=[[] for _ in range(MATERIALS.NUM)]

        _,_,hitrow=self.search(pos=p0)
        r0=ROW.P0(row=hitrow)
        r1=ROW.P1(row=hitrow)

        hit=intersect(a0=p0,a1=p1,b0=r0,b1=r1)
        if hit is None:
            return self.reqs(n=0)

        q0,q1=hit

        batch,_=self.splitrow(pos=q0,p2=q1,mat=mat)
        merged,marids=self.merge(rows=batch)

        for mid in range(MATERIALS.NUM):
            for i in range(marids[mid]):
                acc[mid].append(merged[mid][i])

        if q1[0]<p1[0]:
            b,a=self.split2(p0=(q1[0],p0[1],p0[2]),p1=p1,mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(a[mid]):
                    acc[mid].append(b[mid][i])

        if q1[1]<p1[1]:
            b,a=self.split2(p0=(p0[0],q1[1],p0[2]),p1=(q1[0],p1[1],p1[2]),mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(a[mid]):
                    acc[mid].append(b[mid][i])

        if q1[2]<p1[2]:
            b,a=self.split2(p0=(p0[0],p0[1],q1[2]),p1=(q1[0],q1[1],p1[2]),mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(a[mid]):
                    acc[mid].append(b[mid][i])

        out_arids:dict[int,int]={mid:len(acc[mid]) for mid in range(MATERIALS.NUM)}
        n=max(out_arids.values()) if out_arids else 0
        array,arids=self.reqs(n=n)

        for mid in range(MATERIALS.NUM):
            arids[mid]=out_arids[mid]
            for i,r in enumerate(acc[mid]):
                array[mid][i]=r

        return (array,arids)

    def split(self, pos:POS=None, pos1:POS=None, mat:str=None)->REQS:
        if mat is None:
            raise ValueError("material must be specified")
        if pos is None and pos1 is None:
            raise ValueError("either pos or pos1 must be provided")

        if pos is not None and pos1 is not None:
            return self.split2(p0=pos,p1=pos1,mat=mat)
        if pos is not None:
            return self.split1(pos=pos,mat=mat)
        return self.split1(pos=pos1,mat=mat)

    # ============================================================
    # merge (row-only whenever possible)
    # ============================================================

    def merge2(self, row0:NDARR=None, row1:NDARR=None)->REQS:
        if row0 is None or row1 is None:
            return self.reqs(n=0)

        mid=self.mid(row=row0)
        if self.mid(row=row1)!=mid:
            return self.reqs(n=0)

        touch=ROW.MERGE(row0=row0,row1=row1)
        if touch==(False,False,False):
            return self.reqs(n=0)

        p0=ROW.SORT(p0=ROW.P0(row=row0),p1=ROW.P0(row=row1))[0]
        p1=ROW.SORT(p0=ROW.P1(row=row0),p1=ROW.P1(row=row1))[1]

        # remove bigger rid first (swap-safe)
        if self.rid(row=row0)>self.rid(row=row1):
            hi,lo=row0,row1
        else:
            hi,lo=row1,row0

        self.remove(row=hi)
        self.remove(row=lo)

        mat_name=self.mat.name(mid=mid)
        newrow=self.insert(p0=p0,p1=p1,mat=mat_name)

        array,arids=self.reqs(n=1)
        array[mid][0]=newrow
        arids[mid]=1
        return (array,arids)

    def mergeax(self, mat:str=None, axis:int=None)->REQS:
        if axis is None:
            raise ValueError("mergeax requires axis")
        if mat is None:
            raise ValueError("mergeax requires mat")

        mid=int(self.mat.mid(name=mat))
        start_n=self.nrows(mid=mid)
        array,arids=self.reqs(n=start_n)

        extra:list[int]=list(range(self.arids[mid]-1,-1,-1))
        seen:set[int]=set()

        while extra:
            rid=extra.pop()
            if rid<0 or rid>=self.arids[mid]:
                continue
            if rid in seen:
                continue
            seen.add(rid)

            partner=self.mdx.search(mid=mid,rid=rid,axis=axis)
            if partner is None:
                continue

            pmid,prid=partner
            if pmid!=mid or prid<0 or prid>=self.arids[mid]:
                continue

            row0=self.array[mid][rid]
            row1=self.array[mid][prid]

            created,carids=self.merge2(row0=row0,row1=row1)
            if carids[mid]>0:
                array[mid][arids[mid]]=created[mid][0]
                arids[mid]+=1

                new_rid=self.arids[mid]-1
                extra.append(new_rid)

                if rid<self.arids[mid]:
                    seen.discard(rid)
                    extra.append(rid)

        return (array,arids)

    def mergemat(self, mat:str=None)->REQS:
        if mat is None:
            raise ValueError("mergemat requires mat")

        mid=int(self.mat.mid(name=mat))
        start_n=self.nrows(mid=mid)
        array,arids=self.reqs(n=start_n)

        for ax in range(3):
            while True:
                created,carids=self.mergeax(mat=mat,axis=ax)
                if carids[mid]<=0:
                    break
                for i in range(carids[mid]):
                    array[mid][arids[mid]]=created[mid][i]
                    arids[mid]+=1

        return (array,arids)

    def mergerows(self, rows:NDARR=None)->REQS:
        if rows is None:
            return self.reqs(n=0)

        mids_present:set[int]=set()
        for mid in range(rows.shape[0]):
            for i in range(rows.shape[1]):
                if rows[mid][i][*ROW.IDS_RID]!=ROW.SENTINEL:
                    mids_present.add(mid)
                    break

        worst=0
        for mid in mids_present:
            worst+=self.nrows(mid=mid)

        array,arids=self.reqs(n=worst)

        while True:
            merged_this_round=0

            for ax in (self.mdx.AX_X,self.mdx.AX_Y,self.mdx.AX_Z):
                extra:list[tuple[int,int]]=[]
                for mid in mids_present:
                    for rid in range(self.arids[mid]-1,-1,-1):
                        extra.append((mid,rid))

                seen:set[tuple[int,int]]=set()

                while extra:
                    mid,rid=extra.pop()
                    if rid<0 or rid>=self.arids[mid]:
                        continue

                    key=(mid,rid)
                    if key in seen:
                        continue
                    seen.add(key)

                    partner=self.mdx.search(mid=mid,rid=rid,axis=ax)
                    if partner is None:
                        continue

                    pmid,prid=partner
                    if pmid!=mid or prid<0 or prid>=self.arids[mid]:
                        continue

                    row0=self.array[mid][rid]
                    row1=self.array[mid][prid]

                    created,carids=self.merge2(row0=row0,row1=row1)
                    if carids[mid]>0:
                        array[mid][arids[mid]]=created[mid][0]
                        arids[mid]+=1
                        merged_this_round+=1

                        new_rid=self.arids[mid]-1
                        extra.append((mid,new_rid))

                        seen.discard((mid,rid))
                        extra.append((mid,rid))

            if merged_this_round==0:
                break

        return (array,arids)

    def mergeall(self)->REQS:
        array,arids=self.reqs(n=self.total)
        for mat in self.mat.names():
            created,carids=self.mergemat(mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(carids[mid]):
                    array[mid][arids[mid]]=created[mid][i]
                    arids[mid]+=1
        return (array,arids)

    def merge(self, rows:NDARR=None)->REQS:
        if rows is None:
            return self.mergeall()
        return self.mergerows(rows=rows)

    def __repr__(self)->str:
        return self.__str__()

    def __str__(self)->str:
        n=self.nrows(mat="STONE")
        return f"ROWS(shape={self.shape}, nbytes={self.nbytes}, gbytes={self.gbytes:.3f} with {n} valid rows)"

#!/arc/home/txyliu/lib/mambaforge/envs/p311/bin/python
import os, sys, stat
import json
import time
import uuid
from pathlib import Path
from datetime import datetime

sys.path = list(set([
    "/arc/home/txyliu/lib/mambaforge/envs/p311/lib/python3.11/site-packages",
    "/home/txyliu/project/main/cpsc445-project/main/biocyc_run",
    "/home/txyliu/project/main/cpsc445-project/lib",
]+sys.path))

from concurrent.futures import ProcessPoolExecutor as Exe
import networkx as nx
import numpy as np

from local.caching import save, load, save_exists
from biocyc_facade.pgdb import Pgdb, Dat
from model import MNetwork, Cluster

from scipy.sparse import csr_matrix
import numpy as np
import json

from local.caching import load, save

with open("/home/txyliu/project/main/cpsc445-project/main/biocyc_run/meta_rxns.json", "r") as j:
    meta_rxns = set(json.load(j))
LEN_RXN = len(meta_rxns)

class Numerizer:
    def __init__(self, lst: list[str]=list()) -> None:
        if not isinstance(lst, list): lst = list(lst)
        self._encoding: dict[str, int] = dict((s, i) for i, s in enumerate(lst))
        self._decoding: list[str] = lst

    def Encode(self, s: str):
        if s not in self._encoding:
            self._encoding[s] = len(self._encoding)
            self._decoding.append(s)
        return self._encoding[s]
    
    def Decode(self, i: int):
        return self._decoding[i]
    
MIN_C = int(round(20000*0.1))
edges = np.array(load("dq_sorted"), dtype=np.float64)
print("loaded", edges.shape)
print(edges[:, 4].shape)
print((edges[:, 4]>=MIN_C).shape)
ss = edges[edges[:, 4]>=MIN_C]
print(ss.shape)
save("dq_ss", ss)

edges = np.array(load("gq_sorted"), dtype=np.float64)
print("loaded", edges.shape)
print(edges[:, 4].shape)
ss = edges[edges[:, 4]>=MIN_C]
print(ss.shape)
save("gq_ss", ss)

# encoding = Numerizer(meta_rxns)

# raw_dist = load("0", alt_workspace="/home/txyliu/scratch/runs/b_final_c")

# print("initializing edge list")
# edges = np.zeros(shape=(len(raw_dist), 7), dtype=np.float64) # ia ib dq gq c adq agq
# # mat = np.zeros(shape=(LEN_RXN, LEN_RXN, 3), dtype=np.float64)
# print(edges.shape)


# print("filling")
# for i, ((a, b), (dq, gq, c)) in enumerate(raw_dist.items()):
#     if i % 1024 == 0: print(f"\r{(i+1)/len(raw_dist)*100:0.3f}% ", end="")

#     ia, ib = encoding.Encode(a), encoding.Encode(b)
#     ia, ib = (ia, ib) if ia>=ib else (ib, ia)
#     edges[i] = [ia, ib, dq, gq, c, 0, 0]

# print("getting averages")
# edges[:, 5] = edges[:, 2]/edges[:, 4]
# edges[:, 6] = edges[:, 3]/edges[:, 4]

# print("sorting dq")
# edges = sorted(edges, key=lambda t: t[5])
# save("dq_sorted", edges, compression_level=7)
# print("sorting gq")
# edges = sorted(edges, key=lambda t: t[6])
# save("gq_sorted", edges, compression_level=7)

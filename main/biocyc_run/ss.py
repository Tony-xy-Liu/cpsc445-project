#!/arc/home/txyliu/lib/mambaforge/envs/p311/bin/python
import sys
sys.path = list(set([
    "/arc/home/txyliu/lib/mambaforge/envs/p311/lib/python3.11/site-packages",
]+sys.path))

import networkx as nx

sys.path = list(set([
    "/arc/home/txyliu/lib/mambaforge/envs/p311/lib/python3.11/site-packages",
    "/home/txyliu/project/main/cpsc445-project/main/biocyc_run",
    "/home/txyliu/project/main/cpsc445-project/lib",
]+sys.path))

import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor as Exe
import networkx as nx
import numpy as np
import json

from local.caching import save, load, save_exists
from biocyc_facade.pgdb import Pgdb, Dat
from model import MNetwork, Cluster

# meta = Pgdb("/home/txyliu/project/data/biocyc_pgdbs/metacyc.pgdb")
# mrxns = meta.GetDataTable(Dat.REACTIONS)

    # json.dump(list(mrxns), j)
with open("/home/txyliu/project/main/cpsc445-project/main/biocyc_run/meta_rxns.json", "r") as j:
    mrxns = set(json.load(j))

print(len(mrxns)**2)

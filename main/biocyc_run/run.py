from concurrent.futures import ProcessPoolExecutor as Exe

import os
from pathlib import Path

from local.caching import save, load
from biocyc_facade.pgdb import Pgdb, Dat
from model import MNetwork, Cluster

pgdbs_folder = Path("../../data/txyl_local/biocyc/pgdbs")

def _do(pf: Path):
    global pgdbs_folder
    pgdb = Pgdb(pgdbs_folder.joinpath(pf))
    net = MNetwork(pgdb.GetDataTable(Dat.REACTIONS))
    tree, _, _ = Cluster(net.G, force_complete=True)

    save(f"{pf}.net", net, silent=True)
    save(f"{pf}.tree", tree, silent=True)
    return pf

with Exe(max_workers=14) as exe:
    pfs = list(os.listdir(pgdbs_folder))
    for i, r in enumerate(exe.map(_do, pfs)):
        print(f"\r{i+1} of {len(pfs)} done", end="")

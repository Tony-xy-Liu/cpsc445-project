from concurrent.futures import ProcessPoolExecutor as Exe

import os
from pathlib import Path
from datetime import datetime as dt

from local.caching import save, load
from biocyc_facade.pgdb import Pgdb, Dat
from model import MNetwork, Cluster

pgdbs_folder = Path("../../data/txyl_local/biocyc/pgdbs")

def Timestamp():
    return f"{dt.now().strftime('%H:%M:%S')}>"

def _do(pf: Path):
    global pgdbs_folder
    print(f"{Timestamp()} {pf}")
    pgdb = Pgdb(pgdbs_folder.joinpath(pf))
    net = MNetwork(pgdb.GetDataTable(Dat.REACTIONS))
    tree, _, _ = Cluster(net.G, force_complete=True, min_size=1)
    pgdb._con.close()

    save(f"{pf}.net", net)
    save(f"{pf}.tree", tree)
    print(f"{Timestamp()} done {pf}")
    return pf

with Exe(max_workers=4) as exe:
    pfs = list(os.listdir(pgdbs_folder))
    pfs = pfs[:4]
    for i, r in enumerate(exe.map(_do, pfs)):
        pass

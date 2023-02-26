import os, sys
from concurrent.futures import ProcessPoolExecutor as Exe

from txyl_common.biocyc_facade.pgdb import Pgdb, Dat, Traceable

root = "../../data/txyl_local/biocyc/pgdbs"
_updated = "../../data/txyl_local/biocyc/1.3_pgdbs"

pfs = os.listdir(root)
pfs = list(enumerate(pfs))
total = len(pfs)

def do(pfs):
    max_i = 0
    for i, pf in pfs:
        new_pf = f"{_updated}/{pf}"
        if os.path.exists(new_pf): continue
        print(f"{i+1} of {total}: {pf} {' '*50}")

        _db = Pgdb(f"{root}/{pf}")
        _db.UpdateSchema(new_pf, _overwrite=False, silent=True)
        max_i = max(i, max_i)
    return max_i

sections = []
max_sect = 25
sect = []
while True:
    if len(pfs) == 0:
        if len(sect)>0: sections.append(sect)
        break
    if len(sect)>= max_sect:
        sections.append(sect)
        sect = []
    sect.append(pfs.pop(0))

for s in sections:
    with Exe(max_workers=1) as exe:
        for r in exe.map(do, [s]):
            print(f" -- completed {r}")

print('done')

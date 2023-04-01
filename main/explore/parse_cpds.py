import json
import os, sys
from concurrent.futures import ProcessPoolExecutor as Exe
from local.caching import load, save
from txyl_common.biocyc_facade.pgdb import Pgdb, Dat, Traceable

root = "../../data/txyl_local/biocyc/pgdbs"

pfs = os.listdir(root)
pfs = list(enumerate(pfs))
total = len(pfs)

def do(pfs):
    data = []
    max_i = 0
    for i, pf in pfs:
        max_i = max(i, max_i)
        print(f"{i+1} of {total}: {pf} {' '*50}", end='\r')
        try:
            db = Pgdb(f"{root}/{pf}")

            MAP = {
                "LEFT-TO-RIGHT": "default",
                "RIGHT-TO-LEFT": "default",
                "PHYSIOL-LEFT-TO-RIGHT": "physiol",
                "PHYSIOL-RIGHT-TO-LEFT": "physiol",
            }

            def get_cpds(v: dict):
                direction: str = v.get('REACTION-DIRECTION', ['unk'])[0]
                dirtype = MAP.get(direction, direction)
                lefts = set(v.get('LEFT', []))
                rights = set(v.get('RIGHT', []))

                left_o = lefts.difference(rights)
                right_o = rights.difference(lefts)
                catalysts = lefts.intersection(rights)

                rev = False
                if 'LEFT' in direction and 'RIGHT' in direction: # not reversible
                    rev = direction.index('RIGHT') < direction.index('LEFT')
                    
                if rev:
                    return right_o, left_o, catalysts, dirtype
                else:
                    return left_o, right_o, catalysts, dirtype

            redges = {}
            rxns = db.GetDataTable(Dat.REACTIONS)
            for k, v in rxns.items():
                ins, outs, cats, dirtype = get_cpds(v)
                redges[k] = (ins, outs, cats, dirtype)
            data.append(redges)

        except AssertionError:
            print(f"{pf} failed")
            continue

    return max_i, data

sections = []
max_sect = 1000
sect = []
while True:
    if len(pfs) == 0:
        if len(sect)>0: sections.append(sect)
        break
    if len(sect)>= max_sect:
        sections.append(sect)
        sect = []
    sect.append(pfs.pop(0))

for i, s in enumerate(sections):
    p = []
    jdump = f'rxn_edges_{i+1}'
    if os.path.exists(jdump): continue
    with Exe(max_workers=1) as exe:
        for r, parsed in exe.map(do, [s]):
            p = parsed
            print(f" -- completed {r} {' '*50}")
    save(jdump, p)
    
save("batches", sections)

print('done')

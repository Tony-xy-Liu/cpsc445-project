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
        print(f"{i+1} of {total}: {pf} {' '*50}", end='\r')
        db = Pgdb(f"{root}/{pf}")

        def get_ins_outs(v: dict):
            direction: str = v.get('REACTION-DIRECTION', ['unk'])[0]
            lefts = set(v.get('LEFT', []))
            rights = set(v.get('RIGHT', []))

            left_o = lefts.difference(rights)
            right_o = rights.difference(lefts)
            catalysts = lefts.intersection(rights)
            
            if 'LEFT' not in direction or 'RIGHT' not in direction: # reversible
                all = lefts.union(rights)
                return all, all, catalysts
            else:
                li = direction.index('LEFT')
                ri = direction.index('RIGHT')

                if li < ri:
                    return left_o, right_o, catalysts
                else:
                    return right_o, left_o, catalysts

        consumption, production, catalyst_use = {}, {}, {}
        def addc(d: dict, v: str):
            d[v] = d.get(v, 0)+1

        for k, v in db.GetDataTable(Dat.REACTIONS).items():
            ins, outs, cats = get_ins_outs(v)
            for lst, ref in zip([ins, outs, cats], [consumption, production, catalyst_use]):
                for mol in lst:
                    addc(ref, mol)
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

#!/arc/home/txyliu/lib/mambaforge/envs/p311/bin/python
import os, sys
from pathlib import Path
sys.path = list(set([
    "/arc/home/txyliu/lib/mambaforge/envs/p311/lib/python3.11/site-packages",
    "/home/txyliu/project/main/cpsc445-project/main/biocyc_run",
    "/home/txyliu/project/main/cpsc445-project/lib",
]+sys.path))
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor as Exe

from local.caching import load, save

def timestamp():
    now = datetime.now() 
    date_time = now.strftime("%H:%M:%S")
    return date_time

root = Path("/home/txyliu/scratch/runs/biocyc_av_tree")
fnames = list(os.listdir(root.joinpath("cache")))

nbatches = 5
batches = []
def _add_batch(b):
    batches.append(b.copy())
    b.clear()
_batch = []
for f in fnames:
    _batch.append(f)
    if len(_batch) > len(fnames)//nbatches:
        _add_batch(_batch)
if len(_batch)>0: _add_batch(_batch)

def _do(fnames: list[str], i):
    d = {}
    for j, f in enumerate(fnames):
        print(f"{timestamp()}> {i}:{j} of {len(fnames)} {f}")
        x = load(f, alt_workspace=root, silent=True)
        d.update(x)
    save(f"{i}", d, compression_level=7)

    print(f"{timestamp()}> {i} done")


for i, b in enumerate(batches):
    d = {}
    for j, f in enumerate(fnames):
        print(f"{timestamp()}> {i}:{j} of {len(fnames)} {f}")
        x = load(f, alt_workspace=root, silent=True)
        d.update(x)
    save(f"{i}", d, compression_level=7)

exit(0)

with Exe(max_workers=nbatches) as exe:
# with Exe(max_workers=nbatches) as exe:
    for r in exe.map(_do, batches, range(nbatches)):
        pass
print("done")

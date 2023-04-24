#!/arc/home/txyliu/lib/mambaforge/envs/p311/bin/python
#########################################################################################
# pbs submit array job

# calling this script with "mock" (as in ./script.py mock) will generate
# the workspaces and worker script, but not submit

# per node
NAME    = "b_final_c"
CPU     = 1
MEM     = 64
TIME    = "1:00:00"
ALLOC   = "st-shallam-1"
USER    = "txyliu"
EMAIL   = "txyliu@student.ubc.ca"
# DEPEND  = "4872574[]"
DEPEND  = False
# TEMP_VAR= "SLURM_TMPDIR" # slurm (cedar)
TEMP_VAR= "TMPDIR" # pbs (sockeye)

import os, sys, stat
import json
import time
import uuid
from pathlib import Path
from datetime import datetime
_INNER = "inner"
SCRIPT = os.path.abspath(__file__)
SCRIPT_DIR = Path("/".join(SCRIPT.split("/")[:-1]))

if not (len(sys.argv)>1 and sys.argv[1] == _INNER):
    now = datetime.now() 
    date_time = now.strftime("%Y-%m-%d-%H-%M")
    run_id = f'{uuid.uuid4().hex[:6]}'
    print("run_id:", run_id)
    log_folder = SCRIPT_DIR.joinpath(f"{NAME}.{date_time}.{run_id}")
    OUT_DIR = Path(f"/home/{USER}/scratch/runs/{NAME}")

    context = []
    # ---------------------------------------------------------------------------------
    # get data for run

    root = Path("/home/txyliu/scratch/runs/b_combine")
    fnames = list(os.listdir(root.joinpath("cache")))

    nbatches = 0.5 # 1
    def _add_batch(b):
        context.append({
            "root": str(root),
            "batch": b.copy(),
            "i": len(context),
        })
        b.clear()
    _batch = []
    for f in fnames:
        _batch.append(str(f))
        if len(_batch) > len(fnames)//nbatches:
            _add_batch(_batch)
    if len(_batch)>0: _add_batch(_batch)

    print()
    print(len(context))

    # ---------------------------------------------------------------------------------
    # prep commands & workspaces

    if len(context) == 0:
        print(f"no jobs, stopping")
        exit()

    os.makedirs(log_folder)
    os.chdir(log_folder)

    run_context_path = log_folder.joinpath("context.json")
    with open(run_context_path, "w") as j:
        json.dump(context, j, indent=4)

    # OUT_DIR = Path(f"/home/{USER}/scratch/runs/{NAME}.{run_id}")
    os.makedirs(OUT_DIR, exist_ok=True)

    pbs_bounce = log_folder.joinpath("worker.sh")
    run_cmd = f"python {SCRIPT} {_INNER} {run_context_path} {OUT_DIR} {CPU} {MEM} {TIME} {run_id}"
    with open(pbs_bounce, 'w') as s:
        s.writelines([l+"\n" for l in [
            f'PATH=/arc/home/txyliu/lib/mambaforge/envs/p311/bin/:$PATH',
            f'PYTHONPATH="{":".join(sys.path)}"',
            run_cmd,
        ]])
    os.chmod(pbs_bounce, stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO)
    time.sleep(1)

    # ---------------------------------------------------------------------------------
    # submit

    notes_file = "notes.txt"
            # -V -W "block=true" \
    arr_param = f"-J 0-{len(context)-1}" if len(context)>1 else ""
    depend_param = f"-W depend=afterok:{DEPEND}" if DEPEND else ""
    sub_cmd = f"""\
        qsub -A {ALLOC} \
            -N "{NAME}" \
            {arr_param} \
            -o {OUT_DIR.joinpath(run_id+".^array_index^")}.out \
            -e {OUT_DIR.joinpath(run_id+".^array_index^")}.err \
            -M {EMAIL} -m n \
            {depend_param} \
            -l "walltime={TIME},select=1:ncpus={CPU}:mem={MEM}gb" \
            {pbs_bounce} >> {log_folder.joinpath(notes_file)}
    """.replace("    ", "")
    with open(notes_file, "w") as log:
        log.writelines(l+"\n" for l in [
            f"name: {NAME}",
            f"id: {run_id}",
            f"array size: {len(context)}",
            f"output folder: {OUT_DIR}",
            f"submit command:",
            sub_cmd,
            "",
        ])
    if not (len(sys.argv)>1 and sys.argv[1] in ["--mock", "mock", "-m"]):
        os.chdir(OUT_DIR)
        os.system(sub_cmd)
        print("submitted")

    exit() # the outer script

#########################################################################################
# on the compute node...

_, run_context_path, _out_dir, cpus, mem, given_time, run_id = sys.argv[1:] # first is just path to this script
OUT_DIR = Path(_out_dir)
# job_i = int(os.environ['SLURM_ARRAY_TASK_ID'])
arr_var = "PBS_ARRAY_INDEX"
if arr_var in os.environ:
    job_i = int(os.environ[arr_var])
else:
    os.system(f'echo "not array, defaulting to the first context"')
    job_i = 0
with open(run_context_path) as f:
    run_context = json.load(f)
assert run_context is not None
DATA = run_context[job_i]

def print(x):
    now = datetime.now() 
    date_time = now.strftime("%H:%M:%S")
    with open(OUT_DIR.joinpath(f"{run_id}.{job_i}.log"), "a") as log:
        log.write(f"{date_time}> {x}\n")

print(f"job:{job_i} cpu:{cpus} mem:{mem} time:{given_time} ver:4")
print("-"*50)
# ---------------------------------------------------------------------------------------
# setup workspace in local scratch

salt = uuid.uuid4().hex
WS = Path(os.environ.get(TEMP_VAR, '/tmp')).joinpath(f"{NAME}-{salt}"); os.makedirs(WS)
os.chdir(WS)

# ---------------------------------------------------------------------------------------
# work

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

from local.caching import save, load, save_exists
from biocyc_facade.pgdb import Pgdb, Dat
from model import MNetwork, Cluster

root = Path(DATA["root"])
fnames = DATA["batch"]
i =  DATA["i"]

d = {}
for j, f in enumerate(fnames):
    print(f"{i}:{j} of {len(fnames)} {f} | {len(d)}")
    x = load(f, alt_workspace=root, silent=True)
    for k, (x, y, z) in x.items():
        if k not in d:
            d[k] = x, y, z
        else:
            a, b, c = d[k]
            d[k] = a+x, b+y, c+z # dq, globalq, count
save(f"{i}", d, compression_level=7, alt_workspace=OUT_DIR)

# ---------------------------------------------------------------------------------------
# done
print('echo "done"')

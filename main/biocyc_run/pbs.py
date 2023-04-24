#!/arc/home/txyliu/lib/mambaforge/envs/p311/bin/python
#########################################################################################
# pbs submit array job

# calling this script with "mock" (as in ./script.py mock) will generate
# the workspaces and worker script, but not submit

# per node
NAME    = "biocyc_clustering2"
CPU     = 4
MEM     = 32
TIME    = "2:00:00"
ALLOC   = "st-shallam-1"
USER    = "txyliu"
EMAIL   = "txyliu@student.ubc.ca"
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

    root = Path("/home/txyliu/project/data/biocyc_pgdbs")
    # root = Path("/home/txyliu/project/data/pgdb/pgdbs")
    batch = []
    def _add_batch():
        global batch
        context.append({
            "pgdbs_folder": str(root),
            "samples": batch,
        })
        batch = []
    result_path = OUT_DIR.joinpath("cache")
    for i, s in enumerate(os.listdir(root)):
        if "metacyc" in s.lower(): continue
        print(f"\r{i}", end="")
        tree = result_path.joinpath(f"{s}.tree.pkl.gz")
        net = result_path.joinpath(f"{s}.net.pkl.gz")
        if tree.exists() and net.exists():
            # print(f"{s} already done")
            continue
        batch.append(s)
        if len(batch)>=CPU*100:
            _add_batch()
    _add_batch()

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
    run_cmd = f"python {SCRIPT} {_INNER} {run_context_path} {OUT_DIR} {CPU} {MEM} {TIME}"
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
    sub_cmd = f"""\
        qsub -A {ALLOC} \
            -N "{NAME}" \
            {arr_param} \
            -o {OUT_DIR.joinpath(run_id+".^array_index^")}.out \
            -e {OUT_DIR.joinpath(run_id+".^array_index^")}.err \
            -M {EMAIL} -m n \
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

_, run_context_path, _out_dir, cpus, mem, given_time = sys.argv[1:] # first is just path to this script
OUT_DIR = Path(_out_dir)
# job_i = int(os.environ['SLURM_ARRAY_TASK_ID'])
arr_var = "PBS_ARRAY_INDEX"
if arr_var in os.environ:
    job_i = int(os.environ[arr_var])
else:
    print(f"not array, defaulting to the first context")
    job_i = 0
with open(run_context_path) as f:
    run_context = json.load(f)
assert run_context is not None
DATA = run_context[job_i]

os.system(f'date && echo "job:{job_i} cpu:{cpus} mem:{mem} time:{given_time} ver:3" && echo "{"-"*50}"')

# ---------------------------------------------------------------------------------------
# setup workspace in local scratch

salt = uuid.uuid4().hex
WS = Path(os.environ.get(TEMP_VAR, '/tmp')).joinpath(f"{NAME}-{salt}"); os.makedirs(WS)
os.chdir(WS)

# ---------------------------------------------------------------------------------------
# work

sys.path = list(set([
    "/home/txyliu/project/main/cpsc445-project/main/biocyc_run",
    "/home/txyliu/project/main/cpsc445-project/lib",
]+sys.path))

import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor as Exe

from local.caching import save, load, save_exists
from biocyc_facade.pgdb import Pgdb, Dat
from model import MNetwork, Cluster

pgdbs_folder = Path(DATA["pgdbs_folder"])
samples = DATA["samples"]

def _do(pf: Path):
    global pgdbs_folder
    pgdb_path = pgdbs_folder.joinpath(pf)
    try:

        tree_save = f"{pf}.tree"
        if save_exists(tree_save, alt_workspace=OUT_DIR):
            print(f"skipping [{pf}], completed")
            return

        pgdb = Pgdb(pgdb_path)
        print(pgdb_path)
        # print(pgdbs_folder.joinpath(pf))
        net = MNetwork(pgdb.GetDataTable(Dat.REACTIONS))
        tree, _, _ = Cluster(net.G, force_complete=True, min_size=1)

        save(f"{pf}.net", net, alt_workspace=OUT_DIR, compression_level=7)
        save(tree_save, tree, alt_workspace=OUT_DIR, compression_level=7)
    except Exception as e:
        print(f"failed {e} {pgdb_path}")
    sys.stdout.flush()
    return pf

with Exe(max_workers=CPU) as exe:
    print(len(samples))
    for i, r in enumerate(exe.map(_do, samples)):
        # print(i)
        pass

# ---------------------------------------------------------------------------------------
# done
os.system('echo "done"')

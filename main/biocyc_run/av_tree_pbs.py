#!/arc/home/txyliu/lib/mambaforge/envs/p311/bin/python
#########################################################################################
# pbs submit array job

# calling this script with "mock" (as in ./script.py mock) will generate
# the workspaces and worker script, but not submit

# per node
NAME    = "biocyc_av_tree"
CPU     = 1
MEM     = 16
TIME    = "2:10:00"
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

    trees = Path("/home/txyliu/scratch/runs/biocyc_clustering2/cache")
    root = Path("/home/txyliu/project/data/biocyc_pgdbs")
    # root = Path("/home/txyliu/project/data/pgdb/pgdbs")
    result_path = OUT_DIR.joinpath("cache")
    batch = []
    batch_num = 0
    def _add_batch():
        global batch, batch_num
        name = f"{batch_num}"
        save_name = result_path.joinpath(f"{name}.pkl.gz")
        batch_num += 1
        if save_name.exists():
            batch = []
            return
        context.append({
            "tree_folder": str(trees.joinpath("../")),
            "samples": batch,
            "save_name": name,
        })
        batch = []
    for i, s in enumerate(os.listdir(root)):
        if "metacyc" in s.lower(): continue
        print(f"\r{i}", end="")
        batch.append(s)
        if len(batch)>=CPU*101:
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
        log.write(f"{date_time}>{x}\n")

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

tree_dir = Path(DATA["tree_folder"])
net_dir = tree_dir
result_files = DATA["samples"]
save_name = DATA["save_name"]

if save_exists(save_name, alt_workspace=OUT_DIR):
    print(f"job previously completed")
    exit(0)

# meta = Pgdb("/home/txyliu/project/data/biocyc_pgdbs/metacyc.pgdb")
# mrxns = meta.GetDataTable(Dat.REACTIONS)

with open("/home/txyliu/project/main/cpsc445-project/main/biocyc_run/meta_rxns.json", "r") as j:
    mrxns = set(json.load(j))

def calc(tree, net, dists):
    # points = []
    G = nx.Graph()
    last_b = -1
    leaves = set()
    def traverse(tree, depth):
        if not isinstance(tree, tuple):
            # print(tree)
            leaf = tree[0]
            leaves.add(leaf)
            return 1, tree, leaf, f"{net.Decode(leaf)}" # leaf
        a, b, q, gq = tree
        # a, b, q = tree
        q = max(q+0.5, 0)
        gq = max(gq+0.5, 0)

        # gq  = q

        nonlocal last_b
        # global last_b
        last_b-=1
        branch = last_b

        counta, grpa, node_a, nwk_a = traverse(a, depth+1)
        countb, grpb, node_b, nwk_b = traverse(b, depth+1)

        G.add_edge(branch, node_a, w=q, g=gq)
        G.add_edge(branch, node_b, w=q, g=gq)

        # count, nodes = counta+countb, grpa+grpb
        # count = counta+countb,
        # nodes = grpa+grpb
        # points.append((depth, count, q, gq))
        # points.append((depth, count, q))
        # nwk = f"({nwk_a}:{q}, {nwk_b}:{q})"
        # nwk = ""
        # return count, nodes, branch, nwk
        return 0, None, branch, ""

    # count, nodes, branch, nwk = traverse(tree, 0)
    traverse(tree, 0)

    def _add(d, k, v, i):
        if k not in d:
            d[k] = [0, 0, 0]
        data = d[k]
        data[i] += v
        d[k] = data

    # !!!!!!!!
    ref = mrxns

    recognized_nodes = []
    for v in G:
        vn = net.Decode(v)
        if v not in leaves: continue
        if vn not in ref: continue
        recognized_nodes.append((v, vn))

    seen = set()
    for v, vn in recognized_nodes:
        paths = nx.shortest_path_length(G, source=v, weight="w")
        seen.add(v)
        for u, l in paths.items():
            if u not in leaves: continue
            if u in seen: continue
            un = net.Decode(u)
            if un not in ref: continue
            key = (vn, un) if vn < un else (un, vn)

            _add(dists, key, l, 0)
            _add(dists, key, 1, 2)

    seen = set()
    for v, vn in recognized_nodes:
        paths = nx.shortest_path_length(G, source=v, weight="g")
        seen.add(v)
        for u, l in paths.items():
            if u not in leaves: continue
            if u in seen: continue
            un = net.Decode(u)
            if un not in ref: continue
            key = (vn, un) if vn < un else (un, vn)

            _add(dists, key, l, 1)

dists = {}
# result_files = list(os.listdir(tree_dir.joinpath("cache")))
# samples = []
for i, name in enumerate(result_files):
    # print(f"\r{i+1} of {len(result_files)} | {len(dists)}", end="")
    print(f"{i+1} of {len(result_files)} | {len(dists)}")

    tree_f = f"{name}.tree"
    net_f = f"{name}.net"

    if not save_exists(tree_f, alt_workspace=net_dir):
        print(f"{tree_f} doesnt exist, skipping")
        continue
    tree = load(tree_f, alt_workspace=tree_dir, silent=True)
    net = load(net_f, alt_workspace=net_dir, silent=True)
    # try:
    # except:
    #     print(f"skipping {name}")
    #     continue
    # samples.append((net, tree))

    calc(tree, net, dists)

save(save_name, dists, alt_workspace=OUT_DIR)

# ---------------------------------------------------------------------------------------
# done
print('echo "done"')

import os, sys
sys.path = list(set([
    "/home/tony/workspace/grad/cpsc445-project/lib/local"
]+sys.path))
import random
import numpy as np
import networkx as nx
import time
from concurrent.futures import ProcessPoolExecutor as Exe
from multiprocessing import Queue
from threading import Thread

from local.caching import load, save

def estimate_av_path_len(G: nx.Graph):
    seen = set()
    l_trails = []
    while len(l_trails)<100:
        l_samples = []
        while len(l_samples)<10:
            target = None
            while len(seen) < len(G) and (target is None or target in seen):
                target = np.random.randint(0, len(G))
            l_samples.append(np.mean([l for n, l in nx.single_target_shortest_path_length(G, target)]))
        l_trails.append(np.mean(l_samples))
    return np.mean(l_trails)

def process_sample(reactions: dict):
    ccode = {}
    def encode(c):
        if c not in ccode: 
            ccode[c] = len(ccode)
        return ccode[c]

    clookup = {}
    rlookup = {}
    for i, (rxn, (ins, outs, cats, dt)) in enumerate(reactions.items()):
        cpds = {encode(c) for g in [ins, outs, cats] for c in g}
        rlookup[i] = cpds
        for ci in cpds:
            ref = clookup.get(ci, set())
            ref.add(i)
            clookup[ci] = ref

    G = nx.Graph()
    for v, rxns in clookup.items():
        for rxn in rxns:
            for u in rlookup[rxn]:
                G.add_edge(u, v)

    return (
        len(G),
        len(G.edges),
        np.sum([d for n, d in G.degree])/len(G),
        nx.cluster.average_clustering(G),
        estimate_av_path_len(G),
    )

TOTAL = 19999
GLOBAL_QUEUE = Queue()
def job(batch_num):
    sn = f"properties_{batch_num+1}"
    if os.path.exists(f"./cache/{sn}.pkl.gz"):
        GLOBAL_QUEUE.put_nowait(1000)
        return

    jdump = f'rxn_edges_{batch_num+1}'
    time.sleep(random.random()*20)
    samples = load(jdump, silent=True)
    properties = []
    # graphs = []
    # metabolites = []
    for i, s in enumerate(samples):
        GLOBAL_QUEUE.put_nowait("") # dummy
        try:
            # cc, g, m = process_sample(s)
            r = process_sample(s)
            properties.append(r)
            # graphs.append(g)
            # metabolites.append(m)
        except Exception as e:
            GLOBAL_QUEUE.put_nowait(f"\n\n{e}\nbatch: {batch_num}|i: {i}\n\n")

    save(sn, properties)
    # save(f"graphs_{batch_num+1}", graphs)
    # save(f"metabolites_{batch_num+1}", metabolites)

def report():
    i = 0
    while True:
        x = GLOBAL_QUEUE.get()
        if isinstance(x, int):
            i += x
        else:
            i += 1
        if x == "done": break
        if x != "":
            print(i, x)
        print(f"\r{i} of {TOTAL}", end="")

th = Thread(target=report, daemon=True)
th.start()
with Exe(max_workers=8) as exe:
    batch_numbers = list(range(21))
    for r in exe.map(job, batch_numbers):
        pass

GLOBAL_QUEUE.put("done")
th.join()

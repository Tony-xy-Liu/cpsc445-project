from typing import Any
import numpy as np
import networkx as nx

from biocyc_facade.pgdb import Pgdb, Dat, Traceable

# ############################################################################
# preprocessing

class MNetwork:
    def __init__(self, reactions: dict) -> None:
        ccode = {}
        def encode(c):
            if c not in ccode: 
                ccode[c] = len(ccode)
            return ccode[c]

        clookup = {}
        rlookup = {}
        for k, v in reactions.items():
            lefts = v.get("LEFT", [])
            rights = v.get("RIGHT", [])
            k = encode(k)

            cpds = set(lefts).union(rights)
            rlookup[k] = {encode(c) for c in cpds}
            for c in cpds:
                ci = encode(c)
                ref = clookup.get(ci, set())
                ref.add(k)
                clookup[ci] = ref

        G = nx.Graph()
        for v, rxns in clookup.items():
            for rxn in rxns:
                G.add_edge(v, rxn)

        for rxn, cpds in rlookup.items():
            for u in cpds:
                G.add_edge(rxn, u)

        self.G = G
        self._ccode = ccode
        revcode = ['']*len(ccode)
        for k, i in ccode.items():
            revcode[i] = k
        self._revcode = revcode

    def Decode(self, index: int):
        return self._revcode[index] if index < len(self._revcode) else None
    
    def Encode(self, cpd: str):
        return self._ccode.get(cpd)

# ############################################################################
# hierarchical divisive clustering of graphs based on modularity

# change in Q for each v in cluster if moved to other
def DeltaQ(G: nx.Graph, cluster, other):
    g_degree: Any = G.degree
    degrees_within = [g_degree[u] for u in cluster]
    degrees_out = [g_degree[u] for u in other]
    sum_in = np.sum(degrees_within)
    sum_out = np.sum(degrees_out)

    for v in cluster:
        neighbours = [u for u in G.neighbors(v)]
        if len(other) > 0 and all(u in cluster for u in neighbours): continue
        edges_within = [u for u in neighbours if u in cluster]
        edges_out = [u for u in neighbours if u not in cluster]

        vsum_in = (sum_in - g_degree[v])
        vsum_out = sum_out
        Q = (len(edges_out) - len(edges_within)) / len(G.edges)
        Q -= g_degree[v] * (vsum_out - vsum_in) / (2 * len(G.edges)**2)

        yield Q, v

def ToGive(G: nx.Graph, cluster: set[int], other: set[int]):
    if len(cluster)==0: return [], []
    to_give = sorted(DeltaQ(G, cluster, other), key=lambda t: t[0], reverse=True)
    if len(cluster) == len(G):
        cut = 1
        force = True
    else:
        cut = max(1, len(G)//100)
        # cut = 1
        force = False 

    qs, vs = [], []
    for q, v in to_give:
        if len(qs) >= cut: break
        if not force and q <= 0: continue
        qs.append(q)
        vs.append(v)
    return qs, vs

def Partition(G: nx.Graph):
    if len(G.edges) == 0: return None

    cluster = {v for v in G.nodes}
    other = set()

    i = 0
    delta_q = 0
    _break = False
    while not _break:
        qs, to_give = ToGive(G, cluster, other)
        if len(to_give) == 0: break
        if len(to_give) >= len(cluster):
            cut = len(cluster)-1
            qs = qs[:cut]
            to_give = to_give[:cut]
            _break = True
        delta_q += np.sum(qs)
        cluster = cluster.difference(to_give)
        other = other.union(to_give)
        i += 1
    # print(f"iterations: {i}, deltaQ: {delta_q}, {len(cluster)}, {len(other)}")
    if len(other) == 0: return None

    def _partition(cluster: set[int]):
        g = nx.Graph()
        g.add_nodes_from(cluster)
        for v, u in G.edges:
            if v in cluster and u in cluster:
                g.add_edge(v, u)
        return g

    return _partition(cluster), _partition(other), delta_q

def Cluster(G: nx.Graph, force_complete=True, min_size=1):
    _original = G
    clusters = [{v for v in G.nodes}]
    current_modularity = nx.algorithms.community.modularity(G, clusters)
    def _is_same(a: set, b: set):
        return next(iter(a)) in b
    
    def _cluster(G: nx.Graph, depth: int):
        leaf = [v for v in G.nodes]
        if len(leaf) <= max(1, min_size): return leaf
        part = Partition(G)
        if part is None: return leaf

        a, b, dq = part
        ab = {v for v in G.nodes}
        cluster_a = {v for v in a}
        cluster_b = {v for v in b}
        if len(cluster_a) > len(cluster_b):
            inplace, new = cluster_a, cluster_b
        else:
            inplace, new = cluster_b, cluster_a

        nonlocal clusters, current_modularity
        snapshot = []
        complete = True
        for c in clusters:
            if len(c) >1: complete = False
            if  _is_same(c, ab): 
                snapshot.append(inplace)
            else:
                snapshot.append(c)
        snapshot.append(new)
        new_mod = nx.algorithms.community.modularity(_original, snapshot)
        if not force_complete and new_mod < current_modularity: return leaf

        delta_q_global = new_mod - current_modularity
        current_modularity = new_mod
        clusters = snapshot

        return _cluster(a, depth+1), _cluster(b, depth+1), dq, delta_q_global
    
    return _cluster(G, 0), clusters, current_modularity

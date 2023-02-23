import os
import pickle
import gzip
from typing import Callable, TypeVar

############################## pickling ##############################
EXECUTION_DIR = os.getcwd()
WORKSPACE_ROOT = "/".join(os.path.realpath(__file__).split('/')[:-3])
CACHE = f'{EXECUTION_DIR}/cache'

_force_regenerate = False
def set_force_regenerate(b):
    global _force_regenerate
    _force_regenerate = b

def _get_paths(fname: str, alt=None):
    if isinstance(alt, str) and alt[-1] == '/': alt = alt[:-1]
    cache = CACHE if alt is None else f'{alt}/cache'
    fpath = f'{cache}/{fname}'
    return fpath, cache

def _ext_to_fpaths(fpath: str, compression=False):
    EXT = '.pkl.gz' if compression else '.pkl'
    fpath = fpath.replace(EXT, '')
    fpath += EXT
    fpath_str = fpath.replace(WORKSPACE_ROOT, "{WORKSPACE}") # for logging
    return fpath, fpath_str

def save(name, x, alt_workspace=None, compression_level=1):
    fpath_no_ext, cache = _get_paths(name, alt_workspace)
    if not os.path.isdir(cache): os.system(f'mkdir {cache}')

    fpath, fpath_str = _ext_to_fpaths(fpath_no_ext, compression=compression_level>0)

    cmsg = 'compressing & ' if compression_level > 0 else ''
    print(f'{cmsg}caching data to [{fpath_str}]')

    if compression_level == 0:
        with open(fpath, 'wb') as f:
            pickle.dump(x, f, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        with gzip.open(fpath, "wb", compresslevel=compression_level) as f:
            pickle.dump(x, f, protocol=pickle.HIGHEST_PROTOCOL)


def load(name: str, alt_workspace=None):
    fpath_no_ext, cache = _get_paths(name, alt_workspace)

    for c in [False, True]:
        fpath, fpath_str = _ext_to_fpaths(fpath_no_ext, compression=c)
        if not os.path.isfile(fpath): continue

        dcomp_msg = '& decompressing ' if c else ''
        print(f'recovering {dcomp_msg}cached data from [{fpath_str}]')
        with gzip.open(fpath, "rb") if c else open(fpath, "rb") as f:
            return pickle.load(f)

    fpath, fpath_str = _ext_to_fpaths(fpath_no_ext)
    raise FileNotFoundError(f"{fpath_str} doesn't exist, nor can a compressed cache be found")

def cache(fname, regenerate, force_regenerate=None, compression_level=1):
    if force_regenerate is None: force_regenerate = _force_regenerate
    fpath_no_ext, cache = _get_paths(fname)
    fpath, fpath_str = _ext_to_fpaths(fpath_no_ext, compression=compression_level>0)

    if not force_regenerate and os.path.isfile(fpath):
        return load(fname)
    else:
        x = regenerate()
        save(fname, x, compression_level=compression_level)
        return x

############################## fn decorator ##############################

T = TypeVar('T')
def cache_fn_result(loader: Callable[..., T]) -> Callable[[], T]:
    data = None
    def getter(*args, **kargs):
        nonlocal data
        if data is None:
            data = loader(*args, **kargs)
        return data
    return getter

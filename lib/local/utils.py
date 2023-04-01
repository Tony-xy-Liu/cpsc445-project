from __future__ import annotations
import os
import time
import random
import sqlite3
import json
from pathlib import Path

from caching import CACHE


def current_time_millis():
    return round(time.time() * 1000)

class FileSyncedDictionary:
    DEFAULT_COMMS = "comms"
    def __init__(self, workspace: Path=CACHE, file_name: str|None=None, timeout: float=3) -> None:
        self._timeout = timeout
        if file_name is None: file_name = self.DEFAULT_COMMS
        self._lock_file = workspace.joinpath(file_name)
        self._data_file = workspace.joinpath(f"{file_name}.json")

        with FileLock(self._lock_file, timeout=self._timeout):
            if not os.path.exists(self._data_file):
                with open(self._data_file, 'w') as f:
                    json.dump({}, f)

        self._lock: FileLock|None = None
        self._data: dict = {}
        self._original_data: dict = {}

    def Update(self, data: dict):
        self._data = data

    def Original(self):
        return self._original_data.copy()

    def acquire(self):
        data = self._data
        if self._lock is None:
            self._lock = FileLock(self._lock_file, timeout=self._timeout)
            self._lock.acquire()
            if os.path.exists(self._data_file):
                with open(self._data_file) as j:
                    try:
                        data: dict = json.load(j)
                    except json.JSONDecodeError:
                        data = {}
        self._data = data
        self._original_data = data
        return self
            
    def release(self):
        if self._lock is not None:
            l = self._lock
            self._lock = None
            with open(self._data_file, 'w') as j:
                json.dump(self._data, j, indent=4)
            l.release()

    def __enter__(self):
        return self.acquire()
 
    def __exit__(self, type, value, traceback):
        return self.release()
 
    def __del__(self):
        self.release()

class FileLockException(Exception):
    pass
 
class FileLock(object):
    """ A file locking mechanism that has context-manager support so 
        you can use it in a with statement. This should be relatively cross
        compatible as it doesn't rely on msvcrt or fcntl for the locking.
    """
 
    def __init__(self, file_name, timeout:float=1):
        """ Prepare the file locker. Specify the file to lock and optionally
            the maximum timeout and the delay between each attempt to lock.
        """
        self.lockfile = os.path.join(os.getcwd(), "%s.lock" % file_name)
        self.file_name = file_name
        self.timeout = timeout
        self.file_handle = None
 
 
    def acquire(self):
        """ Acquire the lock, if possible. If the lock is in use, it check again
            every `wait` seconds. It does this until it either gets the lock or
            exceeds `timeout` number of seconds, in which case it throws 
            an exception.
        """
        start_time = time.time()
        max_delay = self.timeout
        base_delay = 0.1
        delay_range = 0.5
        while True:
            try:
                # self.fd = os.open(self.lockfile, os.O_CREAT|os.O_DIRECT|os.O_RDWR)
                con = sqlite3.connect(self.lockfile, timeout=self.timeout)
                cur = con.cursor()
                cur.execute(f"create table if not exists x (id int primary key)")
                cur.execute(f"delete from x where true")
                self.file_handle = con
                break;
            except sqlite3.OperationalError as e:
                if self.timeout is None:
                    raise FileLockException("Could not acquire lock on {}".format(self.file_name))
                if (time.time() - start_time) >= self.timeout:
                    raise FileLockException("Timeout occured.")
                time.sleep((base_delay + delay_range*random.random()))
                # time.sleep(base_delay)
            delay_range = min(max_delay, 0.5 + 1.5*base_delay)
#        self.is_locked = True
 
 
    def release(self):
        """ Get rid of the lock by deleting the lockfile. 
            When working in a `with` statement, this gets automatically 
            called at the end.
        """
        if self.file_handle is not None:
            self.file_handle.close()
            self.file_handle = None
 
 
    def __enter__(self):
        """ Activated when used in the with statement. 
            Should automatically acquire a lock to be used in the with block.
        """
        if self.file_handle is None:
            self.acquire()
        return self
 
 
    def __exit__(self, type, value, traceback):
        """ Activated at the end of the with statement.
            It automatically releases the lock if it isn't locked.
        """
        self.release()
 
 
    def __del__(self):
        """ Make sure that the FileLock instance doesn't leave a lockfile
            lying around.
        """
        self.release()
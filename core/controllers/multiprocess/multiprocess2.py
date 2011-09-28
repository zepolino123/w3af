'''
multiprocess2.py

Copyright 2011 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
'''
__all__ = [
    'get_plugin_manager', 'TimeLimitExpired',
    'TerminatedWork', 'MNGR_TYPE_GREP'
    ]

from Queue import Empty
import itertools
import multiprocessing
import sys
import threading
import traceback


# Amount of available CPUs
try:
    CPU_COUNT = multiprocessing.cpu_count()
except NotImplementedError:
    CPU_COUNT = 2
# Constants representing the state of a pool
RUN = 0
TERMINATE = 1

# Global counter
job_counter = itertools.count()

MNGR_TYPE_GREP = 'MNGR_TYPE_GREP'
MNGR_TYPE_AUDIT = 'MNGR_TYPE_AUDIT'

_mngrs = {MNGR_TYPE_GREP: None}

def get_plugin_manager(mngr_type, plugins):
    
    if mngr_type not in _mngrs:
        raise ValueError, "Invalid Manager Type: '%s'" % mngr_type
    
    mngr = _mngrs[mngr_type]
    if mngr is None:
        d = {MNGR_TYPE_GREP: GrepMngr}
        _mngrs[mngr_type] = mngr = d[mngr_type](plugins)

    return mngr


class TimeLimitExpired(Exception):
    '''
    Exception raised when time limit expires.
    '''
    pass

class TerminatedWork(Exception):
    '''
    Raised when an action is called on a `terminated` Manager.
    '''
    pass

class Failure(object):
    
    def __init__(self, exc_info):
        self.exc_type, self.exc_val, tb = exc_info
        self.exc_tback = traceback.format_exc(exc_info)


class PluginMngr(object):
    
    def __init__(self, plugins):
        self._state = RUN
        self._plugins = plugins        
    
    def work(self, timeout):
        raise NotImplementedError
    
    def assert_is_not_done(self):
        if self._state != RUN:
            raise TerminatedWork
    
    def terminate(self):
        raise NotImplementedError


class GrepMngr(PluginMngr):
    
    def __init__(self, plugins):
        PluginMngr.__init__(self, plugins)
        self._cache = {}
        Queue = multiprocessing.Queue
        # Create and start grep-worker processes
        self._workers = []
        self._length = len(plugins)
        chunksize, extra = divmod(self._length, CPU_COUNT)
        if extra:
            chunksize += 1
        
        for i in xrange(CPU_COUNT):
            
            start = i * chunksize
            _plugins = plugins[start: start+chunksize]
            
            if _plugins:
                worker = GrepWorker(_plugins, Queue(), Queue())
                self._workers.append(worker)
                worker.start()
            else:
                break

        self._result_handler = threading.Thread(
            target=GrepMngr._handle_results,
            args=(self._workers, self._cache)
            )
        self._result_handler.daemon = True
        self._result_handler._state = RUN
        self._result_handler.start()
    
    def work(self, args=(), timeout=None):
        
        self.assert_is_not_done()

        result = Result(cache=self._cache, length=self._length, callback=None)
        
        for worker in self._workers:
            taskq = worker.task_queue
            taskq.put((result._job_id, args))
    
        res_list = result.get(timeout)
        for res_ele in res_list:
            if isinstance(res_ele, Failure):
                exc = res_ele.exc_type(res_ele.exc_val)
                setattr(exc, 'traceback', res_ele.exc_tback)
                raise exc
        
        return res_list
    
    def terminate(self):
        if self._state != TERMINATE:
            
            self._state = TERMINATE
            self._result_handler._state = TERMINATE
            
            for worker in self._workers:
                worker.task_queue.put(None)
                worker.terminate()
        
    
    @staticmethod
    def _handle_results(workers, cache):
        thread = threading.current_thread()
        
        while True:
            if thread._state == TERMINATE:
                break
            for w in workers:
                try:
                    jobid, res = w.result_queue.get(0.1)
                except Empty:
                    pass
                else:
                    try:
                        cache[jobid].set_result(res)
                    except KeyError:
                        pass


class Worker(multiprocessing.Process):
    
    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.daemon = True
    
    def run(self):
        raise NotImplementedError


class GrepWorker(Worker):
    
    def __init__(self, plugins, task_queue, result_queue):
        Worker.__init__(self, task_queue, result_queue)
        self._plugins = plugins
        self._shutdown = threading.Event()
    
    def run(self):
        while not self._shutdown.is_set():
            jobid = None
            
            try:
                jobid, args = self.task_queue.get()
                
                if args is None:
                    # 'Poison pill' means shutdown.
                    break
                
                res = []
                for p in self._plugins:
                    try:
                        value = p.grep(*args)
                    except KeyboardInterrupt:
                        raise
                    except Exception:
                        value = Failure(sys.exc_info())
                    
                    res.append(value or [])
                
                self.result_queue.put((jobid, res))
            
            except KeyboardInterrupt:
                self._shutdown.set()
                
                if not jobid:
                    jobid = self.task_queue.get()[0]
                self.result_queue.put(
                                    (jobid, [Failure(sys.exc_info())])
                                    )


class Result(object):
    
    def __init__(self, cache, length, callback):
        self._cache = cache
        self._length = length
        self._value = []
        self._callback = callback
        self._job_id = job_counter.next()
        cache[self._job_id] = self
        self._cond = threading.Condition(threading.Lock())
        self._is_ready = False
    
    def get(self, timeout):
        self._wait(timeout)
        if not self._is_ready:
            raise TimeLimitExpired
        return self._value
    
    def _wait(self, timeout):
        self._cond.acquire()
        try:
            if not self._is_ready:
                self._cond.wait(timeout)
        finally:
            self._cond.release()
    
    def set_result(self, res):
                
        self._value.extend(res)
        
        if len(self._value) == self._length:
            if self._callback:
                self._callback(self._value)
        
            self._cond.acquire()
            try:
                self._is_ready = True
                self._cond.notify()
            finally:
                self._cond.release()
            
            del self._cache[self._job_id]


if __name__ == '__main__':
    
    class MyPlugin(object):
        
        def __init__(self, name):
            self.name = name
            
        def grep(self, *args):
            print "Plugin '%s' is grepping on %s" % (self.name, args)
            import time, random
            time.sleep(5)
            return [random.randint(0, 100)]
        
        def __str__(self):
            return "<Plugin %s>" % self.name
        __repr__ = __str__
    
    plugins = (
       MyPlugin("AAA"), MyPlugin("BBB"), MyPlugin("CCC"),
       MyPlugin("DDD"), MyPlugin("EEE"), MyPlugin("FFF"),
       MyPlugin("GGG"), MyPlugin("HHH"), MyPlugin("III"),
       )
    grep_mngr = get_plugin_manager(MNGR_TYPE_GREP, plugins)
    res = grep_mngr.work(args=("aaaaaaa", "bbbbbbbb"), timeout=30)
    print 'RESULT:::::::', res
    
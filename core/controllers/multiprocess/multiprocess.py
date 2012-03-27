'''
multiprocess.py

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
#from collections import deque
from Queue import Empty
import itertools
import functools
import multiprocessing
import sys
import threading
import traceback
import types

__all__ = [
    'get_plugin_manager', 'restart_manager', 'TimeLimitExpired',
    'TerminatedWork', 'MNGR_TYPE_GREP'
    ]

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

MNGR_TYPE_GREP, MNGR_TYPE_AUDIT = 'MNGR_TY_GREP MNGR_TY_AUDIT'.split()

_mngrs = {MNGR_TYPE_GREP: None}
_lock = threading.Lock()

def get_plugin_manager(mngr_type, plugins=[]):
    with _lock:
        try:
            mngr = _mngrs[mngr_type]
        except KeyError:
            raise ValueError, "Invalid Manager Type: '%s'" % mngr_type
        if mngr is None:
            d = {MNGR_TYPE_GREP: GrepMngr}
            _mngrs[mngr_type] = mngr = d[mngr_type](plugins)
    return mngr

## TODO: Function `restart_manager` should be refactored into a new
## and more used GrepManager version. This manager should encapsulate
## the whole logic of dealing with everything related to the grep plugins.
## Also, see if this idea may be extended to the remaining plugin types.
def restart_manager(mngr_type):
    with _lock:
        try:
            mngr = _mngrs[mngr_type]
        except KeyError:
            raise ValueError, "Invalid Manager Type: '%s'" % mngr_type
        if mngr:
            mngr.terminate()
            try:
                _mngrs[mngr_type] = None
            except KeyError:
                pass
        
    
class TimeLimitExpired(Exception):
    '''
    Exception raised when time limit expires.
    '''
    pass


class TerminatedWork(Exception):
    '''
    Raised when an action is called on a `TERMINATEd` Manager.
    '''
    pass


class Failure(object):
    
    def __init__(self, exc_obj):
        self.exc_obj = exc_obj
        exc_obj._traceback_ = traceback.format_exc(sys.exc_info())


class PluginMngr(object):
    
    def __init__(self, plugins):
        self._state = RUN
        self._plugins = plugins        
    
    def work(self, timeout):
        raise NotImplementedError
    
    def assert_is_not_terminated(self):
#        print('==STATE=%s, %s: %s' % 
#                ('RUN' if self._state == RUN else 'TERMINATED',
#                 multiprocessing.current_process().name,
#                 threading.current_thread().name)
#                )
        if self._state != RUN:
            raise TerminatedWork
    
    def terminate(self):
        raise NotImplementedError


class GrepMngr(PluginMngr):
    
    def __init__(self, plugins):
        PluginMngr.__init__(self, plugins)
        self._cache = {}
        self._global_repl = {}
        Queue = multiprocessing.queues.SimpleQueue
        # Create and start grep-worker processes
        self._workers = []
        chunksize, extra = divmod(len(plugins), CPU_COUNT)
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
    
    def work(self, action, args=(), timeout=None):
        
        self.assert_is_not_terminated()
        
        from core.data.kb.knowledgeBase import kb
        from core.data.parsers.dpCache import dp_cache
        
        if not kb.is_active():
            kb._start_manager()
        
        if not dp_cache.is_active():
            dp_cache._start_manager()
        
        self._global_repl['kb'] = kb()
        self._global_repl['dp_cache'] = dp_cache()
        
        result = Result(
                    cache=self._cache,
                    length=len(self._workers),
                    )
        
        for worker in self._workers:
            taskq = worker.task_queue
            taskq.put(((action, args), self._global_repl))
        
        #print 'working... %s vs %s' % (self._workers[0].task_queue.qsize(), self._workers[0].result_queue.qsize())
        res_list = result.get(timeout)
        
        for res_ele in res_list:
            if isinstance(res_ele, Failure):
                print '''
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
%s
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
''' % res_ele.exc_obj._traceback_
                raise res_ele.exc_obj
        return res_list
    
    def terminate(self):
        
        print '!!!!!! CALLED TERMINATE() !!!!!!!!!!!!!'
        
        if self._state != TERMINATE:
            
            self._state = TERMINATE
            self._result_handler._state = TERMINATE
            
            for worker in self._workers:
                worker.task_queue.put(None)
                worker.terminate()
    
    @staticmethod
    def _handle_results(workers, cache):
        
        thread = threading.current_thread()
#        wait_to_interrupt = 0
        
        while True:
            if thread._state == TERMINATE:
                break
            for w in workers:
                try:
                    jobid, res = w.result_queue.get()
                except Empty:
                    pass
                else:
                    
#                    if isinstance(res, KeyboardInterrupt):
#                        
#                        if not wait_to_interrupt:
#                            jobs = cache.keys()
#                            for idx, jobid in enumerate(jobs):
#                                res = [] if idx else res
#                                print '||||||||||||||||||||||||||||||| Killing %s' % jobid
#                                cache.mark_as_done(
#                                           jobid, res=res, isdone=True
#                                           )
#                            wait_to_interrupt = (idx+1) * len(workers) - 1
#                            print "<<<<WAIT TO INTERRUPT %s>>>>" % wait_to_interrupt
#                        else:
#                            wait_to_interrupt -= 1
#                            print "<<<<WAIT TO INTERRUPT %s>>>>" % wait_to_interrupt
#                    else:
#                        cache.mark_as_done(jobid, res)
                    print 'Got result from', jobid, type(res)
                    try:
                        cache[jobid].set_result(res)
                    except KeyError:
                        print '+++++++++++++++ KEYERROR %s' % jobid
                        print '[[All KEYS = %s]]' % cache.keys()
                        #pass


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
        self._actions_cache = {}

    def run(self):
        jobid = -1
        while True:
            try:
                jobid += 1
                action_args, globalsrepl = self.task_queue.get()
                if action_args is None:
                    # 'Poison pill' means shutdown.
                    break
                
                res = []
                for p in self._plugins:
                    try:
                        action, args = action_args
                        value = \
                            self._tweaked_action(p, action, globalsrepl)(*args)
                    except Exception, ex:
                        value = Failure(ex)
                    res.append(value or [])
                
                self.result_queue.put((jobid, res))
                print 'Put Result... jobid', jobid
            
            except KeyboardInterrupt, ki:
                print 'Got KeyboardInterrupt'
                self.result_queue.put((jobid, ki))
                print 'Put KeyboardInterrupt... jobid', jobid
            except (IOError, EOFError):
                #print '//////// (%s, %%s)' % (jobid)#, self.result_queue.qsize())
                #self.task_queue.put('aaa')
                #print '"""""""""""""""""""""""""" %s' % (self.task_queue.get())
                #raise
                self.result_queue.put((jobid, KeyboardInterrupt()))
                #print '='*80
                #traceback.print_exc()
                #print '='*80
                print 'Put KeyboardInterrupt (on IOError-EOFError)... jobid', jobid
                
    def _tweaked_action(self, plugin, action, globalsrepl):
        
        def partialaction():
            func = getattr(plugin, action).im_func
            _globals = dict(func.func_globals)
            _globals.update(globalsrepl)
            func = types.FunctionType(func.func_code, _globals)
            return functools.partial(func, plugin)
        
        key = (plugin.name, action)
        taction = self._actions_cache.get(key, None)
        #if taction is None:
        if True:
            taction = partialaction()
            self._actions_cache[key] = taction
        return taction


class Result(object):
    
    _watched = set()
    
    def __init__(self, cache, length):
        self._cache = cache
        self._length = length
        self._value = []
        self._job_id = job_counter.next()
        self._cache[self._job_id] = self
        self._cond = threading.Condition(threading.Lock())
        self._is_ready = False
        self._quit_err = False
    
    def get(self, timeout):
        self._wait(timeout)
        if self._quit_err:
            raise self._quit_err
        if not self._is_ready:
            print '^^^^^^^^TIMEOUT in %s' % self._job_id
            raise TimeLimitExpired
        return list(itertools.chain(*self._value))
    
    def _wait(self, timeout):
        self._cond.acquire()
        try:
            if not self._is_ready:
                self._cond.wait(timeout)
        finally:
            self._cond.release()
    
    def set_result(self, res, isdone=False):
        print '================ %s not in %s === %s' % (self._job_id, Result._watched, type(res))
        if isinstance(res, KeyboardInterrupt):
            if self._job_id not in Result._watched:
                Result._watched.update(self._cache.keys())
                quit = True
            else:
                self._value.append([])
        else:
            quit = False
            self._value.append(res)
        
        if quit or isdone or len(self._value) == self._length:
            self._cond.acquire()
            try:
                if quit:
                    print '*'*80
                    print type(res)
                    print '*'*80
                    self._quit_err = res
                self._is_ready = True
                self._cond.notify()
            finally:
                self._cond.release()
            print '************* DELETING %s' % self._job_id
            del self._cache[self._job_id]


class Cache(object):
    
    def __init__(self):
        self._lock = multiprocessing.RLock()
        self._dict = {}
    
    def mark_as_done(self, jobid, res, isdone=False):
        with self._lock:
            try:
                self._dict[jobid].set_result(res, isdone=isdone)
            except KeyError:
                print 'KeyError: %s' % jobid
    
    def __setitem__(self, k, v):
        with self._lock:
            self._dict[k] = v
            
    def __delitem__(self, k):
        with self._lock:
            del self._dict[k]
    
    def keys(self):
        with self._lock:
            return self._dict.keys()

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
    
__all__ = ['get_plugin_manager']

from itertools import chain
import multiprocessing


CPU_COUNT = multiprocessing.cpu_count()

def get_plugin_manager(plugintype, plugins):
    global grep_plugins
    
    if not grep_plugins:
        if callable(plugins):
            plugins = plugins 
        grep_plugins.extend(plugins)
    
    return grep_mngr
    '''
    @param plugintype: A string indicating de plugin type. Valid values 
        BasePluginManager.PLUGIN_TYPE_XXX
    @param plugins: Either a list of plugin instances or a plugin factory
        function
    '''
    
    """
    global _all_plugins
    try:
        pmngr = _all_plugins[plugintype][0]
    except KeyError:
        raise ValueError, "Invalid plugin type '%s'." % plugintype
    else:
        if not pmngr:
            if callable(plugins):
                plugins = plugins()            
            _all_plugins[plugintype][1].extend(plugins)
            
            # Create the plugin manager instance
            class_mapping = {
                BasePluginManager.PLUGIN_TYPE_GREP: GrepManager
            }
            _all_plugins[plugintype][0] = pmngr = class_mapping[plugintype]()
                        
    return pmngr
    """

class BasePluginManager(object):
    
    PLUGIN_TYPE_GREP = 'PLUGIN_TYPE_GREP'
    PLUGIN_TYPE_AUDIT = 'PLUGIN_TYPE_AUDIT'
    
    # To be redefined by subclasses
    plugin_type = None
    
    def work(self, args=()):
        raise NotImplementedError


class GrepManager(BasePluginManager):
    
    plugin_type = BasePluginManager.PLUGIN_TYPE_GREP
    
    def __init__(self):
        self._taskmngr = TaskManager(GrepManager._do_grep)
    
    def work(self, args=()):
#        gplugins = _all_plugins[self.plugin_type]
#        gplugins[1], 
        res = self._taskmngr.start_work(
#                                                plugins=gplugins[1],
                                                plugins=grep_plugins,
                                                workargs=args
                                            )
        return res
    
    @staticmethod
    def _do_grep(args):
        '''
        Worker method
        '''        
        plugins, sliceobj, req, resp = args
        res = []
        print '*******************', plugins[sliceobj]
        for idx, plugin in enumerate(plugins[sliceobj]):
            print '>>>>>>>>>>>>>>> calling!!!'
            res.extend(plugin.grep(req, resp) or [])
            ## IMPORTANT! Updating values through proxy object ##
            print '############### PLUGIN-TYPE', plugin.getName()
            
            try:
                plugin._already_inspected = plugin._already_inspected
                plugins[idx] = plugin
            except AttributeError:
                pass
            except Exception, ex:
                print "=" * 80
                print ex
                print "=" * 80
                raise
                
        return res

# Make worker method available at module level. Needed by
# multiprocessing internal operation
_do_grep = GrepManager._do_grep


_all_plugins = {
    BasePluginManager.PLUGIN_TYPE_GREP: [None, []]
    }


class TaskManager(object):
    
    def __init__(self, worker_func):
        self._worker_func = worker_func
        self._pool = ProcessPool()
    
    def start_work(self, plugins, workargs=()):
        '''
        Perform works in different processes.
        '''
        def build_slices():
            amt = len(plugins)
            step = (amt // CPU_COUNT) or 1
            for i in range(0, amt, step):
                yield slice(i, i + step)
        
        
##        plugins = _plugin_server.list(plugins)
        
        res = self._pool.map(
                    self._worker_func,
                    (tuple(chain((plugins, slc), workargs)) 
                                            for slc in build_slices())
                )
##        return plugins, chain(res)
        return chain(res)


class ProcessPool(object):
    '''
    Wrapper for multiprocessing.Pool object
    '''
    _pool = None
    
    def __init__(self, processes=None):
        self._processes = processes
    
    def __getattr__(self, name):
        
        if ProcessPool._pool is None:
            ProcessPool._pool = multiprocessing.Pool(
                                    processes=self._processes or CPU_COUNT
                                    )
        return getattr(ProcessPool._pool, name)

# Create the 'Plugin Manager' server process
_plugin_server = multiprocessing.Manager()
grep_plugins = _plugin_server.list()
grep_mngr = GrepManager()
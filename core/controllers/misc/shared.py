'''
shared.py

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

from multiprocessing.managers import SyncManager

__all__ = ['Shared']

class SharedSyncManager(object):
    '''
    A multiprocessing's SyncManager wrapper
    '''
    
    def __init__(self):
        self._registry = {}
    
    def register(self, typeid, callable, exposed=()):
        self._registry[typeid] = (callable, exposed)
    
    def start(self):
        # First register the objects
        for typeid, callable_tuple in self._registry.items():
            SyncManager.register(
                        typeid, callable_tuple[0],
                        exposed=callable_tuple[1]
                        )
        
        # Then create the instance and start the process!
        for typeid in self._registry:
            newmngr = SyncManager()
            newmngr.start()
            print 'saving...', getattr(newmngr, typeid)
            self._registry[typeid] = getattr(newmngr, typeid)()
    
    def __getattr__(self, name):
        return getattr(
                object.__getattribute__(self, '_registry'), name
                )


class Shared(object):
    
    _server = SharedSyncManager()
    
    def __init__(self, sharedinst, exposed=()):
        self._id_str = str(id(self))
        callable = lambda: sharedinst
        Shared._server.register(self._id_str, callable, exposed)
    
    def __getattr__(self, name):
        id_str = object.__getattribute__(self, '_id_str')
        proxy = Shared._server._registry[id_str]
        print '=====proxy', proxy, type(proxy)
        return getattr(proxy[0](), name)
    
    @classmethod
    def start_sharing(cls):
        Shared._server.start()
    
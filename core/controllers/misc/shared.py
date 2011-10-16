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
        self.registry = {}
        self._sync_mngr = None
    
    def register(self, typeid, callabletype, exposed=()):
        assert self._sync_mngr is None, \
                                "Sharing process has already been started"
        self.registry[typeid] = (callabletype, exposed)
    
    def start(self):
        assert self._sync_mngr is None, \
                        "Sharing process has already been started"
        # First register the objects
        for typeid, callable_tuple in self.registry.items():
            SyncManager.register(
                        typeid, callable_tuple[0],
                        exposed=callable_tuple[1]
                        )
        # Start the sharing process
        mngr = SyncManager()
        mngr.start()
        # Finally make references to proxy builders methods
        for typeid in self.registry:
            self.registry[typeid] = getattr(mngr, typeid)


class Shared(object):
    
    _server = SharedSyncManager()
    
    def __init__(self, shared, exposed=()):
        self._id_str = str(id(self))
        _shared = shared
        if not callable(shared):
            _shared = lambda: shared
        Shared._server.register(self._id_str, _shared, exposed)
    
    def __getattr__(self, name):
        id_str = object.__getattribute__(self, '_id_str')
        getproxy = Shared._server.registry[id_str]
        return getattr(getproxy(), name)
    
    def __call__(self, *args):
        id_str = object.__getattribute__(self, '_id_str')
        getproxy = Shared._server.registry[id_str]
        return getproxy(*args)
    
    @classmethod
    def start_sharing(cls):
        Shared._server.start()
    
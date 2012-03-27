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
from multiprocessing.managers import BaseManager

__all__ = ['Shared']


class Shared(object):
    
    class _Manager(BaseManager):
            def is_active(self):
                return self._process.is_alive()
    
    def __init__(self, shared, exposed=()):
        self._shared = shared if callable(shared) else lambda: shared
        self._name = str(id(self))
        self._Manager.register(self._name, self._shared, exposed=exposed)
        self._start_manager()
    
    def _start_manager(self):
        try:
            mngr = self._Manager()
            mngr.start()
        except:
            mngr = None
        self._mngr = mngr
        print ':::::::::::::::: THE STARTED MANAGER: %r' % mngr
    
    def is_active(self):
        try:
            return self._mngr.is_active()
        except AttributeError:
            return True
    
    def __getattr__(self, name):
        def wrap(*args, **kwargs):
            try:
                return getattr(self._getproxy(), name)(*args, **kwargs)
            except (IOError, EOFError):
                return getattr(self._shared(), name)(*args, **kwargs)
        return wrap
    
    def __call__(self, *args):
        return self._getproxy(*args)
    
    def _getproxy(self):
        proxy = None
        if self._mngr:
            try:
                proxy = getattr(self._mngr, self._name)()
            except (IOError, EOFError):
                pass
        if proxy is None:
            proxy = self._shared()
        return proxy
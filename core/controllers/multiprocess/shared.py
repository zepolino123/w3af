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
    
    def __init__(self, shared, exposed=()):
        class _Manager(BaseManager):
            pass
        self.name = name = str(id(self))
        _shared = shared if callable(shared) else lambda: shared
        _Manager.register(name, _shared, exposed=exposed)
        _mngr = _Manager()
        _mngr.start()
        self.getproxy = getattr(_mngr, name)
    
    def __getattr__(self, name):
        return getattr(self.getproxy(), name)
    
    def __call__(self, *args):
        return self.getproxy(*args)
    
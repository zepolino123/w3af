'''
dpCache.py

Copyright 2006 Andres Riancho

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

import threading

from core.controllers.misc.lru import LRU
from core.controllers.multiprocess import Shared
from core.data.parsers.documentParser import DocumentParser

class DPCache(object):
    '''
    This class is a document parser cache.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    def __init__(self):
        self._cache = LRU(30)
        self._LRULock = threading.RLock()
        
    def getDocumentParserFor(self, httpResponse):
        # Before I used md5, but I realized that it was unnecessary.
        # I experimented a little bit with python's hash functions
        # At first I thought that the built-in hash wasn't good enough,
        # as it could create collisions... but... given that the LRU has
        # only 30 positions, the real probability of a collision is too low.
        hash_string = hash(httpResponse.body)
        
        with self._LRULock:
            try:
                dp = self._cache[hash_string]
            except KeyError:
                dp = DocumentParser(httpResponse)
                self._cache[hash_string] = dp
            return dp
    
dp_cache = Shared(DPCache())
'''
Copyright 2009 Andres Riancho

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
from __future__ import with_statement
import sqlite3
import thread
import sys

try:
    from cPickle import Pickler, Unpickler
except ImportError:
    from pickle import Pickler, Unpickler

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import core.data.kb.knowledgeBase as kb
import core.controllers.outputManager as om
import re
import os
from core.controllers.w3afException import w3afException
from core.data.db.persist import persist

from core.data.db.persist import persist
from core.controllers.misc.homeDir import get_home_dir
import core.data.kb.config as cf

class History:
    """Provide convinient way to access history."""

    def __init__(self):
        pass

    def begin(self):
        sessionName = cf.cf.getData('sessionName')
        dbName = os.path.join(get_home_dir(), 'sessions', 'db_' + sessionName)
        # Just in case the directory doesn't exist...
        try:
            os.mkdir(os.path.join(get_home_dir() , 'sessions'))
        except OSError, oe:
            # [Errno 17] File exists
            if oe.errno != 17:
                msg = 'Unable to write to the user home directory: ' + get_home_dir()
                raise w3afException( msg )

        self._db = persist()
        # Check if the database already exists
        if os.path.exists(dbName):
            # Find one that doesn't exist
            for i in xrange(100):
                newDbName = dbName + '-' + str(i)
                if not os.path.exists(newDbName):
                    dbName = newDbName
                    break
        # Create one!
        self._db.create(dbName, ['id', 'url', 'code'])

    def end(self):
        pass
    def search(self, data):
        pass
    def searchById(self, id):
        pass
    def searchAll(self, data):
        pass
    def getNewItem(self):
        newItem = HistoryItem(self._db)
        print "getNewItem"
        return newItem

class HistoryItem:
    _db = None
    id = None
    request = None
    response = None
    info = None
    mark = False

    def __init__(self, db=None):
        if db:
            self._db = db

    def read(self):
        pass

    def save(self):
        if not self.id:
            self._db.persist((self.response.getId(), self.request.getURI(),
                self.response.getCode()), (self.request, self.response))
            self.id = self.response.getId()
        return True

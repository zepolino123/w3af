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
from core.data.db.db import DB
from core.controllers.misc.homeDir import get_home_dir
import core.data.kb.config as cf

class History:
    '''Provides convinient way to access history.'''

    def __init__(self):
        '''Construct object.'''
        self._db = None

    def begin(self):
        '''Create DB and add tables.'''
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

        self._db = DB()
        # Check if the database already exists
        if os.path.exists(dbName):
            # Find one that doesn't exist
            for i in xrange(100):
                newDbName = dbName + '-' + str(i)
                if not os.path.exists(newDbName):
                    dbName = newDbName
                    break
        # Create DB!
        self._db.open(dbName)
        # Create table
        self._db.createTable('data_table', [('id','integer'), ('url', 'text'),
            ('code', 'text'), 'raw_pickled_data', 'blob'], ['id',])

    def end(self):
        '''End history.'''
        self._db.close()

    def getNewItem(self):
        '''Factory for new items.'''
        newItem = HistoryItem(self._db)
        return newItem

class HistoryItem:
    _db = None
    _dataTable = 'data_table'
    id = None
    request = None
    response = None
    info = None
    mark = False

    def __init__(self, db=None):
        '''Construct object.'''
        if db:
            self._db = db

    def find(self, searchData, resultLimit=-1, orderData=[]):
        '''Make complex search.
        search_data = [(name, value, operator), ...]
        '''
        if not self._db:
            raise w3afException('The database is not initialized yet.')
        sql = 'SELECT * FROM ' + self._dataTable
        where = ' WHERE 1=1 '
        result = []
        # FIXME add prepared statements!
        for item in searchData:
            oper = "="
            value = item[1]
            if len(item) > 2:
                oper = item[2]
            if isinstance(value, str):
                value = "'" + value + "'"
            else:
                value = str(value)
            where += " AND (" + item[0] + " " + oper + " " + value + ")"

        orderby = ""
        for item in orderData:
            orderby += item[0] + " " + item[1] + ","
        orderby = orderby[:-1]

        if orderby:
            sql += " ORDER BY " + orderby

        sql += ' LIMIT '  + str(resultLimit)

        try:
            rawResult = self._db.retrieveAll(sql)
            for row in rawResult:
                item = self._db.getNewItem()
                f = StringIO(str(row[-1]))
                req, res = Unpickler(f).load()
                item.id = res.getId()
                item.request = req
                item.response = res
                result.append(item)
        except w3afException:
            raise w3afException('You performed an invalid search. Please verify your syntax.')
        return result

    def load(self, id=None):
        '''Load data from DB by ID.'''
        if not self._db:
            raise w3afException('The database is not initialized yet.')

        if not id:
            id = self.id

        sql = 'SELECT * FROM ' + self._dataTable + ' WHERE id = ? '
        try:
            row = self._db.retrieve(sql, (id,))
            f = StringIO(str(row[-1]))
            req, res = Unpickler(f).load()
            self.request = req
            self.response = res
        except w3afException:
            raise w3afException('You performed an invalid search. Please verify your syntax.')
        return True

    def save(self):
        # Insert 
        if not self.id:
            values = []
            values.append(self.response.getId())
            values.append(self.request.getURI())
            values.append(self.request.getCode())
            f = StringIO()
            p = Pickler(f)
            p.dump((self.request, self.response))
            values.append(f.getvalue())
            sql = 'INSERT INTO ' + self._dataTable + ' (id, url, code, raw_pickled_data)'
            sql += ' VALUES (?,?,?,?)'
            self._db.execute(sql, values)
            self.id = self.response.getId()
        else:
            # Update
            pass
        return True

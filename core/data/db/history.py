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

class HistoryItem:
    _db = None
    _dataTable = 'data_table'
    _columns = [('id','integer'), ('url', 'text'), ('code', 'text'),
            ('raw_pickled_data', 'blob')]
    id = None
    request = None
    response = None
    info = None
    mark = False
    _primaryKeyColumns = ['id',]

    def __init__(self, db=None):
        '''Construct object.'''
        if db:
            self._db = db
        elif not kb.kb.getData('gtkOutput', 'db') == []:
            # Restore it from the kb
            self._db = kb.kb.getData('gtkOutput', 'db')
        else:
            raise w3afException('The database is not initialized yet.')

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
                item = self.__class__(self._db)
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
            self.id = self.response.getId()
        except w3afException:
            raise w3afException('You performed an invalid search. Please verify your syntax.')
        return True

    def read(self, id):
        '''Return item by ID.'''
        if not self._db:
            raise w3afException('The database is not initialized yet.')
        resultItem = self.__class__(self._db)
        resultItem.load(id)
        return resultItem

    def save(self):
        '''Save object into DB.'''
        if not self.id:
            values = []
            values.append(self.response.getId())
            values.append(self.request.getURI())
            values.append(self.response.getCode())
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

    def getColumns(self):
        return self._columns

    def getTableName(self):
        return self._dataTable

    def getPrimaryKeyColumns(self):
        return self._primaryKeyColumns


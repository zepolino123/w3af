'''
knowledgeBase.py

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

from multiprocessing import Lock
from core.controllers.multiprocess import Shared
import core.data.kb.info as info
import core.data.kb.shell as shell
import core.data.kb.vuln as vuln


class KnowledgeBase(object):
    '''
    This class saves the data that is sent to it by plugins. It is the
    only way in which plugins can talk to each other.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    
    def __init__(self):
        self._kb = {}
        self._kb_lock = Lock()

    def save(self, pluginname, variableName, value):
        '''
        This method saves the variableName value to a dict.
        '''
        with self._kb_lock:
            self._kb.setdefault(pluginname, {})[variableName] = value
        
    def append(self, name, variableName, value):
        '''
        This method appends the variableName value to a dict.
        '''
        with self._kb_lock:
            vals = self._kb.setdefault(name, {}).setdefault(variableName, [])
            vals.append(value)
        
    def getData(self, pluginname, variableName=None):
        '''
        @parameter pluginname: The plugin that saved the data to the
            kb.info Typically the name of the plugin.
        @parameter variableName: The name of the variables under which
            the vuln objects were saved. Typically the same name of the
            plugin, or something like "vulns", "errors", etc. In most
            cases this is NOT None. When set to None, a dict with all
            the vuln objects found by the plugin that saved the data
            is returned.
        @return: Returns the data that was saved by another plugin.
        '''        
        res = []
        
#        with self._kb_lock:
#            if variableName is None:
#                res = self._kb.get(pluginname, [])
#            else:
#                res = self._kb.get(pluginname, {}).get(variableName, [])
#                if len(res) == 1:
#                    res = res[0]
#            return res
            
        if pluginname not in self._kb.keys():
            res = []
        else:
            if variableName is None:
                res = self._kb[pluginname]
            elif variableName not in self._kb[pluginname].keys():
                res = []
            else:
                res = self._kb[pluginname][variableName]
        return res

    def getAllEntriesOfClass(self, klass):
        '''
        @return: A list of all objects of class == klass that are
            saved in the kb.
        '''
        res = []
        
        with self._kb_lock:
            for pdata in self._kb.values():
                for vals in pdata.values():
                    if not isinstance(vals, list):
                        continue
                    for v in vals:
                        if isinstance(v, klass) :
                            res.append(v)
        return res
    
    def getAllVulns(self):
        '''
        @return: A list of all vulns reported by all plugins.
        '''
        return self.getAllEntriesOfClass(vuln.vuln)
    
    def getAllInfos(self):
        '''
        @return: A list of all vulns reported by all plugins.
        '''
        return self.getAllEntriesOfClass(info.info)
    
    def getAllShells(self):
        '''
        @return: A list of all vulns reported by all plugins.
        '''
        return self.getAllEntriesOfClass(shell.shell)
        
    def dump(self):
        return self._kb
    
    def cleanup(self):
        '''
        Cleanup internal data.
        '''
        self._kb.clear()

# Multiprocess shared KnowledgeBase
kb = Shared(KnowledgeBase())

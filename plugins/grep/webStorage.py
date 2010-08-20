'''
webStorage.py

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
import core.controllers.outputManager as om
from core.data.options.option import option
from core.data.options.optionList import optionList
from core.controllers.basePlugin.baseGrepPlugin import baseGrepPlugin
import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
import core.data.constants.severity as severity

class webStorage(baseGrepPlugin):
    '''
    Grep every page for traces of WebStorage.
      
    @author: Taras (oxdef@oxdef.info)
    '''
    
    def __init__(self):
        baseGrepPlugin.__init__(self)
        self.patterns = ['localStorage', 'sessionStorage']

    def grep(self, request, response):
        '''
        Plugin entry point, search for the webStorage usage.
        @parameter request: The HTTP request object.
        @parameter response: The HTTP response object
        @return: None
        '''
        res = []

        if not response.is_text_or_html():
            return
        body = response.getBody()

        for riskyCode in self.patterns:
            if riskyCode in body:
                res.append(riskyCode)

        for vulnCode in res:
            v = vuln.vuln()
            v.addToHighlight(vulnCode)
            v.setURL(response.getURL())
            v.setId(response.id)
            v.setSeverity(severity.LOW)
            v.setName('Web Storage (Risky JavaScript Code)')
            msg = 'The URL: "' + v.getURL() + '" contains usage of Web Storage (risky JavaScript code)'
            msg += ': "'+ vulnCode + '".'
            v.setDesc(msg)
            kb.kb.append(self, 'webStorage', v)

    def setOptions(self, optionsMap):
        pass

    def getOptions(self):
        '''
        @return: A list of option objects for this plugin.
        '''
        ol = optionList()
        return ol

    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self.printUniq(kb.kb.getData('webStorage', 'webStorage'), None)

    def getPluginDeps(self):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return []

    def getLongDesc(self):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin greps every page for traces of WebStorage (HTML5 feature).
        More informaion: http://www.w3.org/TR/webstorage/
        '''

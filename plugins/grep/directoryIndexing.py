'''
directoryIndexing.py

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
import re

from core.controllers.basePlugin.baseGrepPlugin import baseGrepPlugin
from core.data.bloomfilter.bloomfilter import scalable_bloomfilter
from core.data.kb.knowledgeBase import kb
import core.data.constants.severity as severity
import core.data.kb.vuln as vuln


class directoryIndexing(baseGrepPlugin):
    '''
    Grep every response for directory indexing problems.
      
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    ### TODO: verify if I need to add more values here, IIS !!!
    _indexing_re = (
        "<title>Index of /",
        '<a href="\\?C=N;O=D">Name</a>',
        "Last modified</a>",
        "Parent Directory</a>",
        "Directory Listing for",
        "<TITLE>Folder Listing.",
        '<table summary="Directory Listing" ',
        "- Browsing directory ",
        '">\\[To Parent Directory\\]</a><br><br>', # IIS 6.0 and 7.0
        '<A HREF=".*?">.*?</A><br></pre><hr></body></html>' # IIS 5.0
        )

    # Added performance by compiling all the regular expressions
    # before using them. The setup time of the whole plugin raises,
    # but the execution time is lowered *a lot*.
    _compiled_regex_list = [
        re.compile(regex, re.IGNORECASE|re.DOTALL) for regex in _indexing_re
        ]

    def __init__(self):
        baseGrepPlugin.__init__(self)
        
        self._already_visited = scalable_bloomfilter()

    def grep(self, request, response):
        '''
        Plugin entry point, search for directory indexing.
        @parameter request: The HTTP request object.
        @parameter response: The HTTP response object
        @return: None
        '''
        url = response.getURL()
        domain_path = url.getDomainPath()
        
        if not domain_path in self._already_visited and response.is_text_or_html():
            self._already_visited.add(domain_path)
            # Work,
            html_string = response.getBody()
            for indexing_regex in self._compiled_regex_list:
                if indexing_regex.search(html_string):
                    v = vuln.vuln()
                    v.setPluginName(self.name)
                    v.setURL(url)
                    msg = 'The URL: "' + url + '" has a directory '
                    msg += 'indexing vulnerability.'
                    v.setDesc(msg)
                    v.setId(response.id)
                    v.setSeverity(severity.LOW)
                    path = url.getPath()
                    v.setName('Directory indexing - ' + path)
                    
                    kb.append(self.name , 'directory' , v)
                    break
        
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self.printUniq(kb.getData( 'directoryIndexing', 'directory'), 'URL')
    
    @staticmethod
    def getLongDesc():
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin greps every response directory indexing problems.
        '''

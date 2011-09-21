'''
ajax.py

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
from core.data.options.optionList import optionList
import core.data.kb.info as info
import core.data.kb.knowledgeBase as kb


class ajax(baseGrepPlugin):
    '''
    Grep every page for traces of Ajax code.
      
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    # Regular expression to search for AJAX
    AJAX_RE = re.compile(
        '(XMLHttpRequest|eval\(|ActiveXObject|Msxml2\.XMLHTTP|'
        'ActiveXObject|Microsoft\.XMLHTTP)',
        re.IGNORECASE
        )
    _already_inspected = scalable_bloomfilter()
    
    def grep(self, request, response):
        '''
        Plugin entry point.
        
        @parameter request: The HTTP request object.
        @parameter response: The HTTP response object
        @return: None, all results are saved in the kb.
        
        Init
        >>> from core.data.url.httpResponse import httpResponse
        >>> from core.data.request.fuzzableRequest import fuzzableRequest
        >>> from core.controllers.misc.temp_dir import create_temp_dir
        >>> from core.data.parsers.urlParser import url_object
        >>> o = create_temp_dir()

        Simple test, empty string.
        >>> body = ''
        >>> url = url_object('http://www.w3af.com/')
        >>> headers = {'content-type': 'text/html'}
        >>> response = httpResponse(200, body , headers, url, url)
        >>> request = fuzzableRequest()
        >>> request.setURL( url )
        >>> request.setMethod( 'GET' )
        >>> a = ajax()
        >>> a.grep(request, response)
        >>> assert len(kb.kb.getData('ajax', 'ajax')) == 0

        Discover ajax!
        >>> body = '<html><head><script>xhr = new XMLHttpRequest(); xhr.open(GET, "data.txt",  true); </script></head><html>'
        >>> url = url_object('http://www.w3af.com/')
        >>> headers = {'content-type': 'text/html'}
        >>> response = httpResponse(200, body , headers, url, url)
        >>> request = fuzzableRequest()
        >>> request.setURL( url )
        >>> request.setMethod( 'GET' )
        >>> a = ajax()
        >>> a.grep(request, response)
        >>> assert len(kb.kb.getData('ajax', 'ajax')) == 1

        Discover ajax with a broken script tag that doesn't close
        >>> kb.kb.save('ajax','ajax',[])
        >>> body = '<html><head><script>xhr = new XMLHttpRequest(); xhr.open(GET, "data.txt",  true); </head><html>'
        >>> url = url_object('http://www.w3af.com/')
        >>> headers = {'content-type': 'text/html'}
        >>> response = httpResponse(200, body , headers, url, url)
        >>> request = fuzzableRequest()
        >>> request.setURL( url )
        >>> request.setMethod( 'GET' )
        >>> a = ajax()
        >>> a.grep(request, response)
        >>> assert len(kb.kb.getData('ajax', 'ajax')) == 1

        Discover ajax with a broken script, head and html tags.
        >>> kb.kb.save('ajax','ajax',[])
        >>> body = '<html><head><script>xhr = new XMLHttpRequest(); xhr.open(GET, "data.txt",  true);'
        >>> url = url_object('http://www.w3af.com/')
        >>> headers = {'content-type': 'text/html'}
        >>> response = httpResponse(200, body , headers, url, url)
        >>> request = fuzzableRequest()
        >>> request.setURL( url )
        >>> request.setMethod( 'GET' )
        >>> a = ajax()
        >>> a.grep(request, response)
        >>> assert len(kb.kb.getData('ajax', 'ajax')) == 1

        Another ajax function, no broken html.
        >>> kb.kb.save('ajax','ajax',[])
        >>> body = '<html><head><script> ... xhr = new ActiveXObject("Microsoft.XMLHTTP"); ... </script></head><html>'
        >>> url = url_object('http://www.w3af.com/')
        >>> headers = {'content-type': 'text/html'}
        >>> response = httpResponse(200, body , headers, url, url)
        >>> request = fuzzableRequest()
        >>> request.setURL( url )
        >>> request.setMethod( 'GET' )
        >>> a = ajax()
        >>> a.grep(request, response)
        >>> assert len(kb.kb.getData('ajax', 'ajax')) == 1

        Two functions, I only want one report for this page.
        >>> kb.kb.save('ajax','ajax',[])
        >>> body = '<script> ... xhr = new XMLHttpRequest(); ... xhr = new ActiveXObject("Microsoft.XMLHTTP"); ... </script>'
        >>> url = url_object('http://www.w3af.com/')
        >>> headers = {'content-type': 'text/html'}
        >>> response = httpResponse(200, body , headers, url, url)
        >>> request = fuzzableRequest()
        >>> request.setURL( url )
        >>> request.setMethod( 'GET' )
        >>> a = ajax()
        >>> a.grep(request, response)
        >>> len(kb.kb.getData('ajax', 'ajax'))
        1

        '''
        
        infos = []
        url = response.getURL()
        
        if response.is_text_or_html() and url not in self._already_inspected:
            
            # Don't repeat URLs
            self._already_inspected.add(url)
            
            dom = response.getDOM()
            # In some strange cases, we fail to normalize the document
            if dom is not None:

                script_elements = dom.xpath('.//script')
                for element in script_elements:
                    # returns the text between <script> and </script>
                    script_content = element.text
                    
                    if script_content is not None:
                        
                        res = self.AJAX_RE.search(script_content)
                        if res:
                            inf = info.info()
                            pname = self.getName()
                            inf.setPluginName(pname)
                            inf.setName('AJAX code')
                            inf.setURL(url)
                            inf.setDesc('The URL: "%s" has an AJAX code.' % url)
                            inf.setId(response.id)
                            inf.addToHighlight(res.group(0))
                            infos.append((pname, 'ajax', inf))
        return infos
    
    def setOptions(self, OptionList):
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
        self.printUniq(kb.kb.getData('ajax', 'ajax'), 'URL')

    def getPluginDeps(self):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return []
    
    @staticmethod
    def getLongDesc():
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin greps every page for traces of Ajax code.
        '''

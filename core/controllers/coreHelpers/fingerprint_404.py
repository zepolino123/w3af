'''
fingerprint_404.py

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
import cgi
import itertools
import urllib

from core.controllers.misc.decorators import retry
from core.controllers.misc.levenshtein import relative_distance_ge
from core.controllers.misc.lru import LRU
from core.controllers.multiprocess import Shared
from core.controllers.w3afException import w3afException, w3afMustStopException
from core.data.url.xUrllib import xUrllib
from core.data.fuzzer.fuzzer import createRandAlNum
import core.controllers.outputManager as om
import core.data.kb.config as cf

__all__ = ['is_404']

def get_clean_body(response):
    '''
    Definition of 'clean' in this function:
        - input:
            - response.getURL() == http://host.tld/aaaaaaa/
            - response.getBody() == 'spam aaaaaaa eggs'
            
        - output:
            - self._clean_body( response ) == 'spam  eggs'
    
    The same works with filenames.
    All of them, are removed encoded and "as is".
    
    @parameter response: The httpResponse object to clean
    @return: A string that represents the "cleaned" response
        body of the response.
    '''
    
    body = response.body
    
    if response.is_text_or_html():
        url = response.getURL()
        to_replace = url.url_string.split('/')
        to_replace.append(url.url_string)
        
        for repl in to_replace:
            if len(repl) > 6:
                unquote_repl = urllib.unquote_plus(repl)
                body = body.replace(repl, '')
                body = body.replace(unquote_repl, '')
                body = body.replace(cgi.escape(repl), '')
                body = body.replace(cgi.escape(unquote_repl), '')

    return body


class Fingerprint404(object):
    '''
    Read the 404 page(s) returned by the server.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    # Sequence of the most common handlers
    handlers = (
        'py', 'php', 'asp', 'aspx', 'do', 'jsp', 'rb',
        'do', 'gif', 'htm', 'pl', 'cgi', 'xhtml', 'htmls'
        )
    IS_EQUAL_RATIO = 0.90
    
    def __init__(self, url):
        self._404_bodies = self._generate_404_knowledge(url)
        self.is_404_LRU = LRU(500)
    
    def is_404(self, http_response):
        '''
        All of my previous versions of is_404 were very complex and
        tried to struggle with all possible cases. The truth is that
        in most "strange" cases I was failing miserably, so now I
        changed my 404 detection once again, but keeping it as simple
        as possible.
        
        Also, and because I was trying to cover ALL CASES, I was
        performing a lot of requests in order to cover them,
        which in most situations was unnecessary.
        
        So now I go for a much simple approach:
            1- Cover the simplest case of all using only 1 HTTP request
            2- Give the users the power to configure the 404 detection
                by setting a string that identifies the 404 response
                (in case we are missing it for some reason in case #1)
        
        @parameter http_response: The HTTP response which we want to
            know if it is a 404 or not.
        '''
        
        # First we handle the user configured exceptions:
        domain_path = http_response.getURL().getDomainPath()
        if domain_path in cf.cf.getData('always404'):
            return True
        elif domain_path in cf.cf.getData('never404'):
            return False        
        
        # This is the most simple case, we don't even have to think
        # about this.
        #
        # If there is some custom website that always returns 404 codes,
        # then we are screwed, but this is open source, and the pentester
        # working on that site can modify these lines.
        if http_response.getCode() == 404:
            return True
            
        # The user configured setting. "If this string is in the response,
        # then it is a 404"
        _404string = cf.cf.getData('404string')
        if _404string and _404string in http_response:
            return True
            
        # Before actually working, I'll check if this response is in the
        # LRU, if it is I just return the value stored there.
        if http_response.id in self.is_404_LRU:
            return self.is_404_LRU[http_response.id]
        
        # self._404_body was already cleaned inside generate_404_knowledge
        # so we need to clean this one.
        html_body = get_clean_body(http_response)
        
        # Compare this response to all the 404's I have in my DB
        for body_404_db in self._404_bodies:
            
            if relative_distance_ge(
                                body_404_db,
                                html_body,
                                self.IS_EQUAL_RATIO
                                ):
                om.out.debug(
                        '"%s" is a 404. [similarity_index > %s]' % 
                        (http_response.getURL(), self.IS_EQUAL_RATIO)
                        )
                self.is_404_LRU[http_response.id] = True
                return True
        else:
            om.out.debug(
                    '"%s" is NOT a 404. [similarity_index < %s]' % 
                    (http_response.getURL(), self.IS_EQUAL_RATIO)
                    )
            self.is_404_LRU[http_response.id] = False
            return False
        
    def _generate_404_knowledge(self, url):
        '''
        Based on a URL, request something that we know is going to be a 404.
        Afterwards analyze the 404's and summarize them.
        
        @return: A list with 404 bodies.
        '''
        # Get the filename extension and create a 404 for it
        domain_path = url.getDomainPath()
        # the result
        bodies = []        
        
        handlers = set(self.handlers)
        handlers.add(url.getExtension())
        url_opener = xUrllib()
        
        for ext in handlers:
            rand_alnum_file = createRandAlNum(8) + '.' + ext
            url404 = domain_path.urlJoin(rand_alnum_file)
            body = self._send_404(url_opener, url404)
            bodies.append(body)
            
        # Ignore similar responses
        result = set()
        result.add(bodies[0])
        for body_i, body_j in itertools.permutations(bodies, 2):
            if not relative_distance_ge(body_i, body_j, self.IS_EQUAL_RATIO):
                result.add(body_j)
        
        om.out.debug('The 404 body result database has a length of %s.'
                     % len(result))
        return result 
        
    @retry(tries=2, delay=0.5, backoff=2)
    def _send_404(self, url_opener, url404):
        '''
        Sends a GET request to url404 and saves the response 
            in self._response_body_list .
        '''
        try:
            # I don't use the cache, because the URLs are random
            # and the only thing that useCache does is to fill
            # up disk space
            response = url_opener.GET(
                                url404, useCache=False, grepResult=False
                                )
        except w3afException, w3:
            raise w3afException('Exception while fetching a 404 '
                                'page, error: %s' % w3)
        except w3afMustStopException, mse:
            # Someone else will raise this exception and handle
            # it as expected whenever the next call to GET is done
            raise w3afException('w3afMustStopException <%s> found by '
                                '_send_404, someone else will handle it.'
                                % mse)
        except Exception, e:
            om.out.error('Unhandled exception while fetching a 404 page, '
                         'error: %s' % e)
            raise

        # I don't want the random file name to affect the 404, so I
        # replace it with a blank space
        return get_clean_body(response)


_fp404 = None

def init_404(url, reset=False):
    assert _fp404 is None or reset, "404 database has already been inited"
    if not _fp404 or reset:
        global _fp404
        _fp404 = Shared(
                    Fingerprint404(url), exposed=('is_404',)
                    )

def is_404(http_resp):
    return _fp404.is_404(http_resp)
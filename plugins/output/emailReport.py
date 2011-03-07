'''
emailReport.py

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

import time
import os
import smtplib
from email.mime.text import MIMEText

from core.controllers.basePlugin.baseOutputPlugin import baseOutputPlugin
from core.controllers.w3afException import w3afException
from core.controllers.falsePositiveManager import falsePositiveManager
import core.data.kb.knowledgeBase as kb
import core.data.kb.config as cf
from core.data.options.option import option
from core.data.options.optionList import optionList
import core.data.constants.severity as severity

MSG_TMPL = '''Hello!
Target: %s has some vulnerabilities.

'''

class emailReport(baseOutputPlugin):
    '''Email reporter class.'''

    def __init__(self):
        baseOutputPlugin.__init__(self)
        self.targets = []
        self.tpl = MSG_TMPL
        self.smtpServer = 'localhost'
        self.smtpPort = 25
        self.toAddrs = ''
        self.fromAddr = ''
        self._fpManager = falsePositiveManager()
        self._exec = False

    def logEnabledPlugins(self, pluginsDict, optionsDict):
        self.targets = cf.cf.getData('targets')

    def setOptions(self, OptionList):
        smtpServer = OptionList['smtpServer'].getValue()
        self.smtpServer, self.smtpPort = smtpServer.split(":")
        self.fromAddr = OptionList['fromAddr'].getValue()
        self.toAddrs = OptionList['toAddrs'].getValue()

    def getOptions(self):
        ol = optionList()
        d = 'SMTP server:port to send notifications through'
        o = option('smtpServer', self.smtpServer+':'+str(self.smtpPort), d, 'ipport')
        ol.add(o)
        d = 'Recipient email address'
        o = option('toAddrs', self.toAddrs, d, 'list')
        ol.add(o)
        d = '"From" email address'
        o = option('fromAddr', self.fromAddr, d, 'string')
        ol.add(o)
        return ol

    def end(self):
        if not self.targets or self._exec:
            return
        self._exec = True
        data = self.tpl % (self.targets[0])
        vulns = kb.kb.getAllVulns()
        realVulns = 0
        for v in vulns:
            if not self._fpManager.isFalsePositive(v.getURI()):
                realVulns += 1
                data += v.getDesc() + '\n'
        if not realVulns:
            return
        msg = MIMEText(data)
        msg['From'] = self.fromAddr
        msg['To'] = ', '.join(self.toAddrs)
        msg['Subject'] = 'W3AF report on %s' % self.targets[0]
        server = smtplib.SMTP(self.smtpServer, int(self.smtpPort))
        server.sendmail(self.fromAddr, self.toAddrs, msg.as_string())
        server.quit()

    def getLongDesc(self):
        '''Return a DETAILED description of the plugin functions and features.'''
        return '''This plugin send short report by email.'''

    def debug(self, message, newLine = True):
        pass

    def information(self, message , newLine = True):
        pass

    def error(self, message , newLine = True):
        pass

    def vulnerability(self, message , newLine=True, severity=severity.MEDIUM):
        pass

    def console(self, message, newLine = True):
        pass

    def logHttp(self, request, response):
        pass

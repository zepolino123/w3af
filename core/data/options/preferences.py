'''
preferences.py

Copyright 2010 Andres Riancho

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

class Preferences(object):
    '''Class for grouping option lists.'''
    def __init__(self):
        '''Contructor.'''
        self.sections = {}
        self.options = {}

    def addSection(self, section='default', label=None, optionList=None):
        '''Add a section named section to the instance.'''
        self.sections[section] = label
        self.options[section] = optionList

    def hasSection(self, section):
        '''Indicates whether the named section is present in the configuration.'''
        return (section in self.sections)

    def getOptions(self, section):
        '''Returns a list of options available in the specified section.'''
        return self.options[section]

    def hasOption(self, section, option):
        '''If the given section exists, and contains the given option, return True; otherwise return False.'''
        if section in self.options and option in self.options[section]:
            return True
        else:
            return False

    def get(self, section, option):
        '''Get an option value for the named section.'''
        if self.hasOption(section, option):
            return self.options[section][option]

    def getValue(self, section, option):
        '''Get an option value for the named section.'''
        if self.hasOption(section, option):
            return self.options[section][option].getValue()

    def set(self, section, option):
        '''If the given section exists, set the given option to the specified value; 
        otherwise raise NoSectionError.'''
        if self.hasSection(section):
            self.options[section][option.getName()] = option

    def setValue(self, section, option, value):
        '''If the given section exists, set the given option to the specified value; 
        otherwise raise NoSectionError.'''
        if self.hasSection(section):
            self.options[section][option.getName()].setValue(value)

    def removeOption(self, section, option):
        '''Remove the specified option from the specified section.
        If the section does not exist, raise NoSectionError.'''
        if self.sectons.has_key(section):
            del self.sections[section][option]

    def removeSection(self, section):
        '''Remove the specified section from the configuration. 
        If the section in fact existed, return True. Otherwise return False.'''
        if self.sectons.has_key(section):
            del self.sections[section]
            del self.options[section]
            return True
        else:
            return False


import re
import unittest
import core.data.kb.config as cf

class falsePositiveManager(object):
    def __init__(self):
        self.patterns = []
        self.patternFile = cf.cf.getData('falsePositiveFile')
        if self.patternFile:
            self.loadFromFile(self.patternFile)

    def loadFromList(self, patterns):
        self.patterns = [re.compile(url.strip(), re.IGNORECASE) for url in patterns]

    def loadFromFile(self, filename):
        patternFile = open(filename)
        lines = patternFile.readlines()
        patternFile.close()
        self.loadFromList(lines)

    def isFalsePositive(self, url):
        for p in self.patterns:
            if p.match(url):
                return True
        return False

class TestFalsePositiveManager(unittest.TestCase):

    def setUp(self):
        self.goodTargets = [
                'http://google.com/.htaccess',
                'http://fbi.com/.bash_history'
                ]

        self.badTargets = [
                'http://foo.com/.ssh/known_hosts',
                'http://example.mil/logs'
                ]
        self.patterns = [
                'http://foo.com/*',
                'http://example.m*'
                ]

    def test_sample(self):
        app = falsePositiveManager()
        app.loadFromList(self.patterns)

        for goodTarget in self.goodTargets:
            self.assertFalse(app.isFalsePositive(goodTarget))

        for badTarget in self.badTargets:
            self.assertTrue(app.isFalsePositive(badTarget))

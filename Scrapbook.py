#!/usr/bin/python
#
# LiveJournal Scrapbook downloader.
# Make sure you're logged in Firefox.
#
# On Windows, a newer version of sqlite3.dll must be downloaded from http://sqlite.org/download.html and put to C:\Python27\DLLs
#
from cookielib import Cookie, LWPCookieJar
from os import listdir, makedirs
from os.path import expanduser, getmtime, isdir, isfile, join
from platform import system
from sqlite3 import connect
from sys import argv, exit, getfilesystemencoding, stdout # pylint: disable=W0622
from urllib2 import build_opener, HTTPCookieProcessor, Request

try:
    from bs4 import BeautifulSoup
except ImportError, ex:
    raise ImportError("%s: %s\nPlease install BeautifulSoup v4.3.2 or later: http://www.crummy.com/software/BeautifulSoup\n" % (ex.__class__.__name__, ex))

FIREFOX_PROFILES_LINUX = '~/.mozilla/firefox'
FIREFOX_PROFILES_WINDOWS = r'~\Application Data\Mozilla\Firefox\Profiles'
FIREFOX_COOKIE_FILE = 'cookies.sqlite'
FIREFOX_COOKIES_SQL_REQUEST = "SELECT host, path, isSecure, expiry, name, value FROM moz_cookies WHERE host LIKE '%%%s%%'"

isWindows = system().lower().startswith('win')

def getFirefoxCookies(domain = ''):
    """Returns Mozilla Firefox cookies for the specified domain."""
    profilesPath = unicode(expanduser(FIREFOX_PROFILES_WINDOWS if isWindows else FIREFOX_PROFILES_LINUX))
    cookieFiles = (join(profilesPath, f, FIREFOX_COOKIE_FILE) for f in listdir(profilesPath))
    cookieDB = sorted((f for f in cookieFiles if isfile(f)), key = getmtime)[-1]
    cursor = connect(cookieDB).cursor()
    cursor.execute(FIREFOX_COOKIES_SQL_REQUEST % domain)
    cookieJar = LWPCookieJar()
    for (host, path, isSecure, expiry, name, value) in cursor.fetchall():
        cookieJar.set_cookie(Cookie(0, name, value, None, False,
            host, host.startswith('.'), host.startswith('.'),
            path, False, isSecure, expiry, not expiry, None, None, {}))
    return cookieJar

def loadWithCookies(url, cookieJar, userAgent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'):
    """Returns a document download from the specified URL, accessed with specified cookies."""
    opener = build_opener(HTTPCookieProcessor(cookieJar))
    return opener.open(Request(url, None, {'User-Agent' : userAgent})).read()

INVALID_FILENAME_CHARS = '<>:"/\\|?*\'' # for file names, to be replaced with _
def cleanupFileName(fileName):
    return ''.join('_' if c in INVALID_FILENAME_CHARS else c for c in fileName)

CONSOLE_ENCODING = stdout.encoding or ('cp866' if isWindows else 'UTF-8')
def encodeForConsole(s):
    return s.encode(CONSOLE_ENCODING, 'replace')

FILE_SYSTEM_ENCODING = getfilesystemencoding()
def encodeForFileSystem(s):
    return s.encode(FILE_SYSTEM_ENCODING, 'replace')

COOKIE_SOURCES = {'firefox': getFirefoxCookies}

COOKIE_DOMAIN = 'livejournal.com'

START_URL = 'http://pics.livejournal.com'

HREF = 'href'
CLASS = 'class'
ALBUM_SELECTOR = 'h3 a'
IMAGE_SELECTOR = '.l-content .b-pics-list-albums-img'
IMAGE_TITLE_SELECTOR = '.b-pics-title'
IMAGE_TITLE_EMPTY_CLASS = 'b-pics-edit-empty'
IMAGE_LINK_SELECTOR = 'li. a'
PAGER_NEXT_SELECTOR = '.b-pics-pager-next'

class ScrapbookDownloader(object):
    def __init__(self, args):
        self.cookies = getFirefoxCookies(COOKIE_DOMAIN)
        self.targetDir = args[0] if args else '.'

    def load(self, url):
        return loadWithCookies(url, self.cookies)

    def run(self):
        print "Downloading to %s" % self.targetDir
        url = START_URL
        nAlbumListPage = 1
        while url:
            print ".page %d" % nAlbumListPage
            albumListPage = BeautifulSoup(self.load(url))
            for a in albumListPage.select(ALBUM_SELECTOR):
                albumName = a.text
                albumPath = join(self.targetDir, encodeForFileSystem(cleanupFileName(albumName)))
                if not isdir(albumPath):
                    makedirs(albumPath)
                print "..%s" % encodeForConsole(albumName)
                url = a[HREF]
                nAlbumPage = 1
                while url:
                    print "...page %d" % nAlbumPage
                    albumPage = BeautifulSoup(self.load(url))
                    for a in albumPage.select(IMAGE_SELECTOR):
                        url = a[HREF]
                        imagePage = BeautifulSoup(self.load(url))
                        title = imagePage.select(IMAGE_TITLE_SELECTOR)[0]
                        imageName = url.split('/')[-1] if IMAGE_TITLE_EMPTY_CLASS in title[CLASS] else title.text
                        print "....%s" % encodeForConsole(imageName)
                        url = imagePage.select(IMAGE_LINK_SELECTOR)[0][HREF]
                        with open(join(albumPath, '%s.%s' % (encodeForFileSystem(cleanupFileName(imageName)), url.split('.')[-1].lower())), 'wb') as f:
                            f.write(self.load(url))
                    url = albumPage.select(PAGER_NEXT_SELECTOR)[0].get(HREF)
                    nAlbumPage += 1
            url = albumListPage.select(PAGER_NEXT_SELECTOR)[0].get(HREF)
            nAlbumListPage += 1

def main(args):
    exit(1 if ScrapbookDownloader(args).run() else 0)

if __name__ == '__main__':
    main(argv[1:])

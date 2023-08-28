"""
    Simple class for monitoring HTTP ETags (https://en.wikipedia.org/wiki/HTTP_ETag)
    This is useful to check whether or not changes have been made to a page.

    The only non-stdlib dependency of this class is on python-requests, but most people
    have that installed on their system, anyways.

    Sep 4 2017 (c) Charlton Trezevant
    MIT License

    Enjoy!
"""

import sqlite3
import os.path
import requests

class EtagMonitor(object):
    """
        Our constructor takes two keyword arguments:
            url, which is the url we want to reads etags from.
            dbpath, which is the path to the sqlite db we use to store etags persistently.

        Just about everything else is taken care of for you, including database initialization (to
        the point where dbpath doesn't have to point to an actual file). All you really have to do
        is call the constructor properly and run has_updated() at whatever interval you prefer.
    """
    def __init__(self, **kwargs):
        if os.path.isfile(kwargs['dbpath']) is not True:
            self.initialize_db(kwargs['dbpath'])
        else:
            self.connect_db(kwargs['dbpath'])

        self.url = kwargs['url']
        self.request = None

    """
        This method sets up the class' database variables for us. It's also used
        with the database initialization method due to certain properties of sqlite3's
        connect method (see below).
    """
    def connect_db(self, path):
        self.sqlite = sqlite3.connect(path)
        self.db = self.sqlite.cursor()

    """
        If the path provided to the constructor doesn't point to a valid database,
        then we need to create one.

        The Sqlite3 module's connect() method will automatically create a db file for us
        if none exists at the path provided. Once that's done we'll configure the tables
        appropriately and populate the last recorded etag with a fake string.
    """
    def initialize_db(self, path):
        self.connect_db(path)
        self.db.execute('CREATE TABLE etag (id INTEGER PRIMARY_KEY, last_tag text UNIQUE)')
        self.db.execute('INSERT INTO etag VALUES (?, ?)', (1, 'fake_etag'))
        self.sqlite.commit()

    """
        Returns whatever etag is currently stored in the sqlite database
    """
    def fetch_last_tag(self):
        return self.db.execute('SELECT * FROM etag WHERE id=1').fetchone()[1]

    """
        Retrieves the latest etag from the HTTP server headers, and returns it.
    """
    def fetch_latest_tag(self):
        self.request = requests.head(self.url)
        return self.request.headers['ETag'].replace('"', '')
        # Note for the above- if you have quotes inside of your ETag string
        # then it WILL break the INSERT in update_db

    """
        Will update the etag database with the latest etag provided.
    """
    def update_db(self, etag):
        self.db.execute('UPDATE etag SET last_tag=? WHERE id=1', (etag,))
        self.sqlite.commit()

    """
        Compares the last recorded etag to the most recently retrieved one from the server,
        and will return True if they are different (e.g. the page or file has been updated)
    """
    def has_updated(self):
        latest = self.fetch_latest_tag()

        if self.fetch_last_tag() != latest:
            self.update_db(latest)
            return True

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import urllib2
    
def download(url, maxage = 0.0):
    conn = sqlite3.connect('../data/cache.sqlite')
    conn.text_factory = str
    c = conn.cursor()
    data = ""

    # Make sure table exists
    c.execute('''CREATE TABLE IF NOT EXISTS cache  (url TEXT PRIMARY KEY, date DATE, content BLOB)''')
    conn.commit()

    # Attempt to retrieve cache
    c.execute('''SELECT * FROM cache WHERE url=?''', (url, ) )
    r = c.fetchone()

    needrenew = True
    try:
        needrenew = (r == None or float((datetime.now()-datetime.strptime(r[1], 
        "%Y-%m-%d %H:%M:%S.%f")).seconds) / (3600*24) > maxage)
    except:
        needrenew = True

    counter = 0
    if needrenew:
        # Robust download, keep attempting to download until successful
        while True:
            try:
                resp = urllib2.urlopen(url)
                data = resp.read().lower()
                resp.close()
                if len(data)>0:
                    break
            except:
                print "Download failed"
                if counter >= 10:
                    conn.close()
                    return "DOWNLOAD ERROR"
                counter += 1

        # Save in DB
        c.execute('''DELETE FROM cache WHERE url=?''',( url, ))
        c.execute('''INSERT into cache values (?,?,?)''', (url, datetime.now(), data) )
        conn.commit()
    else:
        data = r[2]

    # Close connection
    conn.close()
    
    return data
    
def downloadHTML(url, maxage=0):
    htmlStr = download(url, maxage)

    # Decode
    htmlStr = htmlStr.decode('utf-8', errors='replace')

    html = BeautifulSoup(htmlStr)

    return html
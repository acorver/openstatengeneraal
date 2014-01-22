import csv
import urllib
import os
import math
import pickledb

import sys
sys.path.append(os.getcwd())

from data import db

def parsedate(d):
    try:
        return datetime.strptime(d,"%Y-%m-%d")
    except:
        return None

if __name__ == "__main__":
    base = "../data/politicalmashup/"
    
    # Need to download files?
    if len([x for x in os.listdir(base) if x.endswith('.csv')])==0:
        for year in xrange(1994,2013):
            url = "http://backend.politicalmashup.nl/list-votes.xq?view=csv&period="+str(year)+"-"+str(year+1)
            f = str(year)+"-"+str(year+1) + ".csv"
            success = False
            while not success:
                try:
                    urllib.urlretrieve (url, base+f)
                except:
                    pass

    # Load all 'votes' data
    base = "./rawdata/politicalmashup/"
    for file in os.listdir(base):
        if file.endswith(".csv"):
            with open(base + file, 'rb') as csvfile:
                csvr = csv.reader(csvfile, delimiter=';')
                allrows = [x for x in csvr]
                headers = allrows[3]
                rows = [dict(zip(headers, x)) for x in allrows[4:]]

                # rename columns
                for i in xrange(len(headers)):
                    if headers[i]=='#house':
                        headers[i] = 'house'
                    elif headers[i]=='indiener 1':
                        headers[i] = 'submitter 1'
                    elif headers[i]=='partij indiener 1':
                        headers[o] = 'submitter 1 party'
                    elif headers[i]=='indiener 2':
                        headers[i] = 'submitter 2'
                    elif headers[i]=='partij indiener 2':
                        headers[o] = 'submitter 2 party'
                
                # assemble votes in 'votes' sub-dictionary
                for x in rows:
                    x['index'] = x['dossier nummer'].lstrip('0').rstrip()
                    if x['index'] == '':
                        continue
                    if x['onder nummer'].strip() != '':
                       x['index'] += '-' + x['onder nummer'].lstrip('0').rstrip()

                    x['votes'] = {}
                    partyCols = [y for y in x if y.startswith('nl.p.')]
                    for c in partyCols:
                        if x[c]!='':
                            vote = ('Y' if (x[c] in ['aye','yea','yes']) else 
                                    ('N' if (x[c] in ['nay','no']) else x[c]))
                            x['votes'][c[len('nl.p.'):]] = vote
                        x.pop(c, None)

                    db.store({'index': x['index'], 'type': 'vote', 'politicalmashup': x})
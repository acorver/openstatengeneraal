# ===================================================================
# JSON STORAGE USED THROUGHOUT APPLICATION
# ===================================================================

import json
import sqlite3
import requests
from bson import json_util
import elasticsearch as es
import pandas as pd

ES = None

# ===================================================================
# Helper methods
# ===================================================================

def getallAsDataFrame(transformFunc):
    arr = [x for x in map(transformFunc,getall()) if x != None]
    df = pd.DataFrame(arr)
    return df

# ===================================================================
# ElasticSearch
# ===================================================================

def esconnect():
    global ES
    if ES == None:
        ES = es.Elasticsearch()
    return ES

def getids(type=None, from_ = 0, size=10000000):
    all = esconnect().search(fields=[], from_ = from_, size=size)
    return [x['_id'] for x in all['hits']['hits'] if (type==None or x['_type']==type)]

def get(docid):
    return esconnect().get(index='openstatengeneraal', id=docid)['_source']

# SOURCE: http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
def chunk(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def getall(ids=None):
    docs = []
    counter = 0
    es = esconnect()

    if ids==None: ids = getids()
    
    for docids in list(chunk(ids, 1000)):
        docs += [x['_source'] for x in es.mget(index='openstatengeneraal', 
                                               doc_type='vote', 
                                               body={'ids': docids})['docs']]
        
    return docs

def store(doc):
    docs = None
    if isinstance(doc, list):
        docs = doc
    elif isinstance(doc, dict):
        docs = [doc, ]
    else:
        # Error
        return
    try:
        for d in docs:
            if not 'index' in d:
                # Error
                continue
            esconnect().update(
                index = 'openstatengeneraal', 
                id = d['index'], 
                doc_type = d['type'], 
                body = {
                    'doc': d, 
                    'doc_as_upsert': True
                }, 
                refresh = True)
    except:
        # Error
        pass
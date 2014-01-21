import os
import sys
sys.path.insert(0,os.getcwd())

import pandas as pd
from datetime import datetime
import collections
from operator import itemgetter
from data import db
from visualization.votedist import *

# =============================================================================
# Get votes by party
# =============================================================================

def filter(df, from_date = None, to_date = None, category = None, parties=None):
    fdf = df.copy()

    # Party requirement
    if parties!=None:
        todrop = [x for x in fdf.columns if (x.startswith('p.') and not x[len('p.'):] in parties)]
        fdf = fdf.drop(todrop, axis=1)

    # Date requirement
    if from_date != None and to_date != None:
        # Keep only those rows that have dates between the requirements
        fdf = fdf[map(lambda x: isinstance(x, datetime) and (x > from_date and x < to_date), fdf['date'])]
        
    # Category requirement
    if category != None:
        fdf = fdf[fdf.category==category]

    # Done!
    return fdf

# =============================================================================
# Calculate distance matrix
# =============================================================================

def distMtx(df):
    parties = [x for x in df.columns.tolist() if x.startswith('p.')]
    
    mtxDst = [[0 for x in xrange(len(parties))] for y in xrange(len(parties))]
    mtxNum = [[0 for x in xrange(len(parties))] for y in xrange(len(parties))]

    for x in xrange(len(parties)):
        for y in xrange(len(parties)):
            tdf = df[pd.notnull(df[parties[x]]) * pd.notnull(df[parties[y]])]
            num = len(tdf)
            if x==y:
                mtxDst[y][x] = 0
                mtxNum[y][x] = num
                continue
            if x > y:
                mtxDst[y][x] = mtxDst[x][y]
                mtxNum[y][x] = mtxNum[x][y]
                continue
            if num==0:
                mtxDst[y][x] = -1
                continue

            print str(x) + ", " + str(y) + " [len=" + str(num) + "]"

            # Calculate total distance (and save number of shared votes)
            dst = float(sum(abs(tdf[parties[x]] - tdf[parties[y]])))/num
            mtxDst[y][x] = dst
            mtxNum[y][x] = num

    # Return all information
    return {'actors': parties, 'distances':mtxDst, 'num_obs': mtxNum}

# =============================================================================
# Calculate distance matrices:
#    (1) Over all time
#    (2) Over periods of one year
#    (3) Over all time by category
#    (4) Over periods of one year by category
# =============================================================================

def transformData(x):
    try:
        d = {'id': x['index'], 
             'date': datetime.strptime(x['politicalmashup']['date of vote'], '%Y-%m-%d'),
             'house': x['politicalmashup']['#house']}
        for k in x['politicalmashup']['votes']:
            v = x['politicalmashup']['votes'][k]
            if v=='Y': v = 1
            elif v=='N': v = 2
            elif v=='A': v = 3
            else: v = 4
            d['p.'+k] = v
        return d
    except:
        return None

if __name__ == "__main__":
    # Load datasets
    df = db.getallAsDataFrame(transformData)

    # Focus on major parties in Tweede Kamer
    cdf = filter(df[df.house=='commons'], parties=['cda','d66','gl','pvda','pvdd','pvv','sgp','sp','vvd','grkh','cu','50plus'])

    # (1) Over all time
    dmtxAllTime = distMtx(cdf)
    distMtxToTableImage(dmtxAllTime, file='alltime.png')

    # (2) Over periods of one year
    for year in xrange(1994,2013):
        ydf = filter(cdf, from_date=datetime(year, 1, 1), to_date=datetime(year+1, 1, 1))
        distMtxToTableImage(distMtx(ydf), file=str(year)+'.png')
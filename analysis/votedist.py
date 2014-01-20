import os
import sys
sys.path.insert(0,os.getcwd())

import pandas as pd
from datetime import datetime
import collections
from operator import itemgetter
from data import db

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

def distMtx(df, tofile = ''):
    parties = [x for x in df.columns.tolist() if x.startswith('p.')]
    dist = [[(0,0) for x in xrange(len(parties))] for y in xrange(len(parties))]
    mtx = None
    for x in xrange(len(parties)):
        for y in xrange(len(parties)):
            tdf = df[pd.notnull(df[parties[x]]) * pd.notnull(df[parties[y]])]
            num = len(tdf)
            if x==y:
                dist[y][x] = (0,num)
                continue
            if x > y:
                dist[y][x] = dist[x][y]
                continue
            if num==0:
                dist[y][x] = (-1,0)
                continue

            print str(x) + ", " + str(y) + " [len=" + str(num) + "]"

            # Calculate total distance (and save number of shared votes)
            dst = float(sum(abs(tdf[parties[x]] - tdf[parties[y]])))/num
            dist[y][x] = (dst, num)

        # Update distance matrix
        if tofile != '':
            mtx = pd.DataFrame(dist)
            mtx.columns = map(lambda x: x[len('p.'):], parties)
            distMtxToHTML(mtx, tofile + ".html")
            distMtxToCSV(mtx, tofile + ".csv")

    return mtx

def distMtxToCSV(mtx, file):
    s = ';' + ';'.join(mtx.columns) + '\n' + '\n'.join( [ (mtx.columns[i] + ';' + 
            ';'.join(map(lambda x: str(x), mtx.iloc[i]))) for i in xrange(len(mtx.columns)) ] )
    f = open(file, "w")
    f.write(s)
    f.close()

def distMtxToHTML(mtx, file):
    s = ('<html><head><style>'
         'td { text-align: center } \n '
         'a { text-decoration: none; color: inherit; } '
         '</style></head>' 
         '<body><table cellpadding="4"><tr><th></th><th>' + '</th><th>'.join(mtx.columns) + '</th></tr>')
    m = float('-inf')
    for r in mtx:
        m = float(max(m, max(mtx[r], key=itemgetter(0))[0]))
        
    for i in xrange(len(mtx.columns)):
        s += '<tr><td>' + mtx.columns[i] + '</td>' + ''.join(
            ['<td align="center" '+
                 'style="background:rgb('+ ','.join([str(0 if m==0 else unicode(int(255.0*x[0]/m)))]*3) +');' + 
                        'color:' + ('white' if (x[0] < 0.5*m) else 'black') + ';">'+
            '<a href="#" title="Calculated from '+ str(x[1]) +' shared votes.">' + '{:1.3f}'.format(x[0]) + '</a>' +
            '</td>' for x in mtx.iloc[i]]) + '</tr>'
    s += '</table></body></html>'
    
    f = open(file, "w")
    f.write(s)
    f.close()

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
        # Category is optional
        if 

        return d
    except:
        return None

if __name__ == "__main__":
    # Load datasets
    arr = [x for x in map(transformData,db.getall()) if x != None]
    df = pd.DataFrame(arr)

    # Focus on major parties in Tweede Kamer
    cdf = filter(df[df.house=='commons'], parties=['cda','d66','gl','pvda','pvdd','pvv','sgp','sp','vvd','grkh','cu','50plus'])

    # (1) Over all time
    dmtxAllTime = distMtx(cdf, tofile="output/mtx")
    
    # (2) Over periods of one year
    for year in xrange(1994,2013):
        ydf = filter(cdf, from_date=datetime(year, 1, 1), to_date=datetime(year+1, 1, 1))
        distMtx(ydf, tofile="output/mtx-"+str(year))
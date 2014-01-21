import scipy
import pylab
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# =============================================================================
# Print vote distance information to CSV
# =============================================================================

def distMtxToCSV(mtx, file):
    # DOESN'T WORK YET!
    s = ';' + ';'.join(mtx.columns) + '\n' + '\n'.join( [ (mtx.columns[i] + ';' + 
            ';'.join(map(lambda x: str(x), mtx.iloc[i]))) for i in xrange(len(mtx.columns)) ] )
    f = open(file, "w")
    f.write(s)
    f.close()

# =============================================================================
# Print vote distance information to CSV
# =============================================================================

def distMtxToHTML(mtx, file):
    # DOESN'T WORK YET!
    actors = mtx['actors']
    dist = mtx['distances']
    numobs = mtx['num_obs']

    s = ('<html><head><style>'
         'td { text-align: center } \n '
         'a { text-decoration: none; color: inherit; } '
         '</style></head>' 
         '<body><table cellpadding="4"><tr><th></th><th>' + '</th><th>'.join(actors) + '</th></tr>')
    m = float('-inf')
    for r in mtx:
        m = float(max(m, max(dist[r])))
        
    for i in xrange(len(actors)):
        s += '<tr><td>' + actors[i] + '</td>' + ''.join(
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
# Visualize data using 2D multidimensional scaling
# =============================================================================

def distMtxToTableImage(mtx, file):
    actors = mtx['actors']
    dist = np.asarray(mtx['distances'])
    numobs = mtx['num_obs']

    labels = [x for x in xrange(len(actors))]
    txtlabels = [str(x) + ' = ' + actors[x] for x in xrange(len(actors))]

    fig, ax = plt.subplots()

    ax.xaxis.set_major_formatter(ticker.NullFormatter())
    ax.xaxis.set_minor_locator(ticker.FixedLocator([x+0.5 for x in xrange(len(actors))]))
    ax.xaxis.set_minor_formatter(ticker.FixedFormatter(labels))
    
    ax.yaxis.set_major_formatter(ticker.NullFormatter())
    ax.yaxis.set_minor_locator(ticker.FixedLocator([x+0.5 for x in xrange(len(actors))]))
    ax.yaxis.set_minor_formatter(ticker.FixedFormatter(labels))

    heatmap = ax.pcolor(dist, cmap='RdGy_r')
    
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    
    extra = [plt.Rectangle((0, 0), 1, 1, fc="w", fill=False, edgecolor='none', linewidth=0) for x in xrange(len(actors))]
    leg = ax.legend(extra, tuple(txtlabels), loc='center left', bbox_to_anchor=(1, 0.5), borderaxespad=0, )
    leg.draw_frame(False)

    fig.savefig(file)

def distMtxToMDSGraph(mtx):
    actors = mtx['actors']
    dist = mtx['distances']
    numobs = mtx['num_obs']



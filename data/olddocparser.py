# ===================================================================
# Parse votes as far back as 1814
#    - Take the politicalmashup dataset as a starting point
#    - Insert markers in the text indicating words signaling e.g. 
#      the beginning of a VOTE_PRE
#    - Save tuples of (PoliticalMashup Fragment ID, Marker, Text)
# ===================================================================

from __future__ import print_function

# FOR DEBUG PURPOSES ONLY:
# There's a less hack-y way of fixing this
import sys
sys.path.append(os.getcwd())
# /END FOR DEBUG PURPOSES ONLY

import db
from copy import copy

from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from fuzzysearch import find_near_matches_with_ngrams
import difflib

from unidecode import unidecode
import xmltodict

import codecs
import string
import regex as re
import json
import numpy
import traceback

# =======================================================================================
# Save generated content
# =======================================================================================

def textToHTML(texts, id=''):
    str  = "<html><head></head><body>"
    str += "<table><tr><th>PoliticalMashup #id</th><th>Marker</th><th>Text</th></tr>"

    for t in texts:
        str += "<tr><td>" + t[0] + "</td><td>" + t[1] + "</td><td>" + t[2] + "</td></tr>"

    str += "</table></body></html>"

    try:
        with codecs.open('../html/'+id+'.html', 'w', 'utf-8') as f:
            f.write(str)
    except:
        print("Error writing file: " + id)

# =======================================================================================
# STATICLY DEFINED MARKER PATTERNS DERIVED FROM MANUAL INSPECTION OF PROCEEDINGS
# =======================================================================================

STATIC_MARKERS = \
          [
           #('REJECTED','(in stemming gebragt,)?(wordt |worden )?met ([a-z0-9]){1,6} (tegen )?([a-z0-9]){1,6} stem(men)? verworpen', 5),
           #('ACCEPTED','(in stemming gebragt,)?(wordt |worden )?met ([a-z0-9]){1,6} (tegen )?([a-z0-9]){1,6} stem(men)? (aangenomen|goedgekeurd)', 5),
           
           #('REJECTED','(in stemming gebragt,)?(wordt |worden )?(zonder be raadslaging en )?(zonder|met)?(algemeene stemmen|hoofdelyke stemming|hoofdelijke stemming) verworpen', 5),
           #('ACCEPTED','(in stemming gebragt,)?(wordt |worden )?(zonder be raadslaging en )?(zonder|met)?(algemeene stemmen|hoofdelyke stemming|hoofdelijke stemming) (aangenomen|goedgekeurd)', 5),
           
           ('REJECTED','(stemmen|stem) verworpen', 3),
           ('ACCEPTED','(stemmen|stem) (aangenomen|goedgekeurd)', 3),
           
           ('REJECTED','(algemeene stemmen|hoofdelyke stemming|hoofdelijke stemming) verworpen', 3),
           ('ACCEPTED','(algemeene stemmen|hoofdelyke stemming|hoofdelijke stemming) (aangenomen|goedgekeurd)', 3),
           

           ('TOPIC','(deze |het )?amendement(en)?( van)?', 2),
           ('TOPIC','(deze |het )?wetsontwerp(en)?( van)?', 2),
           ('TOPIC','(deze |het )?ivets-ontwerp(en)?', 2),
           ('TOPIC','(deze |het )?wets-ontwekpen(en)?', 2),
           ('TOPIC','(deze |het )?wets-ontu-erp(en)?', 2),
           ('TOPIC','(dit |het |de )?onderart',1),
           ('TOPIC','(dit |het |de )?ond-art',1),
           ('TOPIC','(dit |het |de )?ond.-art',1),
           ('TOPIC','(dit |het |de )?ond.-arttt',1),
           ('TOPIC','(dit |het |de )?oxd.-artt',1),
           ('TOPIC','(dit |het |de )?osd.artt',1),
           ('TOPIC','(dit |het |de )?artt',0),
           ('TOPIC','(dit |het |de )?art. ([0-9]){1,3}',1),
           ('TOPIC','(dit |het |de )?akt. ([0-9]){1,3}',1),
           ('TOPIC','(dit |de )?motie(s)?',1),
           ('TOPIC','(dit |het |de )?abt',0),
           ('TOPIC','(dit |het |de )?(eenig )?artikel(en)?', 2),
           
           # BREAKs serve to increase structure in the document, and prevent erroneous classifications, 
           # but currently no information is extracted from these 'breaks'
           ('BREAK','de notulen van het verhandelde ia de vorige zitting worden gelezen en goedgekeurd', 5),
           ('BREAK','de (algemeene )?beraadslaging wordt gesloten', 1),
           ('BREAK','dienovcieenkomstig wordt besloten', 4),
           ('BREAK','maakt een onderwerp van beraadslaging uit',3),
           ('BREAK','than s is aan de orde', 2),
           ('BREAK','thans is aan de orde', 2),
           ('BREAK','alsnu is aan de orde', 2),
           ('BREAK','aan de orde is', 2),
           ('BREAK','voortzetting der behandeling',2),
           ('BREAK','voortzetting', 1),

           # Decreasing specificity and error tolerance to prevent greedy match 'damaging' name records
           ('ABSENT' ,'bij deze stemming (waren|was) afwezig', 3),
           ('ABSENT' ,'afwezig', 0),
           ('ABSENT' ,'afwezig', 2),
           
           # Decreasing specificity and error tolerance to prevent greedy match 'damaging' name records
           ('PRESENT','bij deze stemming (waren|was) (tegenwoordig|ivgenwoordig)', 3),
           ('PRESENT','(tegenwoordig|ivgenwoordig)', 0),
           ('PRESENT','(tegenwoordig|ivgenwoordig)', 2),
           
           # Decreasing specificity and error tolerance to prevent greedy match 'damaging' name records
           ('INFAVOR','voor (hebben|heeft) gestemd', 3),
           ('AGAINST','tegen (hebben|heeft) gestemd', 3), 
           
           ('VOTE_PRE','Bij deze stemming (waren|was)', 3),
           ('VOTE_PRE', '(hebben|bobben) gestemd', 1),

           # IGNOREs prevent text elements mixed with e.g. names from being parsed as such
           ('IGNORE','(([0-9]){0,2} leden, )?te weten', 2),
           ('IGNORE','(de lieer|de heer)(en)?',1)
          ]

ACTORS = []
ACTORS_INITIALS = []
ACTORS_SCORE = []

ACTOR_MAXLEN = 0
NAMES = {}

# =======================================================================================
# Load metadata
# =======================================================================================

def loadNamesMarkers():
    global MARKERS
    global ACTOR_MAXLEN
    with open('../data/list-members.xq.xml', 'rb') as xmlfile:
        d = xmltodict.parse(xmlfile, dict_constructor=dict)
        for member in d['result']['members']['member']:
            # Get name information
            lastname = unidecode(member['name']['last']).lower()
            initials = unidecode(member['name']['initials']).lower() if 'initials' in member['name'] else ''
            # Some last names consist of two or more names, only one of which gets mentioned in the proceedings
            # This confuses the approximate string matching algorithm, so manually add the 'shortened' version 
            # of the last name to the list of actors, i.e. split all names at 'van' (ENG: 'of')
            if len(re.findall('(\s|^)van\s', lastname)) >= 2:
                # Get indexes to split at
                idx = [x.start() for x in re.finditer('(\s|^)van\s', lastname)]
                extra = [y.strip() for y in [''.join(x) for x in numpy.split(list(lastname), idx)] if len(y)>0]
                for x in extra:
                    ACTORS.append(x)
                    ACTORS_INITIALS.append(initials)
                    # Because this is a 'derived' name, give it a slightly lower score, which will cause originally 
                    # existing names to get preference when the match is exact
                    ACTORS_SCORE.append(0.98) 
            # Save in memory
            ACTORS.append( lastname )
            ACTORS_INITIALS.append( initials )
            ACTORS_SCORE.append(1.0)

    ACTOR_MAXLEN = max([len(ACTORS[x]+ACTORS_INITIALS[x]) for x in xrange(len(ACTORS))])

def loadNamesMapping():
    global NAMES
    try:
        with open('../data/names-mapping.json', 'r') as f:
            NAMES = json.load(f)
    except:
        NAMES = {}

def saveNamesMapping():
    global NAMES
    with open('../data/names-mapping.json', 'w') as f:
        json.dump(NAMES, f)

# =======================================================================================
# Insert content markers in the text
# =======================================================================================

def mark(txtarr, markers = STATIC_MARKERS):
    texts = copy(txtarr)
    # Search for all markers
    for imarker in xrange(len(markers)):
        marker = markers[imarker]
        i = 0
        # Print progress
        print('Marked ' + str(imarker)+'/'+str(len(markers)) + ', marking: ' + marker[1][0:30], end='\r')
        # Search through all text fragments
        while i < len(texts):
            # Already marked? If so, skip
            if texts[i][1] != '':
                i += 1
                continue
            # Find markers in text
            matches = []
            try:
                # lowercase both strings and convert numbers to _'s
                rex = '('+marker[1].lower()+'($|[ \t\r\n\f.!,;:])){e<='+str(marker[2])+'}'
                s1 = texts[i][2].lower()
                matches = re.search(rex, s1).spans()
            except:
                pass

            if len(matches) > 0:
                # Only process one match at a time
                match = matches[0]
                s1 = (texts[i][1],    ''     , texts[i][2][:match[0]])
                s2 = (texts[i][1], marker[0] , texts[i][2][match[0]:match[1]])
                s3 = (texts[i][1],    ''     , texts[i][2][match[1]:])
                texts.pop(i)
                texts.insert(i, s3)
                texts.insert(i, s2)
                texts.insert(i, s1)
                # While loop will reprocess s1 with current marker...
            else:
                # Go to next text fragment
                i += 1
    # Done parsing document!
    return texts

# =======================================================================================
# Check if text contains actors
# =======================================================================================

def getActors(txt, checkOnly=False):
    global NAMES

    if len(txt.strip()) == 0: return []
    
    # Split string based on punctuation (except at ' and "); due to OCR errors, some comma's are parsed as periods or '<'s, etc.
    # CF: http://stackoverflow.com/questions/1198512/split-a-list-into-parts-based-on-a-set-of-indexes-in-python
    idxp = [i for i, ltr in enumerate(txt) if ltr in string.punctuation and ltr not in ["'",'"','-']]
    if len(idxp)==0: return []
    # Splitting at periods, however, does not work, as some names contain initials, e.g. (j . k. van goltstein)
    # EG: : keistens, godefroi, van bosse, van kerkwijk . taets van arnerongen , j . k. van goltstein , van beyma thoe kingma, w. van goltstein en lycklama si nyeholt.
    idx = [idxp[0],] 
    for i in xrange(1,len(idxp)):
        if (idxp[i]-idxp[i-1]) >= 5:
            idx.append(idxp[i])
    # Split string based on these indices
    t = [''.join(x) for x in numpy.split(list(txt), idx)]
    # Remove empty (or just containing punctuation) categories
    t = [x for x in t if len(x)>2]
    # Assume the remaining punctuation is the dots of initials, but the dots might have been misinterpreted due to OCR,
    # so convert all punctuation to [ . , - , ' ]
    t = [''.join([(y if y not in string.punctuation else 
                   ("'" if y in ['"',"'"] else 
                    ('-' if y in ['-','_'] else '.'))) 
                     for y in list(x)]) for x in t]
    # Empty list?
    if len(t)==0: return (False if checkOnly else [])
    # Split at 'en' (ENG: 'and') at end
    names = t[:-1] + t[-1].split(' en ')
    # recognized names
    recnames = []

    for name in names:
        best = None
        # Print progress
        print('Searching for name: '+(name[0:50]), end='\r')
        # Make sure this isn't the 'president' tag
        res = re.search('(voorzitter){e<=1}', name)
        if res != None:
            best = ['president',]
        else:
            # If this text fragment wasn't a series of names, the 'name' variable might be extremely long, meaning 
            # it cannot possibly be a name
            if len(name) > ACTOR_MAXLEN + 3: continue
            # If we're merely interested in whether this row has names, filter out the shortest names to prevent
            # fake hits
            if checkOnly and len(name) < 8: continue
            # Get best
            if name in NAMES:
                best = [NAMES[name], ]
            else:
                # Does 'name' have initials? (If we're only checking, don't bother using the more detailed initials match)
                # REGEX: START OF STRING -> optional whitespace or punctuation -> 'a. b.' etc. -> 'Lastname'
                res = re.match('^((\s|\p{P})*[a-z]\s*\.)+', name)
                if res != None and not checkOnly:
                    # Get matched initials
                    initials = ''.join([x[0]+'.' for x in re.findall('[a-z]\s*\.',name)])
                    # Yes, name has initials: get best matches, and then weigh their scores with initials-fit-scores
                    best10 = difflib.get_close_matches(name, ACTORS, n=10, cutoff=0)
                    bests = 0
                    bestidx = ''
                    for ba in best10:
                        idxs = [i for i, x in enumerate(ACTORS) if x == ba]
                        for idx in idxs:
                            score = 0.2 * difflib.SequenceMatcher(None, ACTORS_INITIALS[idx], initials).ratio() \
                                  + 0.8 * difflib.SequenceMatcher(None, ACTORS[idx]         , ba).ratio()
                            score *= ACTORS_SCORE[idx]
                            if score > bests:
                                bests = score
                                bestidx = idx
                    # Store best actor
                    best = [ (ACTORS_INITIALS[bestidx] + ' ' + ACTORS[bestidx]) , ]
                else:
                    # If not, just pick the best match
                    best = difflib.get_close_matches(name, ACTORS, n=1, cutoff=(0.8 if checkOnly else 0))
                
        if len(best) > 0:
            # Insure minimum match at arbitrary (although it seems to work) threshold of 50%:
            r = 1.0 if name in NAMES else difflib.SequenceMatcher(None, name, best[0]).ratio()
            if r > 0.5:
                if checkOnly:
                    # Don't use the president tag as evidence of a vote
                    if best[0] != 'president': return True
                else:
                    # Store name in database
                    NAMES[name] = best[0]
                    recnames.append(best[0])
    # Nothing found!
    if checkOnly:
        return False
    else:
        return recnames
    
# =======================================================================================
# Search for actors in rows (dir= +- 1)
# =======================================================================================

# CACHE ROWS ALREADY INSPECTED
ACTORS_CACHE_TXT = ''
ACTORS_CACHE = {}

def searchForActors(texts, i, dir=1):
    global ACTORS_CACHE_TXT, ACTORS_CACHE
    if ACTORS_CACHE_TXT != texts: 
        # Reset Cache
        ACTORS_CACHE_TXT=texts
        ACTORS_CACHE = {}
    # Loop through adjacent rows
    row = i + dir
    actors = []
    text = ''
    while row >= 0 and row < len(texts):
        print('Searching for actors on row '+str(row), end='\r')
        # Stop search when certain rows are found
        if texts[row][1] in ['BREAK','ABSENT','INFAVOR','AGAINST','TOPIC','VOTE_PRE']:
            break
        # Ignore this row?
        if not texts[row][1] in ['IGNORE']:
            # Row present in cache?
            ractors = []
            if row in ACTORS_CACHE and ACTORS_CACHE[row]:
                ractors = ACTORS_CACHE[row]
            else:
                hasActors = getActors(texts[row][2], checkOnly=True)
                if hasActors:
                    # Get actors
                    ractors = getActors(texts[row][2])
                    # Store in cache
                    ACTORS_CACHE[row] = ractors
            # Actors found?
            if len(ractors) > 0:
                actors += ractors
                if dir==1:
                    text = text + texts[row][2]
                else:
                    text = texts[row][2] + text
        # Next row
        row += dir
        # Limit number of rows
        if abs(i-row) > 8: break
    # return results
    print('Done searching for actors!', end='\r')
    return {'actors': actors, 'text': text}

# =======================================================================================
# Extract voting information based on validated markers in text
# =======================================================================================

def extract(texts):
    votes = []
    emptyvote = {'pmids':[], 'topic': '', 'infavor': [], 'against':[], 'absent':[], 'decision':''}
    curvote = copy(emptyvote)
    lastMarker = ''
    lastvoteDir = ''

    for itxt in xrange(len(texts)):
        txt = texts[itxt]
        # BREAK encountered? 
        if txt[1]=='BREAK':
            # Store vote if 'decision' and 'topic' had been parsed
            if curvote['topic']!='' and curvote['decision']!='':
                votes.append(curvote)
            # Reset
            curvote = copy(emptyvote)
        
        elif txt[1]=='TOPIC':
            # voting info present? If so, start new vote for this topic 
            if curvote['topic']!='' and curvote['decision']!='':
                votes.append(curvote)
                curvote = copy(emptyvote)
            # Save topic
            curvote['topic'] += txt[2]

        elif txt[1]=='':
            # As long as no 'decision' has been parsed yet, keep adding to the topic
            if curvote['topic']!='': curvote['topic'] += txt[2]
            
        elif txt[1] in ['ACCEPTED','REJECTED']:
            curvote['decision'] = txt[1].lower()
        
        elif txt[1] in ['INFAVOR','AGAINST','ABSENT']:
            # Search for nearby actors
            s1 = searchForActors(texts, itxt, 1)
            s2 = searchForActors(texts, itxt, -1)
            # Remove actors already included in 'infavor' or 'against' columns;
            # this automatically makes the algorithm robust against changing order 
            # of 'names' vs. 'vote markers' (e.g. 'voor hebben gestemd')
            alln = ([] if not 'actors' in curvote['infavor'] else curvote['infavor']['actors']) + \
                   ([] if not 'actors' in curvote['against'] else curvote['against']['actors']) + \
                   ([] if not 'actors' in curvote['absent']  else curvote['absent']['actors']) 
            s1['actors'] = [x for x in s1['actors'] if (x not in alln)]
            s2['actors'] = [x for x in s2['actors'] if (x not in alln)]
            # Save in records
            if len(s1['actors'])>0:
                curvote[txt[1].lower()] = s1
            elif len(s2['actors'])>0:
                curvote[txt[1].lower()] = s2
        # Save PoliticalMashup id
        if txt[0] != '' and txt[0] not in curvote['pmids']: 
            curvote['pmids'].append(txt[0])

    # Add last vote if it has the necessary info
    if curvote['topic']!='' and curvote['decision']!='': 
        votes.append(curvote)
    # For now, delete all votes that don't include either INFAVOR or AGAINST
    votes = [x for x in votes if ('actors' in x['infavor']) or ('actors' in x['against'])]
    # Done!
    return votes


# =======================================================================================
# Recursively transform PoliticalMashup document to tuples of 
#    (PoliticalMashup Fragment ID, Marker, Text) with empty markers
# =======================================================================================

def toTextArray(d):
    if '#text' in d:
        if '@pm:id' in d:
            s = unidecode(d['#text']).lower()
            if len(s)>0:
                yield (d['@pm:id'], '', s)
    for k in d:
        if isinstance(d[k], list):
            for i in d[k]:
                if isinstance(i, dict):
                    for j in toTextArray(i):
                        yield j
        elif isinstance(d[k], dict):
            for j in toTextArray(d[k]):
                yield j

# =======================================================================================
# Process all documents in database
# =======================================================================================

if __name__ == "__main__":
    print("Loading document IDs")
    docs_all = db.getids(type='document', size=30000)
    docs_parsed = db.getids(type='document_parsed', size=30000)
    docs = [x for x in docs_all if not x in docs_parsed]

    print("Loading names mapping and names markers")
    # Load politician/party markers
    loadNamesMapping()
    loadNamesMarkers()
    
    for idoc in xrange(len(docs)):
        doc = docs[idoc]
        try:
            print("Processing doc ("+str(idoc)+"/"+len(docs)+"): " + str(doc))
            # Get array of unmarked text
            text = list(toTextArray(db.get(doc)))
            # Mark the text with keywords
            mtext = mark(text)
            # Save HTML version for debug purposes
            textToHTML(mtext, id=doc)
            # Extract the information based on keywords
            info = extract(mtext)
            # Save info back in database
            with open('../html/'+doc+'.json', 'w') as f:
                json.dump(info, f)
            # Intermediately save names mapping
            saveNamesMapping()
            db.store({'index': doc, 'type': 'document_parsed',
                      'parser': info})
        except:
            print(traceback.format_exc())


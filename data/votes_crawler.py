import xml.etree.ElementTree as ET
import csv
import re
from data import db

from data import cache
    
# ===================================================================
# DOWNLOAD ALL MOTIONS AND VOTES BY HOUSE OF REPRESENTATIVES 
#    (AKA. De Tweede Kamer)
# ===================================================================

def downloadHouseOfReps():
    page = 0

    # Create database table
    db.setup()
    
    # Iterate over all search results
    while True:
        url = ("http://www.tweedekamer.nl/kamerstukken/index.jsp?"
              "clusterName=Stemmingsuitslagen&fld_prl_kamerstuk=Stemmingsuitslagen&"
              "fld_tk_categorie=Kamerstukken&Type=Kamerstukken&"
              "qry=%2A&srt=date%3Adesc%3Adate&sta=" + str(1+page*15))
              
        navtree = cache.downloadHTML(url)
        hrefs = [ x["href"] for x in navtree.select(".search-result-list a") ]
        
        httpbase = "http://www.tweedekamer.nl"

        for href in hrefs:
            try:
                tree = cache.downloadHTML(httpbase+href, 30)
            except:
                continue

            # Get info
            for r in tree.select(".vote-results li"):
                # ===================================================
                # PARSE MOTION
                # ===================================================
                d = {"number": "", "title": "", "submitter": "", 
                     "submitter_party": "", "date": "", "decision":"PARSE_ERROR", 
                     "decision_txt":"", "votes":{}}
                try:
                    d["number"]          = r.select(".search-result-properties p")[0].string
                except:
                    pass
                try:
                    d["title"]           = re.sub(r'\s+', ' ', r.select("h3 a")[0].string)
                except:
                    pass
                try:
                    d["submitter"]       = r.select(".submitter a")[0].string
                except:
                    pass
                try:
                    d["submitter_party"] = r.select(".submitter a")[1].string
                except:
                    pass
                try:
                    d["date"] = r.select(".date")[0].string
                    d["date"] = d["date"].replace("januari","january")
                    d["date"] = d["date"].replace("februari","february")
                    d["date"] = d["date"].replace("maart","march")
                    d["date"] = d["date"].replace("mei","may")
                    d["date"] = d["date"].replace("juni","june")
                    d["date"] = d["date"].replace("juli","july")
                    d["date"] = d["date"].replace("augustus","august")
                    d["date"] = d["date"].replace("oktober","october")
                    d["date"] = datetime.strptime(d["date"],"%d %B %Y")
                except:
                    pass
                try:
                    d["decision_txt"]    = r.select(".result span")[0].string
                except:
                    pass
                try:
                    d["links"]           = "\n".join([httpbase+''.join(x["href"].split()) for x in r.select(".links a")])
                except:
                    pass
                
                docid = db.insertDocument(d)
                
                # ===================================================
                # PARSE VOTES
                # ===================================================
                headers = []
                lv = None

                for hd in r.select(".statistics th"):
                    h = hd.string.lower()
                    if h=="voor":
                        h = "Y"
                    elif h=="tegen":
                        h = "N"
                    elif h=="niet deelgenomen":
                        h = "A"
                    elif h=="vergissing":
                        h = "M"
                    headers.append(h)

                for tr in r.select(".statistics tbody tr"):
                    cols = tr.select("td")
                    v = {'voter':''}
                    # Save motion id
                    v["document"] = d["id"]
                    # Get party info:
                    # Make sure party info is present on current table row, 
                    # otherwise use last party
                    if len(tr.select("td.fractie")) > 0:
                        v["party"] = cols[0].string
                        try:
                            v["party_seats"] = int(cols[1].string)
                        except:
                            pass
                    else:
                        v["party"] = lv["party"]
                        v["party_seats"] = lv["party_seats"]
                        # Parse individual politician 
                        v["voter"] = cols[1].string

                    # Parse votes (columns >2 contain voting info)
                    for j in range(2, len(cols)):
                        if len(cols[j].select("img")) > 0:
                            # How many?
                            try:
                                # Individual or party?
                                if v['voter'] != '':
                                    v[headers[j]] = 1
                                else:
                                    v[headers[j]] = int(cols[j].select("img")[0]["width"])
                            except:
                                pass
                        else:
                            v[headers[j]] = 0
                    
                    # Save most recent column
                    lv = v
                    
                    d['votes'][v['party'] if v['voter']=='' else v['voter']] = v
        page += 1

        # More items left?
        if len(navtree.select("a.right")) == 0:
            break
        else:
            print "to results page: "+str(page)
    
    # Close database
    db.close()

if __name__ == "__main__":
    downloadHouseOfReps()

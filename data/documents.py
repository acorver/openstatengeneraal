import db
import cache
import xmltodict

# ===================================================================
# This file downloads information on all documents (i.e. motions + 
# legislation) in the documents database. Selected fields are then 
# stored in the database
# EXAMPLE LINK: https://zoek.officielebekendmakingen.nl/kst-33129-30.xml
# ===================================================================

if __name__ == "__main__":
    docs = db.getids()
    for doc in docs:
        url = 'https://zoek.officielebekendmakingen.nl/kst-' + doc + '.xml'
                
        # Download XML document
        xml = cache.download(url, 30)
        if "pagina die u zocht kon niet worden gevonden" in xml:
            # 404 page
            print "Not Found: " + doc
            continue

        # Parse XML
        d = None
        try:
            d = xmltodict.parse(xml, dict_constructor=dict)
        except:
            print "Error parsing document: " + doc
            d = {'xml': xml}

        # Save in database
        db.store({'index': doc, 'type': 'vote', 'obxml': d})
        print "Successfully added xml-info to database: " + doc
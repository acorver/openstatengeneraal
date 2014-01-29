# This script parses the list of members of the house of representatives, which can be found here:
#     http://www.parlement.com/id/vg7zoaah7lqb/selectiemenu_tweede_kamerleden
#     http://www.parlement.com/id/vg7zoaah7lqb/selectiemenu_tweede_kamerleden?&u=%u2713&dlgid=jg0gyk622u0g8&s01=jg0gyk5mp624yq&v07=&v11=&v12=&v02=&v05=&v06=&Zoek=Ok&Reset=Reset

import cache
import db
import regex as re

if __name__ == "__main__":
    html = cache.openHTML('../data/parlement.nl-list-politicians.htm')

    politicians = [x.text for x in html.select("div#main_container article .seriekeuze a")]
    membership  = [''.join([unicode(y) for y in x.contents]) for x in 
                    html.select("div#main_container article div") if len(x.select("a"))==0]
    
    data = {}

    for i in range(len(membership)):
        for l in membership[i].split("<br>"):
            party = l[(l.find("(")+1): l.rfind(")")]
            start = ""
            end = ""

            if "t/m" in l:
                start = l[0 : l.find("t/m")]
                end   = l[(l.find("t/m")+3) : l.find("(")]
            else:
                start = l[(l.find("vanaf") + 5) : l.find("(")]

            politician = politicians[i].strip()
            politician = politician[0:politician.find("(")]

            initials = ''.join([x[0]+'.' for x in re.findall('[a-zA-Z]\s*\.',politician)])
            lastname = politician.replace(initials,'').strip()

            # Create info struct
            if not politician in data:
                data[politician]= { 'initials': initials, 'lastname': lastname, 'party': party, 'inoffice': []}
            # Add inoffice moment
            data[politician]['inoffice'].append( (start, end) )
            
        # Insert all data into database
        for d in data:
            db.store({'index': d, 'type': 'actor', 'actor': data[d]})

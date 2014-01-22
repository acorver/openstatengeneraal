import os
import xmltodict
import db

if __name__ == "__main__":
    base = "../data/sgd/"
    counter = 0
    for file in os.listdir(base):
        if file.endswith(".xml"):
            with open(base + file, 'rb') as xmlfile:
                try:
                    idx = file
                    d = xmltodict.parse(xmlfile, dict_constructor=dict)
                    db.store({'index': idx, 'type': 'document', 'politicalmashup': d})
                    counter += 1
                    if (counter%500)==0:
                        print "Processed and stored "+str(counter)+" files."
                except:
                    print "Error storing file: " + file
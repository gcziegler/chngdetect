'''
Created on Oct-07-2017
@author: guillermo.ziegler
Version 0.01

* Library de funciones
'''

def add2msg(content, site, url, code, diff):
    if str(code):
        content = content + """<h3>""" + site + """</h3>""" 
        content = content + """\
        <p>
            Error reading  """ + url  + """<br>\
            URL returned """ + str(code) + """<br>\
        </p>
        """
    else:
        content = content + """\
        <br>\
        <h3>""" + site + """</h3>\
        URL:""" + url + """<br>\
        Changes in content. See """ + site + """.html<br>\
        """
        #content = content + diff
    return(content)

def extract_visible_txt(response):

    # Import BeautifulSoup (to parse what we download)
    from bs4 import BeautifulSoup

    # *** START *** New Code to extract visible text from pages
    soup = BeautifulSoup(response.text, "lxml") #html.parser
    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
    content = soup.getText() 
    #remove empty lines from content
    #while '\n\n' in content:
    #    content=content.replace('\n\n','\n')
    # *** END *** New Code to extract visible text from pages
    return(content)

def create_file(fname, content):
    with open(fname,"w", encoding="utf-8") as f:
        f.write(content)
    return

def filldict(dict_file):
    #To read CSV file for dict
    import csv
    
    url_dict  = {}  #url_dict  
    with open(dict_file, 'r') as f:
        readCSV = csv.reader(f, delimiter=',')
        for line in readCSV:
            name = line[0]
            url = line[1]
            url_dict[name] = url
    return(url_dict)

def chklogsize(fname):
    import os
    statinfo = os.stat(fname)
    return(statinfo.st_size)


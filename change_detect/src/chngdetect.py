'''
Created on Oct 7, 2017

@author: guillermo
'''

'''
LIBRARIES
'''
#My Lib First
from lib.chngdtct import *

#Logging file
import logging
#For System Exit
import sys
#date time
import datetime
#Config Parse to read conf file
import configparser
#To read CSV file for dict
#import csv
#Import para mover y rename files
import os
# Import requests (to download the page)
import requests
# Import BeautifulSoup (to parse what we download)
#from bs4 import BeautifulSoup
#Import Path handling lib
from pathlib import Path
#Import library for diffs
import difflib
#library for email
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

'''
LEER Y APLICAR CONFIGURACION
'''
CNF_FNAME = Path('.', 'config.conf')

if CNF_FNAME.exists() == False:
    logging.error("CONFIG File DOES NOT exist. Terminating!!")
    sys.exit("CONFIG File DOES NOT exist. Terminating")

config = configparser.ConfigParser(allow_no_value=True)
config.read(CNF_FNAME)

'''
CONFIGURAR LOGGING
'''
LOG_FILE = config['logging']['file']
LOG_FORM = config['logging']['format']
LOG_LVL = config['logging']['level']
LOG_SZE = config['logging']['maxsize']

logsize = chklogsize(LOG_FILE)
if logsize >= int(LOG_SZE):
    newname, extension = os.path.splitext(LOG_FILE)
    newname = newname  + datetime.datetime.now().strftime("%Y%m%d%H%M") + extension
    os.rename(LOG_FILE, newname)  

logging.basicConfig(filename=LOG_FILE,format=LOG_FORM,level=LOG_LVL)

logging.info('********************************************************************************')
logging.info('*** STARTING PROCESS ***')
logging.info('********************************************************************************')

logging.info('Reading and applying Configuration file')

'''
CONFIGURACION CSV CON LISTA URLS A REVISAR
'''
#Dict File
URLS_CSV = config['data']['urls_CSV']
URLS_CSV_FLDR = config['data']['urls_CSV_folder']

DATA_DIR_DICT = Path('.', URLS_CSV_FLDR)
DICT_FILE=URLS_CSV

DICT_FNAME = DATA_DIR_DICT.joinpath(Path(DICT_FILE).name)

#If DICT_FILE does NOT exist, stop execution with error
if DICT_FNAME.exists() == False:
    logging.error("Dictionary File DOES NOT exist. Terminating!!")
    sys.exit("Dictionary File DOES NOT exist. Terminating")

'''
CONFIGURACION BASELINE & TEMPO FILES
'''
#Baseline Files
BSLN_FILES_FLDR = config['data']['baseline_files_folder']
DATA_DIR = Path('.', BSLN_FILES_FLDR)
DATA_DIR.mkdir(exist_ok=True, parents=True)

#Tempo File
TEMPO_FILE = 'tempo.txt'
TEMPO_FNAME = DATA_DIR.joinpath(Path(TEMPO_FILE).name)

#remove tempo if exists
try:
    os.remove(TEMPO_FNAME)
except OSError:
    pass

#Diff Ratio
#Cuanto estoy dispuesto a tolerar de diferencia en la comparacion 0 a 1. Mas cerca de 1 mas parecidos son los archivos
DIFF_RATIO = float(config['diffs']['acceptable_ratio'])

#HTML Message
message_top = """\
<html>
    <head></head>
    <body>
"""
message_mid = ""
message_end = """\
    </body>
</html>
"""

'''
CONFIGURACION ATTACHMENT FILES
'''
#Attachments Folder
ATTCHMNT_FILES_FLDR = config['email']['attchmnts_folder']
ATTCHMNT_DIR = Path('.', ATTCHMNT_FILES_FLDR)
ATTCHMNT_DIR.mkdir(exist_ok=True, parents=True)

#Empty Attachments Dir for new pass
fileList = os.listdir(ATTCHMNT_FILES_FLDR)
for fileName in fileList:
    os.remove(ATTCHMNT_FILES_FLDR+"/"+fileName)

'''
Email Configuration
'''
#Email
EMAIL_TO = config['email']['to']
EMAIL_FROM = config['email']['from']
EMAIL_SBJ = config['email']['subject'] + " " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
EMAIL_SMTP = config['email']['smtp']
EMAIL_PORT = config['email']['port']    
EMAIL_USR = config['email']['usr']
EMAIL_PWD = config['email']['pwd']

'''
#URL REQUEST HEADER
'''
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}


chng_ndx = {}       #Stores sites with changes for TOC
rqterror_ndx = {}   #Stores URLs returning Request errors for TOC
acum_ratio = 0      #To calculate avg ratio
acum_checked_sites = 0  #To calculate avg ratio

logging.info('Loading URLs from CSV')
url_dict = filldict(DICT_FNAME)
logging.info('URLs Loaded - Starting Loop')

for each_site in url_dict:
    content = ''
    site = each_site
    url = url_dict[site]

    logging.info("Processing: %s => %s", site, url)
    
    logging.info("Checking web site")
    logging.info("Requesting: %s", site)
    response = requests.get(url, headers=headers)
    
    if response.status_code != requests.codes.ok:  # @UndefinedVariable
        logging.info("Error reading %s - URL Returned %s" % (site, response.status_code))
        logging.info("********************************************************************************")
        logging.info("Preparing Warning message for final report email")        
        #message_mid += add_error2msg(url, site, response.status_code, message_mid)
        #message_mid += add2msg(message_mid, site, url, response.status_code, "")
        logging.info("Email msg updated. Reading next URL from list")
        #chng_ndx.update({site:url})
        rqterror_ndx.update({site:url})
        continue #sigo con next URL
    
    logging.info("URL Returned OK Status %s", response.status_code)
    logging.info("Parsing Response and extracting content")
    content = extract_visible_txt(response)
    
    logging.info('Composing path and name for Baseline file')
    BASE_FILE = site + ".txt"
    BASE_FNAME = DATA_DIR.joinpath(Path(BASE_FILE).name)

    logging.info("Checking if Baseline file %s exists", BASE_FNAME)    
    if not BASE_FNAME.exists():
        logging.info("Creating baseline file from %s content", site)
        #create_baseline(BASE_FNAME, content)
        create_file(BASE_FNAME, content)
        logging.info("Baseline file for %s Created. Reading next site", site)
        logging.info("********************************************************************")     
        continue
    else: #Baseline EXISTS
        logging.info("Baseline file for %s DOES exist. Reading Baseline file", site)
        with open(BASE_FNAME, encoding="utf8") as bf:
            bsln_text = bf.read()    #.replace('\n\n','\n')
        
        logging.info("Setting content read from %s as tempo", site)
        tmp_text = content
        
        logging.info("Comparing Tempo vs Baseline file %s", BASE_FNAME)        
        s = difflib.SequenceMatcher(None, tmp_text, bsln_text)        
        ratio = s.real_quick_ratio()
        acum_ratio += ratio
        acum_checked_sites += 1
        logging.info("Differences ratio is %s", ratio)
        
        if ratio > DIFF_RATIO:
            logging.info("Close Match: Ratio GREATER THAN min acceptable Ratio of %s.", DIFF_RATIO)
            logging.info("Nothing to report")
        else:
            logging.info("Ratio is LESS THAN defined RATIO of %s", DIFF_RATIO)
            logging.info("Reporting differences")
            logging.info("Creating dif HTML")
            diff_html = difflib.HtmlDiff(4, 50).make_file(tmp_text.splitlines(), bsln_text.splitlines(), "Cambio", "Baseline", True, 3)
            
            #logging.info("Adding diff to email body")
            #message_mid += add_chng2msg(message_mid, site, url, diff_html)
            #message_mid += add2msg(message_mid, site, url, "", diff_html)
            #logging.info("Info added to Message")
                        
            '''
            Create and Save specific HTML File for the Diffs in this Site
            '''           
            bsln_html_file = Path(site + ".html")
            attchmnt_fname = ATTCHMNT_DIR.joinpath(Path(bsln_html_file).name)
            create_file(attchmnt_fname, diff_html)
            logging.info("HTML File for Attachment Created")

            logging.info("Removing Baseline file %s", BASE_FNAME)   #baseline_file)
            os.remove(BASE_FNAME)
            logging.info("Creating New Baseline File with Tempo content")
            create_file(BASE_FNAME, content)
            
            logging.info("Adding diff to Changes Index")
            chng_ndx.update({site:url})
            
    logging.info("DONE PROCESSING %s", site)
    logging.info("*********************************************************************")
logging.info("All URLs processed")
logging.info("*********************************************************************")

if chng_ndx or rqterror_ndx:  #At least 1 element in dicts, then send email

    logging.info('Preparing to send email')    

    logging.info('Email msg setup')
    # Create the enclosing (outer) message
    outer = MIMEMultipart('alternative')
    outer['To'] = EMAIL_TO
    outer['From'] = EMAIL_FROM
    outer['Subject'] = EMAIL_SBJ
    
    chng_list_html = ""
    rqterror_list_html = ""
        
    if rqterror_ndx:
        logging.info('Preparing Request Errors TOC')
        rqterror_list_html_ini = "<h3>URL Request problems in:</h3><ul>"
        rqterror_list_html_mid = ""
        rqterror_list_html_fin = "</ul>"
        
        for url in rqterror_ndx:
            rqterror_list_html_mid = rqterror_list_html_mid + "<li><a href='" + rqterror_ndx[url] + "'>" + url + "</a></li>"
        
        rqterror_list_html = rqterror_list_html_ini + rqterror_list_html_mid + rqterror_list_html_fin
    
    if chng_ndx:
        logging.info('Preparing Changed sites TOC')
        chng_list_html_ini = "<h3>Changes deteted in:</h3><ul>"
        chng_list_html_mid = ""
        chng_list_html_fin = "</ul>"
                
        for url in chng_ndx:
            chng_list_html_mid = chng_list_html_mid + "<li><a href='" + chng_ndx[url] + "'>" + url + "</a></li>" 
    
        chng_list_html = chng_list_html_ini + chng_list_html_mid + chng_list_html_fin
    
        logging.info('Attaching files with Changed Sites Diffs')
        for filename in os.listdir(ATTCHMNT_FILES_FLDR):
            path = os.path.join(ATTCHMNT_FILES_FLDR, filename)
            ctype, encoding = mimetypes.guess_type(path)
            maintype, subtype = ctype.split('/', 1)
            with open(path, 'rb') as fp:
                msg = MIMEBase(maintype, subtype)
                msg.set_payload(fp.read())
                # Encode the payload using Base64
            encoders.encode_base64(msg)
            msg.add_header('Content-Disposition', 'attachment', filename=filename)
            outer.attach(msg)
    
    logging.info('Preparing Main Msg Body')
    message = message_top + rqterror_list_html + chng_list_html + message_end
    message_mime_part = MIMEText(message, 'html')
    outer.attach(message_mime_part)

    logging.info('Sending Email')
    #Sending Msg
    mailserver = smtplib.SMTP(EMAIL_SMTP,EMAIL_PORT)
    # identify ourselves to smtp gmail client
    mailserver.ehlo()
    # secure our email with tls encryption
    mailserver.starttls()
    # re-identify ourselves as an encrypted connection
    mailserver.ehlo()
    mailserver.login(EMAIL_USR, EMAIL_PWD)
    mailserver.sendmail(EMAIL_FROM ,EMAIL_TO,outer.as_string())
    mailserver.quit()

    logging.info("Email Sent")
    logging.info("*********************************************************************")    
else:
    logging.info("Nothing to Report. No email sent")
    logging.info("*********************************************************************")

logging.info('Final stats:')
logging.info("Sites checked ............. %s", len(url_dict))
logging.info("Base Ratio ................ %s", DIFF_RATIO)
logging.info("Avg Diff Ratio Detected ... %s", acum_ratio/acum_checked_sites)
logging.info("URL Errors ................ %s", len(rqterror_ndx))
logging.info("Changes Detected .......... %s", len(chng_ndx))
logging.info("Attachments in email ...... %s", len([name for name in os.listdir(ATTCHMNT_FILES_FLDR) if os.path.isfile(name)]))
logging.info("*********************************************************************")
logging.info("*** PROCESS FINISHED ***")
logging.info("*********************************************************************")


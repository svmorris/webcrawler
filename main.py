import os
import re
import sys
import time
import sqlite3
import hashlib
import requests
from bs4 import BeautifulSoup


global SCOPE
SCOPE = r''

global S
S = requests.Session()

global SEEN
SEEN = set()

global TIMEOUT
TIMEOUT = 1


def db_setup():
    try:
        db_connection = sqlite3.connect(f'urls.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute("CREATE TABLE urls ('url', 'hash')")
        db_connection.commit()
        db_connection.close()
    except Exception as e:
        print(e)




def db_save(url, md5_hash):
    db_connection = sqlite3.connect(f'urls.db')
    db_cursor = db_connection.cursor()
    db_cursor.execute('INSERT INTO urls VALUES (?, ?)', (url, md5_hash))
    db_connection.commit()
    db_connection.close()




def db_check(md5_hash):
    db_connection = sqlite3.connect(f'urls.db')
    db_cursor = db_connection.cursor()
    db_cursor.execute('SELECT * FROM urls WHERE hash = ?', (md5_hash,))
    data = db_cursor.fetchall()
    db_connection.commit()
    db_connection.close()

    if len(data) > 0:
        return True
    else:
        return False



def sanitize(a):
    b = []
    for i in a:
        if re.match(r'[^a-zA-Z0-9]',i):
            i = '.'
        b.append(i)
    return ''.join(b)



def recurse_find(url):
    if not url:
        return

    for i in SEEN:
        # print(f"{i} != {url}")
        if i == url:
            return


    # add url to seen list
    globals()['SEEN'].add(url)


    # downlaod website contents
    try:
        res = S.get(url, headers={'User-Agent': "firefox", 'Accept': 'text/*, application/*, script/*'})
    except Exception as e:
        print(e)
        return

    if res.status_code != 200:
        return
    # print(3)

    # extract and hash web conents
    data = res.text
    md5_hash = str(hashlib.md5(data.encode("utf-8")).hexdigest())


    # should be true if another url links to this one (the hash of conents is the same)
    if db_check(md5_hash):
        return

    # print(4)


    # save url both in db and on disc
    db_save(url, md5_hash)
    with open(f"saved/{md5_hash}", "w+")as outfile:
        outfile.write(url+"\n"+data)



    # get all a tags
    soup = BeautifulSoup(data, 'lxml')
    tags = soup.find_all('a')

    print(url)

    # for a tag in website
    for tag in tags:
        # get url
        link = tag.get_attribute_list('href')[0]

        # if there was no href tag, then return
        if not link:
            continue


        # if website uses http shorthand //, then add the same protocol as the main url has
        if link[:2] == '//':
            link = url[:url.find(':')] + ':' + link


        # if its using absolute paths
        elif link[0] == '/':
            # add link to baseurl
            link = url[:url.find('/', 9)] + link


        # if its using relative paths
        elif link[:2] == './' or link[:2] == '..':
            # if we are stuck in a loop of url/xx/xx/xx/xx/xx/xx
            if url[len(url)-len(link):].strip("/") == link.strip('/'):
                return

            link = url + link


        # check if really a url and its in scope
        if re.match(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", link) and re.search(SCOPE, link):
            time.sleep(TIMEOUT)
            recurse_find(link)



    print('returning')
    return







if __name__ == "__main__":
    db_setup()
    if not os.path.exists('saved/'):
        os.mkdir("saved/")
    recurse_find(sys.argv[1])


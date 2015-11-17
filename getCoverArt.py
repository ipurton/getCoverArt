import os
from tinytag import TinyTag
import requests
from lxml import html
import zipfile

__author__ = 'ipurton'

# When run in a folder containing music files, this script pulls album/artist
# info and searches coverlib.com for images associated with the album.

# Revision Log:
# 11/16/2015    IP
# Script now automatically unzips the archive downloaded from coverlib and
# deletes that archive, along with an unneeded readme file.
# 11/15/2015    IP
# First working version. Requires script to be in the same folder as music
# files needing cover images.

# To-Do:
# Allow script to query folders other than current directory (cmd args?)

# Dependencies:
# lxml (use http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml on Windows)
# requests (http://docs.python-requests.org/en/latest/)
# tinytag (https://github.com/devsnd/tinytag)

### Define Functions ###

def elimSpecials(string, var_sep="+"):
    """Eliminates words containing special characters from a string.

    Parameters:
    string -- Plain string containing one or more words.
    var_sep -- Character that seperates words in string (default +)
    Return Value:
    This function returns the inputted string with words containing special
    characters eliminated.
    """
    words = string.split(sep = var_sep)
    new_words = []
    for word in words:
        if word.isalpha():
            new_words.append(word)
    try:
        new_string = var_sep.join(new_words)
    except:
        new_string = string

    return new_string

### Get Music Info ###

# Get current working directory as a string
cwd = os.getcwd()

# Define music file extentions
file_ext = [".mp3", ".ogg", "flac", ".wav"]

# Get a list of all files in cwd
files = [f for f in os.listdir(cwd) if os.path.isfile(f)]

# Filter list to only include music files
m_files = [f for f in files if f[-4:] in file_ext]

# Iterate through music files, pulling artist/album name info
ar_list = []
al_list = []
for file in m_files:
    try:
        tag = TinyTag.get(file)
        temp_ar = tag.artist
        temp_al = tag.album
        if not temp_ar in ar_list:
            ar_list.append(temp_ar)
        if not temp_al in al_list:
            al_list.append(temp_al)
    except:
        exit("No available tag information.")

# If music files come from more than one album, exit script with error
if len(al_list) > 1:
    exit("More than one album found in current dir. Please check files.")
else:
    album = al_list[0].replace(" ", "+")

# If music files come from more than one artist, use "Various Artists" for
# search query.
if len(ar_list) > 1:
    artist = "Various+Artists"
else:
    artist = ar_list[0].replace(" ", "+")

### Run Search Operation ###

# The following search operation doesn't appear to handle special characters
# well, largely due to labeling issues on coverlib. As is, this script strips
# words containing special characters.

alpha_al = elimSpecials(album)
alpha_ar = elimSpecials(artist)

# Define search url using album & artist info
# Bizzarely, this ONLY works when formatter as "artist album". "Album artist"
# achieves no results!
url = "http://coverlib.com/search/?q={}+{}&Sektion=2".format(alpha_ar, alpha_al)

# Import html from search page into an xml tree
page = requests.get(url)
tree = html.fromstring(page.content)

# coverlib's search result page returns div rows of thumbnails for full images.
# Each div of class=row has a div containing all thumbnails, and a unique id
# for that set of images.
# Ex: <div class="thumbnail text-muted searchitem js_href"
# data-href="/entry/id202809/justin-timberlake-futuresex-lovesounds">
# The data-href value identifies the page where the full-size images can be
# found.

# This finds divs of class "thumbnail ..." and returns the data-href values as
# a list.
art_urls = tree.xpath(
    "//div[@class='thumbnail text-muted searchitem js_href']/@data-href")

if len(art_urls) is 0:
    exit("No results found for album/artist.")

# Each page referred to by an art_url has a line similar to the following:
# Ex. <form id="EntryForm"
# action="/Download/zip/Justin_Timberlake-Futuresex-Lovesounds.zip"
# method="post">
# The value of the action parameter needs to be pulled for each url.

art_zips = []
url_head = "http://coverlib.com"
for url in art_urls:
    r_url = url_head + url
    temp_r = requests.get(r_url)
    temp_tree = html.fromstring(temp_r.content)
    temp_zip = temp_tree.xpath("//form[@id='EntryForm']/@action")
    art_zips.append(url_head + temp_zip[0])

# For each url in art_zips, generate a local file container and stream the zip
# into it. Then, extract the zip file and do some minor tidying.
ii = 1
for url in art_zips:
    filename = "image_zip{}.zip".format(ii)
    
    with open(filename, "wb") as handle:
        r = requests.get(url, stream=True)

        if not r.ok:
            exit("Zip file not found.")

        for block in r.iter_content(1024):
            handle.write(block)

        r.close()

    with zipfile.ZipFile(filename) as zip_ref:
        zip_ref.extractall()

    #zip_ref = zipfile.ZipFile(filename)
    #zip_ref.close()

    try:
        os.remove(filename)
    except PermissionError:
        print("Zip file couldn't be removed automatically.")

    if os.path.isfile("readme.txt"):
        os.remove("readme.txt")

    ii += 1

print("{} image sets found and saved to disk.".format(ii-1))
os.system("pause") #Windows only; use input() for other OSs

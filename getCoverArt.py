#!/usr/bin/env python3.4

import os
from tinytag import TinyTag
import requests
from lxml import html
import zipfile

__author__ = 'ipurton'

# When run in a folder containing music files, this script pulls album/artist
# info and searches websites for images associated with the album.

# Revision Log:
# 1/26/2015     IP
# Removed one of the search sites; still looking for replacement.
# 12/18/2015    IP
# Better commenting.
# 12/16/2015    IP
# Better handling of search failures on allcdcovers.
# 11/26/2015    IP
# Added allcdcovers as a second search host to add redundancy.
# 11/16/2015    IP
# Script now automatically unzips the archive downloaded from coverlib and
# deletes that archive, along with an unneeded readme file.
# 11/15/2015    IP
# First working version. Requires script to be in the same folder as music
# files needing cover images.

# To-Do:
# Allow script to query folders other than current directory (cmd args?)
# Add additional search hosts.

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
        input("No available tag information; press Enter to exit.")
        exit()

# If music files come from more than one album, exit script with error
if len(al_list) > 1:
    input("More than one album found in current dir; press Enter to exit.")
    exit()
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
# well, largely due to labeling issues on hosts. As is, this script strips
# words containing special characters.

# Better way to do this? Maybe a dictionary for replacing characters, or some
# form of input option?

alpha_al = elimSpecials(album)
alpha_ar = elimSpecials(artist)

# Define potential search hosts
#host_urls = ["http://www.allcdcovers.com", "http://coverlib.com"]
host_urls = ["http://www.allcdcovers.com"]
    # As of 11/24/2015, coverlib.com appears to be down.
    # As of 1/26/2016, coverlib.com is not used as a search host.

# Iterate through potential hosts, use the one that's up as the host
for url in host_urls:
    try:
        r = requests.get(url)
        s_host = url
    except:
        print("{} is down.".format(url))

# If an active host was found, notify user what's being used. Otherwise, exit
# with an explanation.
if s_host:
    print("Using {} to run search.".format(s_host))
else:
    input("All search hosts are down. Press Enter to exit.")
    exit()

# Each search host neccisitates different http scraping procedures. Currently,
# this is handled with if/elif statements. Is there a better way...?
## allcdcovers ##
if s_host is host_urls[0]:
    # Define search url using album & artist info
    url = "http://www.allcdcovers.com/search/all/all/{}+{}/1".format(alpha_ar,
                                                                     alpha_al)

    # Import html from search page into an xml tree
    page = requests.get(url)
    tree = html.fromstring(page.content)

    # Search results page returns divs of class "coverLink" that contain a link
    # to all images for that cds.
    # Ex: <div class="coverLink">
    # <a href="/show/330836/ought_more_than_any_other_day_2014_retail_cd/front">
    # <img src="/images/loading.gif" alt="" id="cover_image_805204828"/>
    # <br/>Front</a>

    # Find divs of class "coverLink" and return child href values as a list.
    art_urls = tree.xpath("//div[@class='coverLink']//a/@href")

    # Generate count of found urls
    url_count = len(art_urls)
    print("{} images found.".format(url_count))

    # If no results are found, provide an option for an alternative search
    if url_count is 0:
        print("No results found for album/artist search. ",
              "Do you want to try a keyword search?")
        check = int(input("1: enter new search parameters, 2: exit program: "))
        if check is 1:
            # As long as there no search results, allow user to search for
            # album covers using specified keywords.
            # Possibly remove the while loop and do a single keyword search?
            while url_count is 0:
                keywords = input("Enter new search keywords: ")
                keywords = keywords.replace(" ", "+")

                if keywords is "~":
                    exit()

                # Rerun search with user-defined keywords
                url = "http://www.allcdcovers.com/search/all/all/{}/1".format(
                    keywords)
                page = requests.get(url)
                tree = html.fromstring(page.content)

                art_urls = tree.xpath("//div[@class='coverLink']//a/@href")

                url_count = len(art_urls)

                if url_count is 0:
                    print("No results found. ",
                          "Try a new search or enter ~ to exit.")
        elif check is 2:
            exit()
        
    # Each art_url page contains a div of class "selectedCoverThumb" with a
    # child href pointing to a download page for the image.

    img_urls = {}
    ii = 1
    for url in art_urls:
        # The last part of the art_url says what kind of image this is (eg.
        # front, inlay, etc). This can be used to identify the url and, later,
        # the downloaded image.
        x = url.split("/") # Split url into indiv. elements
        img_type = "[{}] {}".format(str(ii), x[-1])
            # Create a unique filename for each img using a counter and the
            # last element of the url.
        r_url = s_host + url # Recreate full url
        temp_r = requests.get(r_url)
        temp_tree = html.fromstring(temp_r.content)
        temp_url = temp_tree.xpath(
            "//div[@class='selectedCoverThumb']//a/@href")
        img_urls[img_type] = (s_host + temp_url[0])
            # Populate img_urls dict; key is img_type & value is the url of the
            # image file.
        ii += 1

    # Iterate through dict, saving out images
    for name,url in img_urls.items():
        filename = "{}.jpg".format(name)
            # allcdcovers has all cover images as jpg
        
        with open(filename, "wb") as handle:
            r = requests.get(url, stream=True)

            if not r.ok:
                print("Image not found at {}.".format(url))
                break

            for block in r.iter_content(1024):
                handle.write(block)

            r.close()

    print("{} images found and saved to disk.".format(ii-1))
    os.system("pause") # Windows only; use input() for other OSs

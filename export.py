#!/usr/bin/env python3
#
#  Podcasts Export
#  ---------------
#  Douglas Watson, 2022, MIT License
#
#  Modified by: Ted Feng, 2024/06/26
#  1. Add ttml export
#  2. Add txt export, converted from ttml 
#
#  export.py: reads list of available episodes from Podcasts.app database, 
#             copies downloaded episodes to specified folder.


import os
import sys
import shutil
import urllib.parse
import sqlite3
import datetime
import re

from distutils.dir_util import copy_tree
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3


SQL = """
SELECT p.ZAUTHOR, p.ZTITLE, e.ZTITLE, e.ZASSETURL, e.ZPUBDATE, e.ZDURATION, e.ZFREETRANSCRIPTIDENTIFIER
from ZMTEPISODE e 
join ZMTPODCAST p
    on e.ZPODCASTUUID = p.ZUUID 
where ZASSETURL NOTNULL;
"""


def get_downloaded_episodes(set_progress=print, emit_message=print):
    """ Returns list of episodes.
    Format [[author, podcast, title, path, zpubdate, duration, ttml], ...]
    """
    return sqlite3.connect(get_db_path()).execute(SQL).fetchall()
    
def get_db_path():
    return os.path.expanduser(
        "~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite")

def export_ttml(ttml):
    source_ttml = os.path.expanduser(os.path.join("~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Library/Cache/Assets/TTML/", ttml))
    


def export(episodes, output_dir, set_progress=None, emit_message=print):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    counter = 0
    for author, podcast, title, path, zpubdate, zduration, zttml in episodes:
        if set_progress is not None:
            set_progress(int(counter / len(episodes) * 100))
        counter += 1

        safe_title = title.replace('/', '|').replace(':', ',')
        safe_podcast = podcast.replace('/', '|').replace(':', ',')
        safe_author = author.replace('/', '|').replace(':', ',')
        pubdate = datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=zpubdate)

        podcast_path = os.path.join(output_dir, safe_podcast)
        if not os.path.exists(podcast_path):
            os.makedirs(podcast_path)

        source_path = urllib.parse.unquote(path[len('file://'):])
        ext = os.path.splitext(source_path)[1] or ".mp3"
        dest_path = os.path.join(podcast_path,
                                 u"{:%Y.%m.%d}-{}-({}){}".format(pubdate, safe_title[0:140], safe_author[0:100], ext))

        if ext == ".movpkg":
            emit_message(u"{} - {}, media file is not an mp3 file, may require further conversion".format(podcast, title))
            copy_tree(source_path, dest_path)
            continue
        else:
            shutil.copy(urllib.parse.unquote(path[len('file://'):]), dest_path)

        if ext == ".mp4":
            emit_message(u"{} - {} is an mp4 file.".format(podcast, title))
            mp4 = MP4(dest_path)
            if mp4.tags is None:
                mp4.add_tags()
            mp4.tags['\xa9ART'] = author
            mp4.tags['\xa9alb'] = podcast
            mp4.tags['\xa9nam'] = title
            mp4.save()
            continue

        try:
            mp3 = MP3(dest_path, ID3=EasyID3)
        except HeaderNotFoundError:
            emit_message(u"Corrupted file: {} - {}".format(podcast, title))
            continue
        if mp3.tags is None:
            mp3.add_tags()
        mp3.tags['artist'] = author
        mp3.tags['album'] = podcast
        mp3.tags['title'] = title
        mp3.save()

# Process ttml file        
        basename = os.path.basename(zttml).replace('transcript_', '')
        source_ttml = os.path.expanduser(os.path.join("~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Library/Cache/Assets/TTML/", zttml+'-'+basename))
        dest_ttml = os.path.join(podcast_path,
                                 u"{:%Y.%m.%d}-{}-({}){}".format(pubdate, safe_title[0:140], safe_author[0:100], '.ttml'))
        shutil.copy(source_ttml, dest_ttml)

# convert ttml file to txt
        dest_txt = os.path.join(podcast_path,
                                 u"{:%Y.%m.%d}-{}-({}){}".format(pubdate, safe_title[0:140], safe_author[0:100], '.txt'))
        try:
            file_ttml = open(dest_ttml, 'r')
            str_ttml = file_ttml.read()
        finally:
            if file_ttml:
                file_ttml.close()
        
        tmp_str = re.sub(r'</p>', r'\n', str_ttml)
        tmp_str = re.sub(r'<span[^>]*>', '', tmp_str)
        tmp_str = re.sub(r'</span>', ' ', tmp_str)
        tmp_str = re.sub(r'<p .*(SPEAK[^"]+)">', r'\n\1\n', tmp_str)
        tmp_str = re.sub(r'<[^>]+>', '', tmp_str)

        try: 
            file_txt = open(dest_txt, 'w')
            file_txt.write(tmp_str)
        finally:
            if file_txt:
                file_txt.close()


# This provides a very basic but functional Command Line Interface with
# 'mutagen' as the only dependency
if __name__ == '__main__':
        output_dir = sys.argv[1]
        export(get_downloaded_episodes(), output_dir)

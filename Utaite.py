import requests
import re
import os
import sys
import ConfigParser
import logging
import subprocess
import nicofetch
import getpass
import warnings
from HTMLParser import HTMLParser

config_path = "config.cfg"
utaites_path = "utaites.txt"

# Disable console logging.
warnings.filterwarnings("ignore")

# Get configuration file.
config = ConfigParser.RawConfigParser()
config.read(config_path)

# Directory to download songs to.
utaiteBaseDir = config.get("Settings", "BaseDir")

# Utaite page to fetch
utaitePageUrlBase = "http://utaite.wikia.com/wiki/"

# Known groups that should be downloaded seperately.
knownGroups = [["After the Rain"], ["Mafumafu", "Soraru"], ["Soralon"],
               ["Soraru", "Lon"], ["Urata", "Shima", "Aho no Sakata", "Senra"],
               ["96Neko", "Kogeinu", "vipTenchou"], ["Team Pet Shop"], ["USSS"]]

# Regex and fetch from wikia by Stephen Chen

# Pulls out each bulleted item that has an nicovideo reference in it.
listItemRegex = r'<li>.+?href="http://www.nicovideo.jp/watch/(.+?)"(?:.|[\n\r])+?</li>'

# Titles are a bit weird
titleRegex = []
# Captures the case with no YouTube link
# e.g.    <li> "Attakain Dakara" <a href...
titleRegex.append(re.compile(r'<li>\s*"([^<>]+?)"\s*'))
titleRegex.append(re.compile(r'<li>\s*\'([^<>]+?)\'\s*'))
# Captures the case with YouTube link
# e.g.    <li> "<a... href="https://www.youtube.com/...">Flower Rail</a>" ...
titleRegex.append(re.compile(r'<li>\s*"<a.+?>(.+?)</a>"'))
titleRegex.append(re.compile(r'<li>\s*\'<a.+?>(.+?)</a>\''))

# Regex for capturing other artists on the song.
# e.g.    ... -Arrange ver.- (English Name) feat. Reol and kradness (Date) </li>
extraTitlesRegex = re.compile(r'</a>\s*(-.*-|)\s*(\(.*?\)|)\s*(.+|)\s*\(.*?\)\s*(<b>.*</b>\s*|)</li>')
subtitleRegex = re.compile(r'</a>(\s*|\s*\(.*?\)\s*)(-.*?-)')

# Featured artist list regex.
# e.g.    feat. Reol, Mafumafu, luz, and Soraru
featuredSingerRegex = re.compile(r'feat\. (.*)$')
singerRegex = []
singerRegex.append(re.compile(r'^(.*?)(, | and )(.*)$'))
# Capture artists with links
singerRegex.append(re.compile(r'^<a.*?>(.*?)</a>(, and |, | and |)(.*)$'))
# Capture the last artist in the list.
finalSingerRegex = re.compile(r'<a.*>(.*?)</a>')

a_href_regex = re.compile(r'^(.*)<a.*>(.*?)</a>(.*)$')
numberedFileRegex = re.compile(r'^(\d*) .*?')

AudioEncodingRegex = re.compile(r'Stream #0:\d -> #0:1 \((.*?) \(')

def progress_indicator(item, total_bytes, bytes_read, bytes_per_second):
    bar_length = 40
    bar_fill = int((float(bytes_read) / float(total_bytes)) * float(bar_length))
    # \x1B[2K\x1B[1000D
    print("\r{0}: [{1}] {2}/{3} kB ({4} kB/s)".format(
        item,
        "=" * bar_fill + "-" * (bar_length - bar_fill),
        int(bytes_read / 1024),
        int(total_bytes / 1024),
        int(bytes_per_second / 1024)).ljust(79)),
    sys.stdout.flush()

artistsDone = []

print ""

# LOGIN TO NICONICO.
fetcher = nicofetch.NicoFetcher()
logged_in = False
while logged_in is False:
    mail = raw_input("Niconico email login: ")
    password = getpass.getpass("Niconico password: ")
    if fetcher.login(mail, password):
        print ""
        print "Logged in!"
        print ""
        logged_in = True
    else:
        print ""
        print "Could not log in, retry?"
        print ""

# MAIN LOOP
# Loop over all the artists in the utaite file.
with open(utaites_path, 'r') as utaites:
    for utaite in utaites:
        utaite = utaite.rstrip()
        utaite = utaite.replace(" ", "_")
        if not utaite: continue
        dirFriendlyUtaite = utaite.replace(":", "")
        dirFriendlyUtaite = dirFriendlyUtaite.replace(".", "")
        utaiteDir = utaiteBaseDir + dirFriendlyUtaite + "\\" + dirFriendlyUtaite + " NND\\"

        utaitePageUrl = utaitePageUrlBase + utaite
        r = requests.get(utaitePageUrl)
        h = HTMLParser()

        if r.status_code == requests.codes.ok:
            # Section off the area that has is in the "List of Covered Songs" box
            s = r.text
            s = s[s.find("List_of_Covered_Songs"):]
            s = s[:s.find(r'<div style="clear:both; margin:0; padding:0;"></div>')]

            # Handle each bulleted item
            track = 0
            for match in re.finditer(listItemRegex, s):
                track = track + 1

                # CHECK IF THE TRACK HAS ALREADY BEEN DOWNLOADED.
                # Create folders if they do not exist.
                if not os.path.isdir(utaiteBaseDir + dirFriendlyUtaite):
                    os.mkdir(utaiteBaseDir + dirFriendlyUtaite)
                if not os.path.isdir(utaiteDir):
                    os.mkdir(utaiteDir)

                # Loop through the files in the utaite directory. A song is
                # uniquely identified by its artist and track number.
                found = False
                for filepath in os.listdir(utaiteDir):
                    file_match = numberedFileRegex.search(filepath)
                    if file_match is not None:
                        if track == int(file_match.group(1)):
                            found = True
                            break

                if found: continue

                item = match.group(0)
                title = None
                # Match the title.
                for tRegex in titleRegex:
                    tm = tRegex.search(item)
                    if tm is not None:
                        title = tm.group(1)
                        break

                if title is None:
                    title = "<Unknown>"
                else:
                    title = h.unescape(title)

                artists = []

                # Match extra parts of the title and featured singers.
                st = subtitleRegex.search(item)
                if st is not None:
                    title = title + " " + st.group(2)

                # Remove links in the title.
                st = a_href_regex.search(title)
                while st is not None:
                    title = st.group(1) + st.group(2) + st.group(3)
                    st = a_href_regex.search(title)

                # EXTRACT FEATURED ARTISTS AND EXTRA TITLE PARTS.
                fm = extraTitlesRegex.search(item)
                if fm is not None:
                    # Extract artists from extra title.
                    featuredArtists = fm.group(3)
                    fs = featuredSingerRegex.search(featuredArtists)
                    if fs is not None:
                        featuredSingers = fs.group(1)
                        for sRegex in singerRegex:
                            sm = sRegex.search(featuredSingers)
                            if sm is not None:
                                artist = sm.group(1)
                                separator = sm.group(2)
                                newRest = sm.group(3)
                        artists.append(artist)
                        rest = newRest

                        while separator == ", ":
                            for sRegex in singerRegex:
                                sm = sRegex.search(rest)
                                if sm is not None:
                                    artist = sm.group(1)
                                    separator = sm.group(2)
                                    newRest = sm.group(3)
                            artists.append(artist)
                            rest = newRest

                        fs = finalSingerRegex.search(rest)
                        if fs is None:
                            if not rest.isspace():
                                artists.append(rest.lstrip().rstrip())
                        else:
                            artists.append(fs.group(1))

                # DETERMINE IF THE SONG SHOULD BE DOWNLOADED.
                downloadSong = True

                # Determine if the artists fit a known group.
                for group in knownGroups:
                    if set(group) == set(artists):
                        downloadSong = False
                        break

                # Determine if the collaboration has been downloaded already.
                for artist in artists:
                    if artist in artistsDone:
                        downloadSong = False

                nicoUrl = match.group(1)

                if downloadSong:
                    # DOWNLOAD VIDEO.
                    print utaite.replace("_", " ") + " - " + title

                    # Fetch video data.
                    vid = fetcher.fetch(nicoUrl)
                    if vid is None:
                        print "Could not find the video - Probably private or removed."
                        print ""

                    else:
                        if vid.is_economy:
                            print "Economy mode in effect. Exiting..."
                            sys.exit()

                        # Download the video.
                        audio_dir = utaiteDir + str(track) + " " + title
                        # Replace disallowed characters.
                        audio_dir = audio_dir.replace("?", " ")

                        try:
                            vid.save_video(audio_dir, progress_indicator)
                        except:
                            print "Could not download the video - Probably forbidden. Pester developer!"
                            print "Known issue with swf files. This file is a " + vid.video_extension + " file."
                            print ""
                            continue

                        print ""

                        # CONVERT TO AUDIO.
                        sys.stdout.write("Converting...")
                        sys.stdout.flush()

                        featured = ""
                        for artist in artists:
                            featured = featured + artist + ", "
                        featured = featured[:-2]

                        artist_tag = utaite.replace("_", " ")
                        title_tag = title
                        if featured is not "":
                            title_tag = title_tag + " (feat. " + featured + ")"
                        album_tag = utaite.replace("_", " ") + " NND"
                        genre_tag = "Utaite"
                        track_tag = str(track)

                        vid_info = subprocess.check_output(["ffmpeg", "-i",
                            vid._video_path, '-f', 'null', '-'],
                            stderr=subprocess.STDOUT)

                        audio_match = AudioEncodingRegex.search(vid_info)
                        if audio_match is None:
                            print " Error!"
                            print "Could not determine encoding of audio. Pester developer!"
                            print ""
                        else:
                            encoding = audio_match.group(1)

                            if encoding == "aac":
                                output_format = ".m4a"
                            elif encoding == "mp3":
                                output_format = ".mp3"
                            else:
                                print " Error!"
                                print "Encountered a new audio encoding: " + encoding + ". Pester developer!"
                                print ""
                                continue

                            FNULL = open(os.devnull, 'w')
                            subprocess.call(['ffmpeg', '-i', vid._video_path, '-vn',
                                '-acodec', 'copy', '-metadata', 'title=' + title_tag,
                                '-metadata', 'artist=' + artist_tag, '-metadata',
                                'album=' + album_tag, '-metadata', 'track=' + track_tag,
                                '-metadata', 'genre=' + genre_tag, '-metadata',
                                'album_artist=' + utaite.replace("_", " "),
                                '-id3v2_version', '3',
                                audio_dir + output_format],
                                stdout=FNULL, stderr=subprocess.STDOUT)

                            print " Done!"
                            print ""

                            # CLEAN UP UNNEEDED FILES.
                            os.remove(vid._video_path)

        artistsDone.append(utaite.replace("_", " "))

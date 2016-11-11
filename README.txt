 _   _   _             _   _            _____                         _
| | | | | |_    __ _  (_) | |_    ___  |_   _|  _ __    __ _    ___  | | __   ___   _ __
| | | | | __|  / _` | | | | __|  / _ \   | |   | '__|  / _` |  / __| | |/ /  / _ \ | '__|
| |_| | | |_  | (_| | | | | |_  |  __/   | |   | |    | (_| | | (__  |   <  |  __/ | |
 \___/   \__|  \__,_| |_|  \__|  \___|   |_|   |_|     \__,_|  \___| |_|\_\  \___| |_|
#########################################################################################

########################
#     REQUIREMENTS     #
########################

1. Download Python 2.7.12 (https://www.python.org/downloads/release/python-2712/)
2. Install the requests module - in a command prompt, enter "pip install requests"
3. Download ffmpeg (https://www.ffmpeg.org/download.html)
4. Add the location of ffmpeg.exe to your PATH environment variable (.../ffmpeg/bin)

########################
#        USAGE         #
########################

1. Update the BaseDir in config.cfg to the directory that you would like to download to
2. Update the list of utaite in utaites.txt with the utaites that you would like to fetch
    a. Be sure to leave the first line empty
    b. Utaite names entered should be as they appear in address of the utaite wikia, with
         underscores (_) replaced with spaces
         (utaite.wikia.com/wiki/UTAITE_NAME => UTAITE NAME in utaites.txt)
3. Open a command prompt in the directory that Utaite.py was extracted to
     (Shift + right click in windows explorer)
4. Run the script with "python utaite-tracker.py"
5. You will be prompted for your NicoNicoDouga email login and password
6. Watch your utaite collection grow!

########################
#         NOTES        #
########################

1. For now, all .swf files cannot be downloaded, though since there are very few
     of them, this is being left for now. Sometimes non-swf files also have
     permissions issues. Usually these resolve when the download is retried on
     the next execution of the script.
2. Since NND throttles speeds for non-premium users, the downloads will probably be
     pretty slow. I recommend running this script on the side while doing other things
     or overnight. If NND goes into low-economy mode, the script will stop to avoid
     downloading very low-quality files.
3. To stop the script, press Ctrl + C twice in quick succession. This must be done
     because the download is wrapped in a try-except block, so the first Ctrl + C
     will only make the script think that the current download failed.
4. The script keeps track of which files have been downloaded based on the file
     structure and filenames that it downloads files to. In order to not lose
     progress and redownload files, leave the downloaded files where they are
     downloaded to.
5. If an error is encountered that is not explained, please let the developer know!
     Send the utaite name and track that encountered the error as well as the error
     itself, and the developer will investigate.

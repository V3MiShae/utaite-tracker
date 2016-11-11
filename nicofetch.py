# Licenses are boring
# This script may be freely used, modified and distributed as long as
# this notice is included
# - Matti Virkkunen <mvirkkunen@gmail.com> / Lumpio- @IRCnet etc.
#
# https://github.com/lumpio/nicofetch

# Adapted from non-working state.

import sys
import os, os.path, shutil
import urllib, urllib2, cookielib
import tempfile
import time
import re
import subprocess

from cgi import parse_qs
from urllib import unquote

__all__ = ["error", "VideoInfo", "NicoFetcher"]

debug = False

def js_unescape(s):
    s = unicode(s).replace("\\\"", "\"").replace("\\'", "'")
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda mo: unichr(int(mo.group(1), 16)), s)
    s = s.replace("\\\\", "\\");
    return s

def download_file(in_file, out_file, item, progress_listener):
    total_bytes = int(in_file.info().get("Content-Length", 1))
    bytes_read = 0

    if progress_listener:
        progress_listener(item, total_bytes, 0, 0)

        prev_bytes_read = 0
        bytes_per_second = 0
        interval = 0.5

        start_time = time.clock()
        prev_time = start_time

    while True:
        data = in_file.read(10 * 1024)

        out_file.write(data)
        bytes_read += len(data)

        if len(data) == 0:
            bytes_read = total_bytes

        if progress_listener:
            cur_time = time.time()
            if cur_time >= prev_time + interval or bytes_read == total_bytes:
                if bytes_read == total_bytes:
                    bytes_per_second = int(float(total_bytes) / (cur_time - start_time))
                else:
                    bytes_per_second = int(float(bytes_read - prev_bytes_read) / (cur_time - prev_time))

                progress_listener(item, total_bytes, bytes_read, bytes_per_second)

                prev_bytes_read = bytes_read
                prev_time = cur_time

        if bytes_read == total_bytes:
            break

    out_file.close()
    in_file.close()

class error(Exception):
    pass

class VideoInfo:
    def __init__(self, fetcher):
        self.video_id = None
        self.video_extension = None
        self.thread_id = None
        self.title = None
        self.is_economy = None
        self.watch_url = None
        self.video_url = None
        self.comments_url = None

        self._video_path = None
        self._video_is_temp = False
        self._comments_path = None
        self._comments_is_temp = False

        self._fetcher = fetcher

    def request_video(self):
        print "URL: " + self.video_url
        data = {"mail": self._fetcher.mail, "password": self._fetcher.password,
            "next_url": "/watch/" + self.video_id}
        headers = {}
        headers["Referer"] = "http://www.nicovideo.jp/watch/" + self.video_id
        return self._fetcher._request(self.video_url, data, headers)

    def cleanup(self):
        if self._video_is_temp:
            os.remove(self._video_path)
            self._video_is_temp = False
            self._video_path = None

    def _get_path(self, path, default_ext):
        path = os.path.expanduser(path)

        if os.path.exists(path):
            if os.path.isdir(path):
                filename = self.title.replace("/", "").replace("\0", "")
                if self.title != self.video_id:
                    filename += " (" + self.video_id + ")"
                filename += default_ext

                generated_path = os.path.join(path, filename)

                if os.path.exists(generated_path):
                    raise error("File exists: " + generated_path)

                return generated_path
            else:
                raise error("File exists: " + path)
        elif path.endswith("/"):
            raise error("Path ends with / and is not an existent directory")

        return path

    def ensure_video_downloaded(self, progress_listener=None):
        if not self._video_path:
            self._fetcher.authenticate(self.video_id)
            (video_file, video_path) = tempfile.mkstemp(prefix="nicofetch")
            download_file(self.request_video(), os.fdopen(video_file, "w"), "video", progress_listener)
            self._video_path = video_path
            self._video_is_temp = True

    def save_video(self, path, progress_listener=None):
        new_path = self._get_path(path, self.video_extension)
        self.ensure_video_downloaded(progress_listener)

        new_path = new_path + self.video_extension
        shutil.move(self._video_path, new_path)
        self._video_path = new_path
        self._video_is_temp = False

class NicoFetcher:
    VIDEO_ID_RE = re.compile(r"(?:/|%2F|^)([a-z]{2}\d+)")
    THUMB_VIDEO_TITLE_RE = re.compile(r"title:\s*'([^']*)'")
    THUMB_KEY_RE = re.compile(r"'thumbPlayKey':\s*'([^']*)'")
    THUMB_MOVIE_TYPE_RE = re.compile(r"movieType:\s*'([^']*)'")
    LOGGED_VIDEO_TITLE_RE = re.compile(r"\(\"wv_title\", \"([^\"]*)\"\)")
    LOGGED_MOVIE_TYPE_RE = re.compile(r"<movie_type>(.*?)</movie_type>")
    DELETED_RE = re.compile(r'<description>(deleted)|(not found or invalid)</description>')
    URI_RE = re.compile(r"\.jp(.*)")
    #LOGGED_MOVIE_TYPE_RE = re.compile(r"\(\"movie_type\", \"([^\"]*)\"\)")
    #WATCH_VARS_RE = re.compile(r"<embed[^>]+id=\"flvplayer\"[^>]+flashvars=\"([^\"]*)\"", re.I)
    #NOT_LOGGED_IN_RE = re.compile(r"<form[^>]*?id=\"login\"")

    def __init__(self):
        self.is_logged_in = False
        self.is_premium = False
        self.mail = None
        self.password = None

        self._cookie_jar = cookielib.CookieJar()
        self._opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=debug), urllib2.HTTPCookieProcessor(self._cookie_jar))

    def _request_data(self, *args, **kwargs):
        f = self._request(*args, **kwargs)
        data = f.read()
        f.close()
        return data

    def _request(self, url, data=None, headers={}):
        if data is not None and not isinstance(data, basestring):
            data = urllib.urlencode(data)

        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36"

        req = urllib2.Request(url, data, headers)

        return self._opener.open(req)

    def authenticate(self, video_id):
        # Attempt to gain permissions by just having logged in on the video page.
        self._request("https://secure.nicovideo.jp/secure/login?site=niconico",
            {"mail": self.mail, "password": self.password, "next_url": "/watch/" + video_id})

    def login(self, email, password):
        self.mail = email
        self.password = password
        login_data = self._request("https://secure.nicovideo.jp/secure/login?site=niconico",
            {"mail": email, "password": password})

        flag = login_data.info().getheader("x-niconico-authflag")

        self.is_logged_in = (flag == "1") or (flag == "3")
        self.is_premium = (flag == "3")

        return self.is_logged_in

    def _fetch_video_data(self, vid, url, data=None):
        video_data = self._request_data(url, data)

        try:
            getflv_values = parse_qs(video_data)

            vid.thread_id = getflv_values["thread_id"][0]
            vid.video_url = getflv_values["url"][0]
            if vid.video_url[-3:] == "low":
                vid.is_economy = True
            vid.comments_url = getflv_values["ms"][0]

            return True
        except:
            return False

    def _fetch_logged_in(self, vid):
        watch_data = self._request_data("http://ext.nicovideo.jp/api/getthumbinfo/" + vid.video_id)

        # Check that the video is available.
        if self.DELETED_RE.search(watch_data) is not None:
            return False

        mo = self.LOGGED_MOVIE_TYPE_RE.search(watch_data)
        if mo is None:
            # Assume mp4 if information cannot be found.
            vid.video_extension = ".mp4"
        else:
            vid.video_extension = "." + mo.group(1).lower()

        vid.title = unicode(vid.video_id)

        if not self._fetch_video_data(vid, "http://flapi.nicovideo.jp/api/getflv/" + vid.video_id):
            return False

        return True

    def fetch(self, video_id):
        vid = VideoInfo(self)

        vid.video_id = video_id
        vid.watch_url = "http://www.nicovideo.jp/watch/" + vid.video_id

        if self.is_logged_in:
            if not self._fetch_logged_in(vid):
                return None
        else:
            return None

        return vid

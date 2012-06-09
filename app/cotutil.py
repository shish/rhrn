
import web
import hashlib
import random
import re
import model
import math


def override_method(handler):
    web.ctx.method = web.input().get("_method", web.ctx.method)
    return handler()


class User:
    def __init__(self, row):
        self.name = row.name
        self.password = row.password
        self.email = row.email
        self.avatar = "http://www.gravatar.com/avatar/"+hashlib.md5(row.email).hexdigest()

    def get_avatar(self, size):
        return "http://www.gravatar.com/avatar/"+hashlib.md5(self.email).hexdigest()+"?s="+str(size)


class Review:
    def __init__(self, row):
        self.row = row

    def dict(self):
        d = dict(self.row)
        del d["writer_ip"]
        d["avatar"] = User(model.get_user(d["writer"])).avatar
        d["date_posted"] = shorten_datetime(d["date_posted"])
        return d


def hashpw(pw):
    return hashlib.sha1("s4l7y-w4l7y\x00"+pw).hexdigest()


def generate_password():
    choices = "235679abcdefghkmnpqrstuvwxyz"
    pw = ""
    for n in range(0, 8):
        pw = pw + random.choice(choices)
    return pw


def shorten_url(url):
    return re.sub("https?://(www\.)?", "", url)


def shorten_datetime(dt):
    return str(dt)[:16]


def get_domain(url):
    return re.sub("https?://(?:www\.)?([^/]+).*", "\\1", url)


def ll_to_metric(lon1, lat1, lon2, lat2):
    R = 6371
    dLat = math.radians(lat2-lat1)
    dLon = math.radians(lon2-lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    if d < 1:
        return "%dm" % (d*1000)
    else:
        return "%.2fkm" % d

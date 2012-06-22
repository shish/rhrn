#!/usr/bin/python

import web
from webutil import *
import model
import json
import math
import Image
import colorsys
import StringIO
import os
import logging
import logging.handlers
import ConfigParser
import urllib2

config = ConfigParser.SafeConfigParser()
config.read("../app/rhrn.cfg")

web.config.debug = True

urls = (
    '/', 'index',
    '/about', 'about',
    '/about/(.*)', 'about',

    '/review', 'review',
    '/review/(.*)', 'review',

    '/dashboard', 'dashboard',
    '/dashboard/login', 'dashboard_login',
    '/dashboard/logout', 'dashboard_logout',

    '/user/(.*)', 'user',

    '/tiles/happiness/(.*)/(.*)/(.*).png', 'tiles',

    '', ''
)
app = web.application(urls, globals())
app.add_processor(override_method)


class User:
    def __init__(self, row):
        self.name = row.name
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


if web.config.get('_session') is None:
    import rediswebpy
    session = DefaultingSession(app, rediswebpy.RedisStore(prefix='session:rhrn:'), {
        'user': User(model.get_user(name="Anonymous")),
        'flash': [],
    })
    web.config._session = session
else:
    session = web.config._session

def flash(type, msg):
    session.flash.append((type, msg))

def flash_clear():
    session.flash = []

render_bare = web.template.render('../templates', globals={
    'session': session,
    'shorten_url': shorten_url,
    'shorten_datetime': shorten_datetime,
    'get_domain': get_domain,
    'flash_clear': flash_clear,
    'urlquote': web.urlquote
})
render_mobile = web.template.render('../templates/mobile', base='base', globals={
    'session': session,
    'shorten_url': shorten_url,
    'shorten_datetime': shorten_datetime,
    'get_domain': get_domain,
    'flash_clear': flash_clear,
    'urlquote': web.urlquote,
    'll_to_metric': ll_to_metric
})
render = web.template.render('../templates', base='base', globals={
    'session': session,
    'shorten_url': shorten_url,
    'shorten_datetime': shorten_datetime,
    'get_domain': get_domain,
    'flash_clear': flash_clear,
    'urlquote': web.urlquote
})



class index:
    def GET(self):
        if web.ctx.host.startswith("m."):
            return render_mobile.index()
        else:
            i = web.input(lat=None, lon=None)
            return render.index(i.lat, i.lon)


class about:
    def GET(self, page="about"):
        if page == "about":
            return render.about_about()


class review:
    def GET(self, id=None):
        if id == "new":
            import time
            i = web.input(lat="0", lon="0", id="r"+str(time.time()))
            if web.ctx.host.startswith("m."):
                return render_mobile.new_review(i.id, i.lat, i.lon)
            else:
                return render_bare.new_review(i.id, i.lat, i.lon)
        if id == None:
            if web.ctx.host.startswith("m."):
                i = web.input(lon=None, lat=None)
                rs = model.get_reviews_point(i.lon, i.lat)
                return render_mobile.reviews(rs, float(i.lon), float(i.lat))

            i = web.input(bbox="0,0,0,0", filter=None)

            if i.filter == "my":
                writer = session.user.name
                notwriter = None
            elif i.filter == "notme":
                writer = None
                notwriter = session.user.name
            elif i.filter == "notanon":
                writer = None
                notwriter = "Anonymous"
            else:
                writer = None
                notwriter = None

            bbox = [float(n) for n in i.bbox.split(",")]
            rs = model.get_reviews(bbox=bbox, writer=writer, notwriter=notwriter)
            return json.dumps({
                "status": "ok",
                "message": None,
                "data": [Review(r).dict() for r in rs]
            })

    def POST(self):
        i = web.input(
            lat=None, lon=None, comment=None, happy=None,
            volume=None, danger=None, crowds=None,
            anon=None
        )

        if i.anon:
            username = "Anonymous"
        else:
            username = session.user.name

        model.new_review(
            username, web.ctx.ip,
            i.happy=="true", float(i.lon), float(i.lat), i.comment,
            i.volume, i.danger, i.crowds
        )

        if web.ctx.host.startswith("m."):
            raise web.seeother("/")
        else:
            return json.dumps({
                "status": "ok",
                "message": None,
                "data": None
            })

    def DELETE(self, id):
        if session.user.name == "Anonymous":
            return

        r = model.get_review(id)
        if r and (session.user.name == r.writer or session.user.name == "Shish"):
            model.del_review(id)
            return json.dumps({
                "status": "ok",
                "message": None,
                "data": None
            })


class dashboard:
    def GET(self):
        if session.user.name == "Anonymous":
            raise web.seeother("/")
        yays = model.get_reviews(writer=session.user.name, happy=True)
        nays = model.get_reviews(writer=session.user.name, happy=False)
        favs = model.get_reviews(writer=session.user.name, favourite=True)
        return render.dashboard(session.user.name, yays, nays, favs)

class dashboard_login:
    def POST(self):
        inp = web.input(name=None, email=None, token=None)

        # creating a new user
        if inp.name and inp.email and inp.token:
            ex = model.get_user(name=inp.name)
            if ex:
                return render.janrain(inp.name, inp.email, inp.token, "Username taken")

            ex = model.get_user(email=inp.email)
            if ex:
                return render.janrain(inp.name, inp.email, inp.token, "Email already in use")

            model.new_user(inp.name, inp.email, token=inp.token)

            user = model.get_user(token=inp.token)
            session.user = User(user)
            raise web.seeother("/")

        # already got a user
        elif inp.token:
            data = urllib2.urlopen("https://rpxnow.com/api/v2/auth_info?apiKey=%s&token=%s" % (config.get("janrain", "apikey"), inp.token)).read()
            resp = json.loads(data)
            if resp['stat'] == "ok":
                prof = resp['profile']
                jid = prof['identifier']
                user = model.get_user(token=jid)
                user_mail = model.get_user(email=prof['email'], token='')
                if user:
                    model.set_user_meta_by_email(user.email, data)
                    session.user = User(user)
                    raise web.seeother("/")
                elif user_mail:
                    model.set_user_token_by_email(prof['email'], jid)
                    model.set_user_meta_by_email(prof['email'], data)
                    session.user = User(user_mail)
                    raise web.seeother("/")
                else:
                    return render.janrain(prof.get('preferredUsername', ''), prof.get('email', ''), jid)
            else:
                return "Error logging in"

        return "Missing token"

class dashboard_logout:
    def GET(self):
        # FIXME: used by mobile
        session.user = User(model.get_user(name="Anonymous"))
        raise web.seeother("/")

    def POST(self):
        session.user = User(model.get_user(name="Anonymous"))
        raise web.seeother("/")


class user:
    def GET(self, name="Anonymous"):
        yays = model.get_reviews(writer=name, happy=True)
        nays = model.get_reviews(writer=name, happy=False)
        favs = model.get_reviews(writer=name, favourite=True)
        return render.dashboard(name, yays, nays, favs)


def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

class tiles:
    def GET(self, zoom, x, y):
        cache_file = "cache/%s-%s-%s.png" % (zoom, x, y)

        if os.path.exists(cache_file):
            return file(cache_file).read()

        (lat0, lon0) = num2deg(int(x)-1, int(y)+2, int(zoom))
        (lat1, lon1) = num2deg(int(x),   int(y)+2, int(zoom))
        (lat2, lon2) = num2deg(int(x)+1, int(y),   int(zoom))
        (lat3, lon3) = num2deg(int(x)+2, int(y)-1, int(zoom))
        (latd, lond) = (abs(lat1-lat2), abs(lon1-lon2))

        rs = list(model.get_reviews(bbox=[
            lon0, lat0,
            lon3, lat3
        ]))

        im = Image.new('RGBA', (256, 256))
        pix = im.load()

        logging.info("Generating tile based on %d reviews" % len(rs))
        if rs:
            for x in range(0, 256):
                for y in range(0, 256):
                    lat = lat1 + latd * float(256-y)/256
                    lon = lon1 + lond * float(x)/256
                    goodness = 0
                    badness = 0
                    for r in rs:
                        d = math.sqrt(math.pow((lat-r.lat)/latd, 2) + math.pow((lon-r.lon)/lond, 2))
                        if d < 1:
                            if r.happy:
                                goodness = goodness + (1-d)
                            else:
                                badness = badness + (1-d)
                            #if r.happy:
                            #    goodness = goodness + (0.001 - d) * 1000
                            #else:
                            #    badness = badness + (0.001 - d) * 1000
                    good_hue = 2.0/6
                    bad_hue = 0.0/6
                    mid = (good_hue + bad_hue) / 2
                    if goodness - badness == 0:
                        hue = mid
                        alp = 0
                    else:
                        ratio = (goodness - badness) / (goodness + badness)
                        hue = mid + mid * ratio
                        alp = 63 * clamp(0, max(goodness, badness)/2, 1)
                    sat = 1
                    val = 1
                    (r, g, b) = colorsys.hsv_to_rgb(hue, sat, val)
                    pix[x, y] = (int(r*256), int(g*256), int(b*256), int(alp))

        buf = StringIO.StringIO()
        im.save(buf, format= 'PNG')

        file(cache_file, "w").write(buf.getvalue())

        return buf.getvalue()

if __name__ == "__main__":
    logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s %(message)s',
            filename="../logs/app.log")
    smtp = logging.handlers.SMTPHandler(
            "localhost", "noreply@shishnet.org",
            ["shish+rhrn@shishnet.org", ], "rhrn error report")
    smtp.setLevel(logging.WARNING)
    logging.getLogger('').addHandler(smtp)

    logging.info("App starts...")
    app.run()

#!/usr/bin/python

import web
import model
import json
import math
import Image
import colorsys
import StringIO
import os
from cotutil import *

web.config.debug = True

urls = (
    '/', 'index',
    '/about', 'about',
    '/about/(.*)', 'about',

    '/review', 'review',
    '/review/(.*)', 'review',

    '/dashboard', 'dashboard',
    '/dashboard/new', 'dashboard_new',
    '/dashboard/login', 'dashboard_login',
    '/dashboard/logout', 'dashboard_logout',
    '/dashboard/reset', 'dashboard_reset',

    '/tiles/happiness/(.*)/(.*)/(.*).png', 'tiles',

    '', ''
)
app = web.application(urls, globals())
app.add_processor(override_method)


if web.config.get('_session') is None:
    session = web.session.Session(app, web.session.DBStore(model.db, 'cot_session'), {
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
            return render_bare.index(i.lat, i.lon)

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
            return json.write({
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
            return json.write({
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
            return json.write({
                "status": "ok",
                "message": None,
                "data": None
            })


class dashboard:
    def GET(self):
        if session.user.name == "Anonymous":
            raise web.seeother("/dashboard/login")
        yays = model.get_reviews(writer=session.user.name, happy=True)
        nays = model.get_reviews(writer=session.user.name, happy=False)
        favs = model.get_reviews(writer=session.user.name, favourite=True)
        return render.dashboard(session.user.name, yays, nays, favs)

class dashboard_new:
    def GET(self):
        return render.dashboard_new()

    def POST(self):
        inp = web.input(name=None, email=None, password1=None, password2=None)

        if inp.password1 != inp.password2:
            return render.dashboard_new(error="Passwords don't match")

        if model.get_user(name=inp.name):
            return render.dashboard_new(error="Username taken")

        if model.get_user(email=inp.email):
            return render.dashboard_new(error="A user already has that address")

        model.new_user(inp.name, inp.email, inp.password1)
        session.user = User(model.get_user(name=inp.name, password=inp.password1))

        raise web.seeother("/")

class dashboard_login:
    def GET(self):
        return render.dashboard_login()

    def POST(self):
        inp = web.input(name=None, password=None, return_to="/dashboard")

        if not inp.name or not inp.password:
            return render.dashboard_login(inp.name, "Missing name or password")

        user = model.get_user(name=inp.name, password=inp.password)

        if not user:
            return render.dashboard_login(inp.name, "No user with those details")

        session.user = User(user)

        raise web.seeother("/")

class dashboard_logout:
    def GET(self):
        # FIXME: used by mobile
        session.user = User(model.get_user(name="Anonymous"))
        raise web.seeother("/")

    def POST(self):
        session.user = User(model.get_user(name="Anonymous"))
        raise web.seeother("/")

class dashboard_reset:
    def GET(self):
        return render.dashboard_reset()

    def POST(self):
        inp = web.input(name=None, email=None)

        if not inp.name and not inp.email:
            return render.dashboard_reset(error="Missing name or email")

        user = model.get_user(name=inp.name) or model.get_user(email=inp.email)

        if not user or user.name == "Anonymous":
            return render.dashboard_login(error="No user with those details")

        pw = generate_password()
        model.set_user_password(user.name, pw)
        web.sendmail(
            'Rate Here, Rate Now <shish+rhrn@shishnet.org>',
            user.email,
            '[RHRN] Password Reset',
            "Your new password is "+pw+
            "\n\nLog in at http://www.ratehereratenow.com/dashboard/login"+
            "\n\nSee you in a moment!"+
            "\n\n    -- The Rate Here, Rate Now Team"
        )

        return render.dashboard_reset_sent()

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

        (lat0, lon0) = num2deg(int(x)-1, int(y)-1, int(zoom))
        (lat1, lon1) = num2deg(int(x),   int(y),   int(zoom))
        (lat2, lon2) = num2deg(int(x)+1, int(y)+1, int(zoom))
        (lat3, lon3) = num2deg(int(x)+2, int(y)+2, int(zoom))
        (latd, lond) = (abs(lat1-lat2), abs(lon1-lon2))

        rs = list(model.get_reviews(bbox=[
            lon0, lat0,
            lon3, lat3
        ]))

        im = Image.new('RGBA', (256, 256))

        if rs:
            for x in range(0, 256):
                for y in range(0, 256):
                    lat = lat1 + (lat2-lat1) * y/256
                    lon = lon1 + (lon2-lon1) * x/256
                    goodness = 0
                    badness = 0
                    for r in rs:
                        d = math.sqrt(math.pow(lat-r.lat, 2) + math.pow(lon-r.lon, 2))
                        if d < 0.001:
                            if r.happy:
                                goodness = goodness + (0.001 - d) * 1000
                            else:
                                badness = badness + (0.001 - d) * 1000
                    good_hue = 2.0/6
                    bad_hue = 0.0/6
                    mid = (good_hue + bad_hue) / 2
                    if goodness - badness == 0:
                        hue = mid
                        alp = 0
                    else:
                        ratio = (goodness - badness) / (goodness + badness)
                        hue = mid + mid * ratio
                        alp = 63 * min(1, max(goodness, badness))
                    sat = 1
                    val = 1
                    (r, g, b) = colorsys.hsv_to_rgb(hue, sat, val)
                    im.putpixel(
                        (x, y),
                        (r*256, g*256, b*256, alp)
                        #(x, y, x, y)
                    )

        buf = StringIO.StringIO()
        im.save(buf, format= 'PNG')

        file(cache_file, "w").write(buf.getvalue())

        return buf.getvalue()

if __name__ == "__main__":
    app.run()

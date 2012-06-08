#!/usr/bin/python

import web
import model
import json
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
            return render_bare.new_review(i.id, i.lat, i.lon)
        if id == None:
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

if __name__ == "__main__":
    app.run()

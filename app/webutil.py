
import web
import hashlib
import random
import re
import math


def override_method(handler):
    web.ctx.method = web.input().get("_method", web.ctx.method)
    return handler()


class DefaultingSession(web.session.Session):
    def _save(self):
        current_values = dict(self)
        del current_values['session_id']
        del current_values['ip']

        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        if not self.get('_killed') and current_values != self._initializer:
            web.setcookie(cookie_name, self.session_id, domain=cookie_domain)
            self.store[self.session_id] = dict(self)
        else:
            if web.cookies().get(cookie_name):
                web.setcookie(cookie_name, self.session_id, expires=-1, domain=cookie_domain)


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


def clamp(a, val, b):
    low = min(a, b)
    high = max(a, b)
    if val < low:
        val = low
    if val > high:
        val = high
    return val

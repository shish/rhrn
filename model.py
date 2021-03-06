import web
import time
import hashlib
import webutil
import os, urlparse

db_info = urlparse.urlparse(os.environ['DB_DSN'])
db = web.database(
    dbn=db_info.scheme,
    host=db_info.hostname,
    port=db_info.port,
    db=db_info.path.strip("/"),
    user=db_info.username,
    pw=db_info.password,
)


# ============================================================================
# users

def new_user(name, email, token):
    db.insert('rh_user',
        name=name,
        email=email,
        token=token
    )

def get_user(name=None, email=None, token=None):
    wheres = []
    if name is not None:
        wheres.append("(lower(name) = lower($name))")
    if email is not None:
        wheres.append("(lower(email) = lower($email))")
    if token is not None:
        wheres.append("(token = $token)")

    users = list(db.select('rh_user',
        where=" AND ".join(wheres),
        vars=locals()
    ))

    if users:
        return users[0]
    else:
        return None

def set_user_token_by_email(email, token):
    db.update('rh_user',
        where="email = $email",
        vars=locals(),
        token=token
    )

def set_user_meta_by_email(email, meta):
    db.update('rh_user',
        where="email = $email",
        vars=locals(),
        janrain_meta=meta
    )


# ============================================================================
# comments

def get_reviews(bbox=None, writer=None, happy=None, favourite=None, notwriter=None):
    wheres = []

    if bbox:
        lon = (abs(bbox[0]) + abs(bbox[2])) / 2
        lat = (abs(bbox[1]) + abs(bbox[3])) / 2
        lon_min = min(bbox[0], bbox[2])
        lon_max = max(bbox[0], bbox[2])
        lat_min = min(bbox[1], bbox[3])
        lat_max = max(bbox[1], bbox[3])
        wheres.append("(lon BETWEEN $lon_min AND $lon_max)")
        wheres.append("(lat BETWEEN $lat_min AND $lat_max)")

    if writer:
        wheres.append("(writer ILIKE $writer)")

    if happy == True:
        wheres.append("(happy)")
    if happy == False:
        wheres.append("(NOT happy)")

    if favourite:
        wheres.append("(favourite)")

    if notwriter:
        wheres.append("(writer NOT ILIKE $notwriter)")

    return db.select('rh_review',
        where=" AND ".join(wheres),
        order="date_posted DESC",
        limit=500,
        vars=locals()
    )

def get_reviews_point(lon, lat):
    return db.select('rh_review',
        what="*, sqrt(pow(lon-$lon, 2) + pow(lat-$lat, 2)) AS dist",
        order="dist ASC",
        limit=50,
        vars=locals()
    )

def get_review(id):
    l = db.select('rh_review',
        where="id=$id",
        vars=locals()
    )
    if l:
        return l[0]
    else:
        return None

def new_review(writer, writer_ip, happy, lon, lat, content, volume, danger, crowds):
    db.insert('rh_review',
        writer = writer,
        writer_ip = writer_ip,
        happy = happy,
        lon = lon,
        lat = lat,
        content = content,
        volume = volume,
        danger = danger,
        crowds = crowds
    )

def del_review(id):
    db.delete('rh_review',
        where="id=$id",
        vars=locals()
    )


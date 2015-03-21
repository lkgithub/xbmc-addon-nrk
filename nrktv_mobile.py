# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import datetime
from requests import Session
import xbmcaddon

FAKE_PROXY_FOR = xbmcaddon.Addon().getSetting("x-forwarded-for")

session = Session()
session.headers['User-Agent'] = 'xbmc.org'
session.headers['app-version-android'] = '51'

if FAKE_PROXY_FOR:
    session.headers['X-Forwarded-For'] = FAKE_PROXY_FOR

_image_url = "http://m.nrk.no/m/img?kaleidoId=%s&width=%d"


class Model(object):
    id = None
    title = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Category(Model):
    @staticmethod
    def from_response(r):
        return Category(
            title=r['displayValue'],
            id=r['categoryId'],
        )


class Channel(Model):
    media_url = None

    @staticmethod
    def from_response(r):
        return Channel(
            title=r['title'],
            id=r['channelId'],
            media_url=r['mediaUrl'],
            thumb=_image_url % (r['imageId'], 250),
            fanart=_image_url % (r['imageId'], 1920),
        )


class Program(Model):
    description = None
    episode = None
    """Episode number, name or date as string."""

    aired = None
    """Date and time aired as :class:`datetime.datetime`"""

    duration = None
    """In seconds"""

    category = None
    """:class:`Category`"""

    legal_age = None
    image_id = None
    media_urls = None
    available = True

    @staticmethod
    def from_response(r):
        category = Category.from_response(r['category']) if 'category' in r \
            else None

        aired = None
        try:
            aired = datetime.datetime.fromtimestamp(
                int(r.get('usageRights', {}).get('availableFrom', 0)/1000))
        except (ValueError, OverflowError, OSError):
            pass

        media_urls = []
        if 'parts' in r:
            parts = sorted(r['parts'], key=lambda x: x['part'])
            media_urls = [part['mediaUrl'] for part in parts]
        elif 'mediaUrl' in r:
            media_urls = [r['mediaUrl']]

        return Program(
            id=r['programId'],
            title=r['title'].strip(),
            category=category,
            description=r.get('description'),
            duration=int(r.get('duration', 0)/1000),
            image_id=r['imageId'],
            legal_age=r.get('legalAge') or r.get('aldersgrense'),
            media_urls=media_urls,
            thumb=_image_url % (r['imageId'], 250),
            fanart=_image_url % (r['imageId'], 1920),
            episode=r.get('episodeNumberOrDate'),
            aired=aired,
            available=r.get('isAvailable', True)
        )


def _get(path):
    r = session.get("http://m.nrk.no/tvapi/v1" + path)
    r.raise_for_status()
    return r.json()


def recommended_programs(category_id='all-programs'):
    return [Program.from_response(item) for item in
            _get('/categories/%s/recommendedprograms' % category_id)]


def popular_programs(category_id='all-programs'):
    return [Program.from_response(item) for item in
            _get('/categories/%s/popularprograms' % category_id)]


def recent_programs(category_id='all-programs'):
    return [Program.from_response(item) for item in
            _get('/categories/%s/recentlysentprograms' % category_id)]


def episodes(series_id):
    return [Program.from_response(item) for item in
            _get('/series/%s' % series_id)['programs']]


def program(program_id):
    return Program.from_response(_get('/programs/%s' % program_id))


def channels():
    return [Channel.from_response(item) for item in _get('/channels')]


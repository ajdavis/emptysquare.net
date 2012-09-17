#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import re
import json
import urllib
import urllib2
from xml.dom import minidom

import flickrapi
import tornado.web
from tornado.web import URLSpec, RequestHandler as RQ

api_key = '24b43252c30181f08bd549edbb3ed394'

this_dir = os.path.dirname(__file__)

emptysquare_collection = []
sets = []
set_slug2photos = {}

# From http://github.com/facebook/tornado/blob/master/website/markdown/extensions/toc.py
# This is exactly the same as Django's slugify
def slugify(value):
    """ Slugify a string, to make it URL friendly. """
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+','-',value)

def parse_flickr_json(json_string):
    """
    @param json_string: Like jsonFlickrApi({'key':'value', ...})
    @return:            A native Python object, like dictionary or list
    """
    try:
        middle_part = json_string.split('jsonFlickrApi(')[-1].split(')')[0]
    except:
        raise Exception('JSON from Flickr in unexpected format: %s' % repr(json_string))

    return json.loads(middle_part)

def dump_json(obj):
    """
    @param obj:     A native Python object, like dictionary or list
    @return:        A string, the object dumped as pretty, parsable JSON
    """
    return json.dumps(obj, sort_keys=True, indent='    ')

class JSONFlickr(object):
    def __init__(self, api_key):
        """
        @param api_key:  A Flickr API key
        """
        self.flickr = flickrapi.FlickrAPI(api_key)

    def __getattr__(self, attr):
        def f(**kwargs):
            kwargs_copy = kwargs.copy()
            kwargs_copy['format'] = 'json'
            return parse_flickr_json(
                getattr(self.flickr, attr)(**kwargs_copy)
            )

        return f

def write_sitemap(prefix, sets, set_slug2photos, sitemap_filename):
    """
    Write a Google-compatible sitemap, like so:

    <urlset xmlns="http://www.google.com/schemas/sitemap/0.9"
      xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
      xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
      <url>
        <loc>http://www.example.com/foo.html</loc>
        <image:image>
           <image:loc>http://example.com/image.jpg</image:loc>
        </image:image>
      </url>
    </urlset>

    sets is like:

    [{'slug':slug, ...}, ... ]

    set_slug2photos is like:

    {'slug': {'id':'1234', 'photo':[{'title':title, 'source':url, ...}, ...], ...}, ...}

    @param prefix:              The first part of photo set URLs, e.g., 'http://emptysquare.net/photography'
    @param sets:                The Flickr photo sets' info, as JSON dictionary
    @param set_slug2photos:     A map: slug => individual set's JSON dictionary
    @param sitemap_filename:    A string, the filename in which to write the XML
    """
    document = minidom.Document()

    def create_and_append(parent, node_name):
        node = document.createElement(node_name)
        parent.appendChild(node)
        return node

    urlset = create_and_append(document, 'urlset')
    urlset.setAttribute("xmlns", "http://www.google.com/schemas/sitemap/0.9")
    urlset.setAttribute("xmlns:image", "http://www.google.com/schemas/sitemap-image/1.1")
    # Uncomment if for some reason you ever include a video link
    #urlset.setAttribute("xmlns:video", "http://www.google.com/schemas/sitemap-video/1.1")

    for _set in sets:
        url = create_and_append(urlset, 'url')

        loc = create_and_append(url, 'loc')

        # Construct URL like http://emptysquare.net/photography/homeless-shelters/#1/
        loc.appendChild(document.createTextNode((
                prefix + _set['slug'] if prefix.endswith('/') else prefix + '/' + _set['slug']
            ) + '/#1/'
        ))

        if _set['slug'] in set_slug2photos:
            photos = set_slug2photos[_set['slug']].get('photo')
            if photos:
                source = photos[0]['source']
                image_image = create_and_append(url, 'image:image')
                image_loc = create_and_append(image_image, 'image:loc')
                image_loc.appendChild(document.createTextNode(source))

    for page in special_set_slugs:
        url = create_and_append(urlset, 'url')

        loc = create_and_append(url, 'loc')

        # Construct URL like http://emptysquare.net/photography/bio/
        loc.appendChild(document.createTextNode(
            prefix + page if prefix.endswith('/') else prefix + '/' + page
        ))
    
    with open(sitemap_filename, 'w') as f:
        f.write(document.toprettyxml(indent="  ", encoding="UTF-8"))

def read_flickr_collection(flickr_username, collection_name):
    global emptysquare_collection, sets, set_slug2photos

    json_flickr = JSONFlickr(api_key)

    print('Getting user id')
    user_id = json_flickr.people_findByUsername(
        username=flickr_username, format="json"
    )['user']['nsid']

    print(user_id)

    print('Getting collections')
    collection_tree = json_flickr.collections_getTree(user_id=user_id, collection_id=0)['collections']['collection']

    try:
        # TODO: recurse, find collection even if isn't top-level
        emptysquare_collection = [
            collection for collection in collection_tree
            if collection['title'] == collection_name
        ][0]
    except IndexError:
        raise Exception("Couldn't find Flickr collection named %s" % repr(collection_name))

    for _set in emptysquare_collection['set']:
        slug = slugify(_set['title'])
        _set['slug'] = slug
        print('Reading photoset %s' % repr(_set['title']))
        photos = json_flickr.photosets_getPhotos(photoset_id=_set['id'])['photoset']

        # Add image URLs to the photo info returned by photosets_getPhotos()
        for photo in photos['photo']:
            photo['flickr_url'] = 'http://www.flickr.com/photos/%s/%s' % (
                flickr_username, photo['id']
            )

            sizes = json_flickr.photos_getSizes(photo_id=photo['id'])['sizes']['size']

            try:
                medium_640_size = [
                    size for size in sizes
                    if size['label'] == 'Medium 640'
                ][0]

                # Download the photo -- Flickr's static URLs change occasionally, so we need to host the
                # photo ourselves
                img_path = 'photography/images'
                if not os.path.exists(img_path):
                    os.makedirs(img_path)
                response = urllib2.urlopen(medium_640_size['source'])
                fname = os.path.join(img_path, slugify(photo['title'] + '-' + photo['id']) + '.jpg')
                with open(fname, 'wb+') as f:
                    f.write(response.read())
                photo['source'] = '/' + fname
            except IndexError:
                raise Exception(
                    "Couldn't find 'Medium 640' size for photo %s" % repr(photo['title'])
                )

        # Save for write_sitemap() and generate_html()
        set_slug2photos[slug] = photos

def index_for_set_slug(slug):
    return [
        index for index, a_set in enumerate(emptysquare_collection['set'])
        if a_set['slug'] == slug
    ][0]

def emptysquare_set_photos(slug):
    return set_slug2photos[slug]

special_set_slugs = ['exhibitions', 'bio', 'contact']

class StaticHandler(tornado.web.RequestHandler):
    """
    Instead of writing HTML to an output socket, this handler's render()
    method stores the HTML in self.html
    """
    def finish(self, chunk=None):
        self.html = chunk

class SetHandler(StaticHandler):
    def get(self, slug):
        sets = emptysquare_collection['set']
        current_set_index = index_for_set_slug(slug)

        next_set_slug = (
            sets[current_set_index + 1]['slug']
            if current_set_index + 1 < len(sets)
            else special_set_slugs[0]
        )

        self.render(
            "templates/set.html",
            body_class='set',
            sets=sets,
            current_slug=slug,
            current_set_index=current_set_index,
            photos=emptysquare_set_photos(slug),
            next_set_slug=next_set_slug,
        )

class ExhibitionsHandler(StaticHandler):
    def get(self):
        self.render(
            "templates/exhibitions.html",
            body_class='page',
            sets=emptysquare_collection['set'],
            current_slug='exhibitions',
            current_set_index=-1,
            next_set_slug='bio'
        )

class BioHandler(StaticHandler):
    def get(self):
        self.render(
            "templates/bio.html",
            body_class='page',
            sets=emptysquare_collection['set'],
            current_slug='bio',
            current_set_index=-1,
            next_set_slug='contact'
        )

class ContactHandler(StaticHandler):
    def get(self):
        self.render(
            "templates/contact.html",
            body_class='page',
            sets=emptysquare_collection['set'],
            current_slug='contact',
            current_set_index=-1,
            next_set_slug=emptysquare_collection['set'][0]['slug']
        )

# Use Tornado's application machinery to manage URLs, but don't actually run a Tornado
# server -- just render all the templates to static HTML that the user is responsible
# for uploading to a webserver
settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "autoescape": None,
}

application = tornado.web.Application([
    URLSpec(r'/photography/exhibitions/', ExhibitionsHandler, name='exhibitions'),
    URLSpec(r'/photography/bio/', BioHandler, name='bio'),
    URLSpec(r'/photography/contact/', ContactHandler, name='contact'),
    URLSpec(r'/photography/(\S+)/', SetHandler, name='set'),
], **settings)


class Permissive:
    """
    I'll let you do anything
    """
    def __getattr__(self, item):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __setattr__(self, key, value):
        return self

    def __nonzero__(self):
        return False # I *am* zero

def render_path(path):
    for spec in application.handlers[0][1]:
        match = spec.regex.match(path)
        if match:
            def unquote(s):
                if s is None: return s
                return urllib.unquote(s)
            handler = spec.handler_class(application, Permissive(), **spec.kwargs)
            # Pass matched groups to the handler. Since
            # match.groups() includes both named and unnamed groups,
            # we want to use either groups or groupdict but not both.
            kwargs = dict((k, unquote(v))
                          for (k, v) in match.groupdict().iteritems())
            if kwargs:
                args = []
            else:
                args = [unquote(s) for s in match.groups()]
            break

    handler.get(*args, **kwargs)
    return handler.html

def generate_html():
    paths = [
        application.reverse_url('set', a_set['slug'])
        for a_set in emptysquare_collection['set']
    ] + [ application.reverse_url(slug) for slug in special_set_slugs ]

    for path in paths:
        print(path)
        dest_dir = os.path.join(this_dir, path).lstrip('/')

        try: os.makedirs(dest_dir)
        except: pass

        fullpath = os.path.join(dest_dir, 'index.html')
        print('Writing %s' % fullpath)
        with open(fullpath, 'w+') as f:
            f.write(render_path(path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update emptysquare gallery from your Flickr account')
    parser.add_argument(
        dest='flickr_username',
        action='store',
        help='Your Flickr username',
    )

    parser.add_argument(
        dest='collection_name',
        action='store',
        help='The (case-sensitive) name of the Flickr collection to use',
    )

    args = parser.parse_args()

    read_flickr_collection(args.flickr_username, args.collection_name)

    print('Writing sitemap')
    write_sitemap(
        'http://emptysquare.net/photography',
        emptysquare_collection['set'],
        set_slug2photos,
        'static/sitemap.xml'
    )

    print('Generating HTML')
    generate_html()

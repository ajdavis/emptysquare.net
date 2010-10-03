#!/usr/bin/env python
import os
import logging
import simplejson
import re

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.autoreload
from tornado.web import URLSpec

logging.basicConfig(filename='emptysquare.log', level=logging.DEBUG)

def emptysquare_collection(rv=[None]):
    if not rv[0]:
        # cache
        with open('emptysquare_collection.json') as f:
            rv[0] = simplejson.loads(f.read())
    
    return rv[0]

def index_for_set_slug(slug, rv={}):
    if slug not in rv:
        # cache
        try:
            index = [
                index for index, a_set in enumerate(emptysquare_collection()['set'])
                if a_set['slug'] == slug
            ][0]
        except IndexError:
            raise tornado.web.HTTPError(404, 'No set with slug %s' % repr(slug))
        
        rv['slug'] = index
    
    return rv['slug']

def emptysquare_set_photos(slug, rv={}):
    if slug not in rv:
        # cache
        with open('%s.set.json' % slug) as f:
            rv[slug] = simplejson.loads(f.read())
    
    return rv[slug]

class PhotographyHandler(tornado.web.RequestHandler):
    def get(self):
        first_set = emptysquare_collection()['set'][0]
        self.redirect(self.reverse_url('set', first_set['slug']) + '#1/')

special_set_slugs = ['bio', 'contact']

class SetHandler(tornado.web.RequestHandler):
    def get(self, slug):
        sets = emptysquare_collection()['set']
        current_set_index = index_for_set_slug(slug)
        
        next_set_slug = (
            sets[current_set_index + 1]['slug']
            if current_set_index + 1 < len(sets)
            else special_set_slugs[0]
        )
        
        self.render(
            "templates/set.html",
            sets=sets,
            current_slug=slug,
            current_set_index=current_set_index,
            photos=emptysquare_set_photos(slug),
            next_set_slug=next_set_slug
        )

class PhotoForBotHandler(tornado.web.RequestHandler):
    """
    emptysquare.js script sets the FB like button's URL to a hashless URL:
    if visitor is at http://emptysquare.net/photography/fritz-christina/#1/,
    script sets like button's URL to http://emptysquare.net/photography/fritz-christina/1/.
    
    Similarly, our Google sitemap includes URLs like /1/, not /#1/.
    
    This handler responds to FB's or Googlebot's request for that
    page, and to human's inbound clicks from Google search results, or
    from Facebook if a person clicks on someone's activity, i.e. "Joe
    likes A. Jesse Jiryu Davis photography | Fritz & Christina on
    emptysquare.net."
    """
    def get(self, slug, photo_index):
	is_fb = 'facebookexternalhit' in self.request.headers['User-Agent'].lower()
	is_google = 'googlebot' in self.request.headers['User-Agent'].lower()
	logging.info('User-Agent: %s, is_fb = %s, is_google = %s' % (
	    repr(self.request.headers['User-Agent'].lower()),
	    repr(is_fb), repr(is_google)
	))
	
        if is_fb or is_google:
            # A visitor to my site has clicked "Like", so FB is scraping the
            # hashless URL.  Or Googlebot is following a URL in my sitemap.
            sets = emptysquare_collection()['set']
            current_set_index = index_for_set_slug(slug)
            return self.render(
                "templates/photo_for_facebook.html" if is_fb else "templates/photo_for_google.html",
                sets=sets,
                current_slug=slug,
                current_set_index=current_set_index,
                photos=emptysquare_set_photos(slug),
                # Remember that the photo index comes in 1-indexed
                photo_index=int(photo_index)-1
            )
        else:
            # A visitor has clicked someone's "like" activity on Facebook.com,
            # and is inbound to a hashless URL -- redirect them to the
            # human-readable page
            self.redirect(
                '%s#%s/' % (
                    self.reverse_url('set', slug),
                    photo_index
                )
            )

class BioHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(
            "templates/bio.html",
            sets=emptysquare_collection()['set'],
            current_slug='bio',
            current_set_index=-1,
            next_set_slug='contact'
        )

class ContactHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(
            "templates/contact.html",
            sets=emptysquare_collection()['set'],
            current_slug='contact',
            current_set_index=-1,
            next_set_slug=emptysquare_collection()['set'][0]['slug']
        )

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
}

application = tornado.web.Application([
    URLSpec(r'/photography/', PhotographyHandler, name='photography'),
    URLSpec(r'/photography/bio/', BioHandler, name='bio'),
    URLSpec(r'/photography/contact/', ContactHandler, name='contact'),
    URLSpec(r'/photography/(\S+)/(\d+)/', PhotoForBotHandler, name='photo_for_bot'),
    URLSpec(r'/photography/(\S+)/', SetHandler, name='set'),
], **settings)

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application, xheaders=True)
    print "Listening on port 8000"
    http_server.listen(8000)
    logging.info('logger up')
    #tornado.autoreload.start() 
    tornado.ioloop.IOLoop.instance().start()

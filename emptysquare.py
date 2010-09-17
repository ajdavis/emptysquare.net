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

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect(self.reverse_url('photography'))

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
            photos=simplejson.dumps(emptysquare_set_photos(slug)),
            next_set_slug=next_set_slug
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
    URLSpec(r'/', MainHandler),
    URLSpec(r'/photography/', PhotographyHandler, name='photography'),
    URLSpec(r'/photography/bio/', BioHandler, name='bio'),
    URLSpec(r'/photography/contact/', ContactHandler, name='contact'),
    URLSpec(r'/photography/(\S+)/', SetHandler, name='set'),
], **settings)

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(80)
    print 'listening on port 80'
    logging.info('logger up')
    # TODO: don't autoreload in production
    tornado.autoreload.start() 
    tornado.ioloop.IOLoop.instance().start()

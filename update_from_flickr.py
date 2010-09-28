#!/usr/bin/env python
"""
Requires Python 2.7 or better

notes 2010-09-17 emptysquare.net flickrapi

key 24b43252c30181f08bd549edbb3ed394
secret 2f58307171bc644e
"""

from __future__ import print_function
import re
import simplejson
import flickrapi
import argparse # Python 2.7 module
from xml.dom import minidom

api_key = '24b43252c30181f08bd549edbb3ed394'

parser = argparse.ArgumentParser(description='Update emptysquare gallery from your Flickr account')
parser.add_argument(dest='flickr_username', action='store', help='Your Flickr username')
parser.add_argument(dest='collection_name', action='store', help='The (case-sensitive) name of the Flickr collection to use')

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
    
    return simplejson.loads(middle_part)

def dump_json(obj):
    """
    @param obj:     A native Python object, like dictionary or list
    @return:        A string, the object dumped as pretty, parsable JSON
    """
    return simplejson.dumps(obj, sort_keys=True, indent='    ')

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
        
        # Construct URL like http://emptysquare.net/photography/homeless-shelters/1/
        loc.appendChild(document.createTextNode((
                prefix + _set['slug'] if prefix.endswith('/') else prefix + '/' + _set['slug']
            ) + '/1/'
        ))
        
        if _set['slug'] in set_slug2photos:
            photos = set_slug2photos[_set['slug']].get('photo')
            if photos:
                source = photos[0]['source']
                image_image = create_and_append(url, 'image:image')
                image_loc = create_and_append(image_image, 'image:loc')
                image_loc.appendChild(document.createTextNode(source))
    
    with open(sitemap_filename, 'w') as f:
        f.write(document.toprettyxml(indent="  ", encoding="UTF-8"))

def main(flickr_username, collection_name):
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
    
    sets = []
    set_slug2photos = {}
    for _set in emptysquare_collection['set']:
        slug = slugify(_set['title'])
        _set['slug'] = slug
        fname = '%s.set.json' % slug
        print('Caching photoset %s in file %s' % (repr(_set['title']), repr(fname)))
        photos = json_flickr.photosets_getPhotos(photoset_id=_set['id'])['photoset']
        
        # Add image URLs to the photo info returned by photosets_getPhotos()
        for photo in photos['photo']:
            sizes = json_flickr.photos_getSizes(photo_id=photo['id'])['sizes']['size']
            
            try:
                medium_640_size = [
                    size for size in sizes
                    if size['label'] == 'Medium 640'
                ][0]
                
                # Store the source URL in photo, so it'll get saved to the photo set's
                # cache file
                photo['source'] = medium_640_size['source']
            except IndexError:
                raise Exception(
                    "Couldn't find 'Medium 640' size for photo %s" % repr(photo['title'])
                )
        
        with open(fname, 'w') as f:
            f.write(dump_json(photos))
        
        # Save for write_sitemap()
        set_slug2photos[slug] = photos
    
    with open('emptysquare_collection.json', 'w') as f:
        f.write(dump_json(emptysquare_collection))
    
    print('Writing sitemap')
    write_sitemap('http://emptysquare.net/photography', emptysquare_collection['set'], set_slug2photos, 'static/sitemap.xml')
    
    print('Done')

if __name__ == '__main__':
    args = parser.parse_args()
    main(args.flickr_username, args.collection_name)
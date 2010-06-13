"""
A thin wrapper around the Flickr API.
"""

import hashlib
import json
import urllib


FLICKR_AUTH_END_POINT = 'http://www.flickr.com/services/auth/'
FLICKR_END_POINT = 'http://api.flickr.com/services/rest/'
ICON_TEMPLATE = 'http://farm%s.static.flickr.com/%s/buddyicons/%s.jpg'

GET = 'get'
POST = 'post'


class _FlickrResponse(object):
    def __init__(self, data):
        self.data = data

    def __getitem__(self, index):
        response = self.data[index]
        if type(response) in (tuple, list, dict):
            response = _FlickrResponse(response)
        return response

    def __getattr__(self, name):
        response = self.data.get(name)
        if type(response) in (tuple, list, dict):
            response = _FlickrResponse(response)
        return response

    def __len__(self):
        if type(self.data) in (tuple, list):
            return len(self.data)
        raise TypeError

    def __str__(self):
        return str(self.data)

    def icon_url(self):
        if 'iconserver' in self.data:
            iconserver = self.data['iconserver']
            if int(iconserver) > 0:
                return ICON_TEMPLATE % (
                    self.data['iconfarm'], iconserver, self.data['nsid'])
        return 'http://www.flickr.com/images/buddyicon.jpg'


class _FlickrCall(object):
    def __init__(self, api_key, method, secret=None):
        self.api_key = api_key
        self.method = method
        self.secret = secret

    def __getattr__(self, name):
        return _FlickrCall(
            self.api_key, '%s.%s' % (self.method, name), self.secret)

    def _get_call_query(self, **kwargs):
        return [(k, kwargs[k]) for k in sorted(kwargs.keys())]

    def _get_call_signature(self, **kwargs):
        return hashlib.md5(self.secret + ''.join([
            '%s%s' % (kv[0], kv[1])
            for kv in self._get_call_query(**kwargs)])).hexdigest()

    def __call__(self, method=GET, authenticated=False, **kwargs):
        request_args = {
            'api_key': self.api_key,
            'format': 'json',
            'method': 'flickr.%s' % self.method,
            'nojsoncallback': 1,
        }
        request_args.update(kwargs)
        if authenticated:
            request_args['api_sig'] = self._get_call_signature(**request_args)
        request_query = urllib.urlencode(self._get_call_query(**request_args))

        if method == POST:
            request = (FLICKR_END_POINT, request_query)
        else:
            request = ('%s?%s' % (FLICKR_END_POINT, request_query),)
        return _FlickrResponse(json.loads(urllib.urlopen(*request).read()))

    def post(self, **kwargs):
        return self.__call__(POST, **kwargs)


class Flickr(object):
    def __init__(self, api_key, secret=None):
        self.api_key = api_key
        self.secret = secret

    def __getattr__(self, name):
        return _FlickrCall(self.api_key, name, self.secret)

    def get_login_url(self, frob, perms='read'):
        call = _FlickrCall(self.api_key, None, self.secret)
        request_args = {
            'api_key': self.api_key,
            'frob': frob,
            'perms': perms,
        }
        request_args['api_sig'] = call._get_call_signature(**request_args)
        return '%s?%s' % (
            FLICKR_AUTH_END_POINT, urllib.urlencode(request_args), )


def friends_example():
    flickr = Flickr('API_KEY', 'API_SECRET')

    user_nsid = flickr.people.findByEmail(
        find_email='john@sneeu.com').user.nsid
    friends = flickr.contacts.getPublicList(user_id=user_nsid)
    for friend in friends.contacts.contact:
        print '<li><img src="%s" /><span>%s</span></li>' % (
            friend.icon_url(), friend.username)


def auth_example():
    flickr = Flickr('API_KEY', 'API_SECRET')

    frob = flickr.auth.getFrob(authenticated=True).frob._content

    raw_input("Hit enter after authenticating at: %s" % \
        flickr.get_login_url(frob))

    token = flickr.auth.getToken(authenticated=True, frob=frob)
    print token

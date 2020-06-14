"""Defines specific links that should be immediately redirected elsewhere."""

import webapp2


redirection_map = {
    ## EXAMPLE: Old home page links.
    # '/perts': '/',
    # '/PERTS': '/',
}


class RedirectionHandler(webapp2.RequestHandler):
    def get(self):
        target_url = '{}?{}'.format(
            redirection_map[self.request.path], self.request.query_string)
        self.redirect(target_url)


app = webapp2.WSGIApplication(
    [(k, RedirectionHandler) for k, v in redirection_map.items()])

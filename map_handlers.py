"""URL Handlers designed to be simple wrappers over our map reduce jobs.
See map.py.
"""

import logging
import mapreduce
import webapp2

from api_handlers import ApiHandler
from model import (Practice,)
import config
import map as map_module  # don't collide with native function map()
import util


debug = util.is_development()


class MapHandler(ApiHandler):
    def preview(self, mapper, kind, params):
        del params['preview']
        if 'n' not in params:
            params['n'] = 10

        # Set up a fake job context for the mapper
        job_config = mapper.launch(preview_only=True)
        context = map_module.get_fake_context(job_config)

        # Get some entities to preview.
        results = self.api.get(kind, **params)
        before = [e.to_client_dict() for e in results]

        results = [mapper.do(context, e) for e in results]
        after = [e.to_client_dict() for e in results]

        self.write({
            'preview': True,
            'n': params['n'],
            'before': before,
            'after': after,
            'message': (
                "Warning: the results returned here are the result of a "
                "simple query-and-modify, not a true map reduce job. "
                "Also, no changes have been saved."),
        })


class TagChangeHandler(MapHandler):
    def get(self):
        params = self.get_params()
        mapper = map_module.TagChangeMapper()
        logging.info(u"TagChangeHandler {}".format(params))

        if params.get('preview', False):
            # Don't run the map reduce job, just show a sample of what it
            # would do.
            return self.preview(mapper, 'Practice', params)

        else:
            # Run it for real
            job_config = mapper.launch()
            self.write(job_config.job_id)


class StatusHandler(MapHandler):
    """Query status of a map reduce job.

    Returns: 'running', 'success', 'failed', or 'aborted'
    """
    def do(self, job_id):
        MapreduceJob = mapreduce.api.map_job.map_job_control.Job
        # The error message if the job id is wrong is confusing. Simplify it.
        try:
            job = MapreduceJob.get_job_by_id(job_id)
        except ValueError:
            raise Exception("Invalid job id: {}".format(job_id))

        return {
            'success': True,
            'data': job.get_status(),
        }

webapp2_config = {
    'webapp2_extras.sessions': {
        # Related to cookie security, see:
        # http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html
        'secret_key': config.session_cookie_secret_key,
    },
}

app = webapp2.WSGIApplication([
    ('/map/tag_change', TagChangeHandler),
    ('/map/status/(.*)', StatusHandler),
], config=webapp2_config, debug=debug)

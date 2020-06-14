// Angular service for tracking page engagement

angular.module('mskApp')
  .service('Engagement', ['$timeout', function Engagement($timeout) {

    'use strict';

    this.trackViewDurations = function (durations, params) {

      // Create Mixpanel calls at each of the specified durations
      // e.g. at 5, 30, and 60 seconds.

      if (durations) {
        forEach(durations, function (duration) {

          $timeout( function () {

            params['View Time'] = duration;
            mixpanel.track('Content View Duration', params);

          }, duration*1000);

        });
      }

    };

  }]);
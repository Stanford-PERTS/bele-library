// Angular service for handling social sharing functionality

angular.module('mskApp')
  .service('Share', ['$q', '$http', '$window', function Share($q, $http, $window) {

    'use strict';

    var self = this;

    var twitterCountUrl = 'https://cdn.api.twitter.com/1/urls/count.json?callback=JSON_CALLBACK&url=';
    var facebookCountUrl = 'https://graph.facebook.com/?callback=JSON_CALLBACK&id=';
    var pinterestCountUrl = 'https://api.pinterest.com/v1/urls/count.json?callback=JSON_CALLBACK&url=';

    // Facebook, Twitter, and NOT Google+ by default
    this.getShareCount = function () {

      var def = $q.defer();
      var location = $window.location.href.split('?')[0];
      var count = 0;

      $http.jsonp(facebookCountUrl + location)
        .then(function (response) {

          if (response.data && response.data.shares) {
            count += response.data.shares;
          }

          return $http.jsonp(twitterCountUrl + location);

        }).then(function (response) {

          if (response.data && response.data.count) {
            count += response.data.count;
          }

          def.resolve(self.stringifyCount(count));

        }, function (error) {
          def.reject(error);
        });

      return def.promise;

    };

    // Make more attractive count strings aka 15000 = 15k
    this.stringifyCount = function (count) {

      if (count >= 1000000) {
        return Number(count / 1000000).toFixed(2) + 'M';
      } else if (count >= 100000) {
        return Number(count / 1000).toFixed(0) + 'K';
      } else if (count >= 10000) {
        return Number(count / 1000).toFixed(1) + 'K';
      } else if (count >= 1000) {
        return Number(count / 1000).toFixed(1) + 'K';
      } else {
        return count;
      }

    };

  }]);
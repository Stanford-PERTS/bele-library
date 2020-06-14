// Angular service for working with Mindset Kit API

angular.module('mskApp')
  .service('QueryParams', ['$window', function Api($window) {

    'use strict';

    // Making our own $location.search() setter
    this.set = function(params) {

      var queryString = '';

      if (!($.isEmptyObject(params))) {

        queryString += '?q=';

        if (params.q) {
          queryString += encodeURI(params.q);
          delete params.q;
        }

        angular.forEach(params, function (value, key) {

          if (value && value.length > 0) {
            if (Array.isArray(value) && value.length > 1) {
              angular.forEach(value, function(arrayValue) {
                queryString += '&' + key + '=' + encodeURI(arrayValue);    
              });
            } else {
              queryString += '&' + key + '=' + encodeURI(value);
            }
          }

        });

      }

      window.history.pushState('', 'BELE Library - Search', queryString);
      return queryString;

    };

    // Making our own $location.search() getter
    this.get = function() {

      var search = $window.location.search.split('?')[1];
      var params = [];
      var keyPairs = {};

      if (search) {

        if (search && search.indexOf('&') > -1) {
          params = search.split('&');
        } else {
          params = [search];
        }

        if (!($.isEmptyObject(params))) {

          angular.forEach(params, function(param) {
            if (param.indexOf('=') > -1) {
              var key = param.split('=')[0];
              var value = param.split('=')[1];
              // Check if key already in pairs, make into array
              if (keyPairs[key] !== undefined) {
                // Check if value is already an array
                if (Array.isArray(keyPairs[key])) {
                  keyPairs[key].push(value);
                } else {
                  keyPairs[key] = [keyPairs[key], value];
                }
              } else {
                keyPairs[key] = value;
              }
            }
          });

        }

      }

      return keyPairs;
    };

  }]);

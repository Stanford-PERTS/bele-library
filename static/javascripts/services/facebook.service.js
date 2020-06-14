// Angular service for handling Facebook API calls

angular.module('mskApp')
  .service('Facebook', ['$q', 'Api', function Facebook($q, Api) {

    'use strict';

    // What permissions we request from user's facebook accounts.
    var facebookPermissions = 'public_profile,email';
    var shouldSubscribe = false;

    var auth = function(type) {

      var def = $q.defer(); 

      FB.login(function (response) {

        if (response.authResponse) {
          // Successfully authorized
          var data = {
            auth_type: 'facebook',
            facebook_access_token: response.authResponse.accessToken,
          };

          // Adds subscribe if set to true
          if (shouldSubscribe) {
            data.should_subscribe = shouldSubscribe;
          }

          Api.auth[type](data)
            .then(function (response) {
              def.resolve(response);
            }, function (error) {
              def.reject(error);
            });

        } else {
          // User cancelled login or did not fully authorize.
          def.reject('User cancelled login or did not fully authorize.');
        }

      }, {
        scope: facebookPermissions
      }); 

      return def.promise;     

    };

    // Facebook register function
    this.register = function(subscribe) {

      // Pass through subscription variable
      shouldSubscribe = subscribe;
      mixpanel.track('Sign Up', {
        'method': 'facebook'
      });
      return auth('register');

    };

    // Facebook login function
    this.login = function() {

      // Reset subscription variable
      shouldSubscribe = false;
      mixpanel.track('Login', {
        'method': 'facebook'
      });  
      return auth('login');

    };

  }]);
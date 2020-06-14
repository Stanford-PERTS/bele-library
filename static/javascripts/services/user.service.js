// Angular service for handing User object in Angular module

/* global mixpanel */

angular.module('mskApp')
  .service('User', ['Api', '$rootScope', '$http', '$q', function User(Api, $rootScope, $http, $q) {

    'use strict';

    var currentUser;  // set in ng-init expressions in base.html
    var self = this;
    var apiKey = 'AIzaSyA8tegl18bt3C1l8iz_RzWOaNj-9SMHO9A';

    this.currentUser = function () {
      return currentUser;
    };

    this.setUser = function (user) {

      if (user) {

        // Identify user in mixpanel.
        if ($rootScope.production) {
          mixpanel.identify(user);
        }

        Api.users.findById(user).then( function (response) {
          if (response.data) {

            currentUser = response.data;
            $rootScope.user = response.data;

            // Set properties on the mixpanel user
            if ($rootScope.production) {
              // Split properties between those set only once, and each time
              mixpanel.people.set_once({
                "$first_name": currentUser.first_name,
                "$last_name": currentUser.last_name,
                "$email": currentUser.email,    // only special properties need the $
                "$created": currentUser.created
              });
              mixpanel.people.set({
                "$last_login": currentUser.last_login
              });
            }

            // Sets superproperties for all Mixpanel calls
            mixpanel.register({
              'Signed In': true,
              'Email': currentUser.email,
              'Admin': currentUser.is_admin || false,
              'Account Type': currentUser._auth_id.split(':')[0]
            });

            self.getImage(currentUser)
              .then( function (response) {
                if (response) {
                  currentUser.image_url = response;
                }
                $rootScope.$broadcast('user:updated');
              }, function (error) {
                $rootScope.$broadcast('user:updated');
              });

          } else {
            // No user.
            mixpanel.register({
              'Signed In': false
            });
          }
        });
      } else {
        // No user.
        mixpanel.register({
          'Signed In': false
        });
      }

    };

    this.getImage = function (user) {

      var thisUser = user || currentUser;

      var def = $q.defer();

      if (thisUser) {

        if (thisUser.image_url) {

          def.resolve(thisUser.image_url.replace(/https?:/, ''));

        } else if (thisUser.facebook_id && thisUser.facebook_id !== 'None') {

          def.resolve('//graph.facebook.com/' + thisUser.facebook_id + '/picture?type=square');

        } else if (thisUser.email) {

          // var emailHash = CryptoJS.MD5(thisUser.email.toLowerCase());
          // var gravatarUrl = '//www.gravatar.com/avatar/' + emailHash + '?d=404';
          // $http.get(gravatarUrl).then( function (response) {
          //   if (response) {
          //     def.resolve(gravatarUrl);
          //   } else {
          //     def.reject('No image');
          //   }
          // }, function (error) {
          //   def.reject('No image');
          // });

          def.reject('No image');

        } else {
          def.reject('No image');
        }

      } else {
        def.reject('No user');
      }

      return def.promise;

    };

  }]);



// Directive for handling user images

angular.module('mskApp')
  .directive('userImage', ['User', function (User) {
    'use strict';
    return {
      restrict: 'A',
      scope: {
        user: '='
      },
      transclude: false, // we want to insert custom content inside the directive
      link: function(scope, element, attrs) {

        // Method to apply image
        scope.fetchImage = function () {

          var imageUrl;
          var user = scope.user;

          if (user) {

             User.getImage(user)
              .then( function (response) {
                if (response) {
                  element.attr('style', 'background-image: url("' + response + '");');
                }
              });
          }

        };

        // Set default user image
        element.attr('style', 'background-image: url("/static/images/default-user.png");');

        scope.$watch(function() { return scope.user; }, function() {

          if (scope.user && scope.user.uid) {
            scope.fetchImage();
          }

        });

      }
    };
  }]);
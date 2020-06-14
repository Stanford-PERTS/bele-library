angular.module('mskApp')
  .directive('searchResult', ['$window', 'Api', 'User', function ($window, Api, User) {
    'use strict';

    return {
      restrict: 'E',
      replace: true,
      transclude: true,
      scope: {
        result: '=',
        resultType: '=',
        profileResult: '=',
        isYours: '=',
        user: '=',
      },
      templateUrl: '/static/directives/search_result.html',

      link: function(scope, element, attrs) {
        scope.result.createdPrettyDate = scope.result && util.prettyDate(scope.result.created);
        scope.kind = util.getKind(scope.result.uid);
        scope.canEdit = false;

        if (User.currentUser() && scope.result.authors) {
          scope.canEdit = scope.result.authors.find(a => a === User.currentUser().uid) !== undefined;
        } else {
          scope.$on('user:updated', () => {
            if (scope.result.authors) {
              scope.canEdit = scope.result.authors.find(a => a === User.currentUser().uid) !== undefined;
            }
          });
        }
        // console.log('scope', scope.$root.user);
        // User.currentUser().subscribe(value => console.log('value', value));
        // scope.on('user:updated', function(event, data) {
        //   conosle.log('user updated', data);
        //   scope.canEdit = scope.result.authors.find(a => a === User.currentUser().uid) !== undefined
        // });

        // scope.imgFallback = 'https://via.placeholder.com/100x100';
        let { icon } = scope.result;
        switch (scope.kind) {
          case 'Book':
            scope.imgFallback = '/';
            break;
          case 'Page':
            scope.imgFallback = '/';
            break;
          default:
            scope.imgFallback = '/';
            break;
        }
        
        // TODO: standardize what form all images will come in
        let link = scope.imgFallback;
        if (icon) {
          try {
            icon = JSON.parse(icon);
          } catch(err) {
            console.info('Attempt to parse json failed. Falling back to alt representation.', err);
          }
          if (typeof(icon) === 'string') {
            link = icon;
          } else if (icon.hasOwnProperty('link')) {
            link = icon.link;
            link = link ? link + '?size=360' : link;
          }
        } else if (scope.kind === 'Chapter' && scope.result.bookIcon) {
          link = scope.result.bookIcon;
          link = link ? link + '?size=360' : link;
        }
        scope.iconSrc = link;

        // Use 'rejected' to show user if their own practice was rejected
        if (scope.profileResult && scope.isYours && scope.kind === 'Practice') {
          scope.rejected = (!scope.result.pending && !scope.result.listed);
        } else {
          
        }

        // Create user link if username is properly made
        if (scope.result.user && scope.result.user.username) {
          scope.userLink = '/users/' + scope.result.user.canonical_username;
        }

        // Determine type by look at content_type
        if (Array.isArray(scope.result.content_type)) {
          angular.forEach(scope.result.content_type, function(type) {
            if (type === 'video') { scope.isVideo = true; }
            if (type === 'files') { scope.hasFiles = true; }
          });
        } else {
          if (scope.result.content_type === 'video') { scope.isVideo = true; }
          if (scope.result.content_type === 'files') { scope.hasFiles = true; }
        }

        // Determine linking based on kind of content
        if (scope.kind === 'Practice') {
          scope.link = '/practices/' + scope.result.short_uid;
        } else if (scope.kind === 'Lesson') {
          scope.link = null;
        } else if (scope.kind === 'Page') {
          scope.link = '/pages/' + scope.result.short_uid;
          scope.editLink = '/pages/edit/' + scope.result.short_uid;
        } else if (scope.kind === 'Book') {
          scope.link = '/books/' + scope.result.short_uid;
          scope.editLink = '/books/manage/' + scope.result.short_uid;
        } else if (scope.kind === 'Chapter') {
          scope.link = '/books/' + scope.result.bookUID.replace('Book_', '') + '#' + scope.result.short_uid;
        }

        // Function to pull course paths
        scope.loadCourses = function() {
          if (scope.kind === 'Lesson' && !scope.loadingCourses) {

            scope.loadingCourses = true;

            Api.lessons.getThemes(scope.result)
              .then( function (response) {

                if (response.data && response.data.length) {

                  if (response.data.length === 1) {
                    $window.location.href = response.data[0].lesson_link;
                  } else {
                    scope.courses = response.data;
                    scope.link = scope.courses[0].lesson_link;
                    scope.loadingCourses = false;
                    scope.coursesFound = true;
                  }
                }

              });

          } else {
            // Error!
          }
        };
      }
    };
  }]);

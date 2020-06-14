angular.module('mskApp')
  .directive('discussion', ['User', 'Api', '$window', '$location', '$anchorScroll', function (User, Api, $window, $location, $anchorScroll) {
    'use strict';

    return {
      restrict: 'E',
      scope: {
        parentId: '=parent',
        type: '='
      },
      replace: true, // Replace with the template below
      transclude: true, // we want to insert custom content inside the directive
      templateUrl: '/static/directives/discussion.html',

      link: function(scope, element, attrs) {

        var minCommentLength = 8;

        if (attrs.type === 'lesson') {
          scope.isLesson = true;
        }

        scope.commentText = ''; // from textarea field
        scope.isHidden = false; // open or close discussion box
        scope.commentCount = 0;
        scope.comments = [];
        scope.user = User.currentUser(); // get user from User service

        scope.$on('user:updated', function(event, data) {
          scope.user = User.currentUser();
        });

        var viewLimit = 3; // limit on visible comments on load
        scope.page = 0;
        scope.canLoadMore = false;

        scope.fetchComments = function () {

          var params = {
            order: 'created',
            page: scope.page
          };

          // Determine id type
          if (attrs.type === 'practice') {
            params.practice_id = scope.parentId;
          } else if (attrs.type === 'lesson') {
            params.lesson_id = scope.parentId;
          } else {
            params.page_id = scope.parentId;
          }

          // Fetch comments by parent id
          Api.comments.fetch(params)
            .then( function (response) {

              if(!response.error && response.data.length > 0) {

                var comments = response.data;

                // Determine comment count and if more can be loaded
                scope.commentCount+=comments.length;
                if (comments.length === 10) {
                  scope.canLoadMore = true;
                }

                // Bucket comments into initial view and 'more'
                if (scope.page === 0) {
                  // If more than viewLimit, move extras into second array
                  if (scope.commentCount > viewLimit) {
                    scope.comments = comments.slice(0,viewLimit);
                    scope.moreComments = comments.slice(viewLimit);
                    scope.hasMore = true;
                  } else {
                    scope.comments = comments;
                  }
                } else {
                  forEach(comments, function (comment) {
                    scope.moreComments.push(comment);
                  });
                }
              }

              // Display discussion directive by adding 'active' class
              element.addClass('active');

            });

        };

        // Initial comment pull.
        scope.fetchComments();

        scope.reply = function (comment) {

          scope.commentText = '@' + comment.user.username + ': ';
          $location.hash('discussion');
          $anchorScroll();
          $('#commentBox').focus();

        };

        // Uploads and adds a comment to UI
        scope.addComment = function () {

          // Check that commentText has been entered
          if (scope.commentText.length > minCommentLength) {

            scope.postingComment = true;

            mixpanel.track('Added Comment', {
              'Content Id': scope.parentId,
              'Content Type': attrs.type
            });

            var params = {
              'body': scope.commentText
            };

            // Determine id type
            if (attrs.type === 'practice') {
              params.practice_id = scope.parentId;
            } else if (attrs.type === 'lesson') {
              params.lesson_id = scope.parentId;
            } else {
              params.page_id = scope.parentId;
            }

            Api.comments.create(params)
              .then( function (response) {

                if(!response.error) {

                  var comment = response.data;
                  comment.user = scope.user;

                  // Add to visible end of list depending on viewAll value
                  if (scope.viewAll) {
                    scope.moreComments.push(comment);
                  } else {
                    scope.comments.push(comment);
                  }
                  scope.commentCount += 1;
                  scope.commented = true;
                }

                scope.postingComment = false;

              });

          }

        };

        scope.cancelComment = function() {
          scope.commentText = '';
          scope.isHidden = false;
          scope.checkShowButton();
        };

        scope.deleteComment = function(comment) {

          if (confirm('Are you sure you want to remove this comment?')) {

            // Delete it!
            Api.comments.delete(comment.uid)
              .then( function (response) {

                scope.comments.remove(comment);
                if (scope.moreComments && scope.moreComments.length > 0) {
                  scope.moreComments.remove(comment);
                }

              });

          }

        };

        scope.checkShowButton = function () {
          if (scope.commentText.length > minCommentLength) {
            scope.showButton = true;
          } else {
            scope.showButton = false;
          }
        };

        scope.loadMore = function () {
          scope.canLoadMore = false;
          scope.page++;
          scope.fetchComments();
        };

      }
    };
  }]);
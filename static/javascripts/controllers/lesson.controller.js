// Angular controller for handling practice search page

angular.module('mskApp')
  .controller('LessonCtrl', ['$scope', '$window', 'Api', 'User', 'Share', 'Engagement', function ($scope, $window, Api, User, Share, Engagement) {

    'use strict';

    $scope.liked = false;
    $scope.lessonId = $window.location.pathname.split('/').pop().split('?')[0];
    $scope.themeId = $window.location.pathname.split('/')[1];
    $scope.topicId = $window.location.pathname.split('/')[2];

    $scope.showTranscription = false;

    var trackParams = {
      'Content Type': 'Lesson',
      'Content Id': $scope.lessonId,
      'Topic Id': $scope.topicId,
      'Theme Id': $scope.themeId
    };

    // Track content view
    mixpanel.track('View Content', trackParams);

    // Track time spent on lessons
    Engagement.trackViewDurations([15, 30, 60, 120], trackParams);

    // Get share counts
    Share.getShareCount().then(function (response) {
      $scope.shareCount = response;
    }, function (error) {
      $scope.shareCount = 0;
    });

    // Update user once it's been fetched.
    $scope.$on('user:updated', function(event, data) {
      $scope.user = User.currentUser();

      // Fetch practices if a user is found.
      if ($scope.user) {

        Api.votes.fetch($scope.lessonId, 'lesson')
          .then(function (response) {

            if (response.data && response.data.length > 0) {
              $scope.liked = response.data[0].vote_for;
              $scope.voteId = response.data[0].uid;
            } else {
              // None found...
            }
            $scope.voteFound = true;
          });
      }

    });

    $scope.toggleLike = function() {

      if ($scope.user && !$scope.loading) {
        if ($scope.liked) {
          $scope.unlikeLesson();
        } else {
          $scope.likeLesson();
        }
      } else {
        // Error.
      }

    };

    $scope.toggleTranscription = function() {

      $scope.showTranscription = !$scope.showTranscription;
      if ($scope.showTranscription) {
        mixpanel.track('View Transcript', trackParams);
      }

    };

    $scope.likeLesson = function() {

      $scope.liked = true;
      $scope.loading = true;

      mixpanel.track('Like Content', trackParams);

      Api.votes.create($scope.lessonId, 'lesson')
        .then(function (response) {
          // @todo: catch response.error
          $scope.loading = false;
          if (response.data) {
             $scope.voteId = response.data.uid;
          }
        });

    };

    $scope.unlikeLesson = function() {

      $scope.liked = false;
      $scope.loading = true;
      Api.votes.delete($scope.voteId)
        .then(function (response) {
          // @todo: catch response.error
          $scope.loading = false;
        });

    };

    $scope.trackDownload = function (fileName) {

      mixpanel.track('File Download', {
        'Content Type': 'Lesson',
        'Content Id': $scope.lessonId,
        'Topic Id': $scope.topicId,
        'Theme Id': $scope.themeId,
        'File Name': fileName
      });

    };

    // Function to send form on reflection exercises

    $scope.emailReflection = function () {

      $scope.emailErrorMessage = '';
      $scope.emailProcessing = true;
      var emailTo = $scope.emailTo || $scope.user.email;

      if ($scope.emailBody && $scope.emailBody.length > 5 && emailTo) {

        // Send reflection to email via API
        Api.sendReflectionEmail({
          'to_address': emailTo,
          'questions': $scope.emailQuestions,
          'reflection': $scope.emailBody
        }).then( function (response) {
          $scope.emailProcessing = false;
          $scope.emailSuccessMessage = true;
        });

        // Track 'Email Reflection'
        mixpanel.track('Email Reflection', {
          'Content Type': 'Lesson',
          'Content Id': $scope.lessonId,
          'Topic Id': $scope.topicId,
          'Theme Id': $scope.themeId
        });

      } else {

        $scope.emailErrorMessage = 'Reflection is too short.';
        $scope.emailProcessing = false;

      }
    };

    // MOVE EVERYTHING OUT OF LESSON.JS

  }]);


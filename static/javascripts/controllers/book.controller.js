// Angular controller for handling book search book

angular.module('mskApp')
  .controller('BookCtrl', ['$scope', '$window', 'Api', 'User', 'Share', 'Engagement', function ($scope, $window, Api, User, Share, Engagement) {
  
    'use strict';

    // Used to associate grade level integers with names
    $scope.gradeLevels = [
      'Kindergarten',
      '1st',
      '2nd',
      '3rd',
      '4th',
      '5th',
      '6th',
      '7th',
      '8th',
      '9th',
      '10th',
      '11th',
      '12th',
      'Postsecondary'
    ];

    $scope.liked = false;
    $scope.bookId = $window.location.pathname.split('/').pop().split('?')[0];

    var trackParams = {
      'Content Type': 'Book',
      'Content Id': $scope.bookId
    };

    console.log($scope);

    // Track content view
    mixpanel.track('View Content', trackParams);

    // Track time spent on book
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

      // Fetch books if a user is found.
      if ($scope.user) {

        Api.votes.fetch($scope.bookId, 'book')
          .then(function (response) {

            if (response.data && response.data.length > 0) {
              $scope.liked = response.data[0].vote_for;
              $scope.voteId = response.data[0].uid;
            } else {
              // None found.
            }

            $scope.voteFound = true;

          });
      }
    });

    $scope.toggleLike = function() {

      if ($scope.user && !$scope.loading) {
        if ($scope.liked) {
          $scope.unlikeBook();
        } else {
          $scope.likeBook();
        }
      } else {
        // Error.
      }

    };

    $scope.likeBook = function() {

      $scope.liked = true;
      $scope.loading = true;

      mixpanel.track('Like Content', trackParams);

      Api.votes.create($scope.bookId, 'book')
        .then(function (response) {
          // @todo: catch response.error
          $scope.loading = false;
          if (response.data) {
             $scope.voteId = response.data.uid;
          }
        });

    };

    $scope.unlikeBook = function() {

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
        'Content Type': 'Book',
        'Content Id': $scope.lessonId,
        'File Name': fileName
      });

    };

  }]);


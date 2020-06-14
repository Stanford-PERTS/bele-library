// Angular controller for handling practice search page

angular.module('mskApp')
  .controller('BookPageCtrl', ['$scope', '$window', 'Api', 'User', 'Share', 'Engagement', function ($scope, $window, Api, User, Share, Engagement) {

    'use strict';

    $scope.liked = false;
    $scope.pageId = $window.location.pathname.split('/').pop().split('?')[0];
    $scope.bookId = $window.location.pathname.split('/')[1];
    $scope.chapterId = $window.location.pathname.split('/')[2];

    $scope.showTranscription = false;

    var trackParams = {
      'Content Type': 'BookPage',
      'Content Id': $scope.pageId,
      'Chapter Id': $scope.chapterId,
      'Book Id': $scope.bookId
    };

    // Track content view
    mixpanel.track('View Content', trackParams);

    // Track time spent on pages
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

        Api.votes.fetch($scope.bookId, 'book')
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

    $scope.init = function(bookId) {
      $scope.bookId = bookId;
    };

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

    $scope.toggleTranscription = function() {

      $scope.showTranscription = !$scope.showTranscription;
      if ($scope.showTranscription) {
        mixpanel.track('View Transcript', trackParams);
      }

    };

    $scope.trackDownload = function (fileName) {

      mixpanel.track('File Download', {
        'Content Type': 'BookPage',
        'Content Id': $scope.pageId,
        'Chapter Id': $scope.chapterId,
        'Book Id': $scope.bookId,
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
          'Content Type': 'BookPage',
          'Content Id': $scope.pageId,
          'Chapter Id': $scope.chapterId,
          'Book Id': $scope.bookId
        });

      } else {

        $scope.emailErrorMessage = 'Reflection is too short.';
        $scope.emailProcessing = false;

      }
    };

    $scope.goTo = function(url) {
      window.location.href = url;
    };

    $scope.openAuthorsModal = function() {
      $('#authorsModal').modal('show'); 
    };

    $scope.handleClickRemoveAuthor = function (authorId, displayName) {
      $scope.authorPendingRemoval = { uid: authorId, name: displayName };
      $scope.$root.redirect = null;
      $('#authorsModal').modal('hide');
      $('#removeAuthorModal').modal('show');
    };

    $scope.handleConfirmRemoveAuthor = function (author) {
      $scope.removingAuthor = true;
      $scope.$root.redirect = null;

      Api.books.removeAuthor($scope.bookId, author.uid)
        .then(function (response) {
          if (response.data) {
            // The author modal is rendered server-side, so now we have to
            // reload.
            $window.location.reload();
          } else {
            throw new Error("Unable to remove author from page: " + author.uid);
          }
        });
    };

    $scope.handleCloseRemove = function() {
      $scope.openRemoveAuthorModal = false;
      $('#removeAuthorModal').modal('hide');
    };

    $scope.handleClickInviteAuthors = function() {
      console.log('handleClickInviteAuthors');
      $scope.$root.redirect = null;
      $scope.openAuthorshipModal = true;
      $('#authorsModal').modal('hide');
    };

    $scope.handleClickCloseAuthors = function() {
      $scope.openAuthorshipModal = false;
      $('#authorsModal').modal('hide');
    };

    // Hacks to deal with nested bootstrap modals
    $('#authorsModal').on('hidden.bs.modal', function () {
      if ($scope.openAuthorshipModal === true) {
        $('#authorshipModal').modal('show');
        let node = document.createElement("DIV");
        node.id = 'custom-backdrop';
        node.className = 'modal-backdrop fade in';
        document.body.appendChild(node);
      }
    });

    $(document).on('hidden.bs.modal', '#authorshipModal', function () {
      const node = document.getElementById('custom-backdrop');
      if (node) {
        document.body.removeChild(node);
      }
    });

  }]);


// Angular controller for handling page search page

angular.module('mskApp')
  .controller('PageCtrl', ['$scope', '$window', 'Api', 'User', 'Share', 'Engagement', function ($scope, $window, Api, User, Share, Engagement) {

    'use strict';

    $scope.pageId = $window.location.pathname.split('/').pop().split('?')[0];
    $scope.liked = false;

    $scope.expanded = {};

    var trackParams = {
      'Content Type': 'Page',
      'Content Id': $scope.pageId
    };

    // Track content view
    mixpanel.track('View Content', trackParams);

    $scope.contentProps = [
      'advancesEquity',
      'jsonProperties',
      'pageAcknowledgements',
      'pageCitations',
      'pageEvidence',
      'pageMaterials',
      'pageMeasures',
      'pagePreconditions',
      'pageTime',
      'relatedPages'
    ];

    const resetExpanded = (target = false) =>
      $scope.contentProps.forEach(
        (scopeProp) => $scope.expanded[scopeProp] = target
      );
    resetExpanded(true);
    $scope.setExpanded = function(propertyName) {
      const wasInitiallyExpanded = $scope.expanded[propertyName];
      // Toggle expand/collapse of target item
      $scope.expanded[propertyName] = !wasInitiallyExpanded;
    };

    $scope.doInit = (page) => {
      $scope.page = page;
    };

    // Update user once it's been fetched.
    $scope.$on('user:updated', function(event, data) {
      $scope.user = User.currentUser();

      // Fetch pages if a user is found.
      if ($scope.user) {

        Api.votes.fetch($scope.pageId, 'page')
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

      console.log($scope.user, $scope.loading, $scope.liked);

      if ($scope.user && !$scope.loading) {
        if ($scope.liked) {
          $scope.unlikePage();
        } else {
          console.log('liking page');
          $scope.likePage();
        }
      } else {
        // Error.
      }

    };

    $scope.likePage = function() {

      $scope.liked = true;
      $scope.loading = true;

      mixpanel.track('Like Content', trackParams);

      Api.votes.create($scope.pageId, 'page')
        .then(function (response) {
          // @todo: catch response.error
          $scope.loading = false;
          if (response.data) {
             $scope.voteId = response.data.uid;
          }
        });

    };

    $scope.unlikePage = function() {

      $scope.liked = false;
      $scope.loading = true;
      Api.votes.delete($scope.voteId)
        .then(function (response) {
          // @todo: catch response.error
          $scope.loading = false;
        });

    };

    $scope.print = function() {
      $window.print();
    };

    $scope.goTo = function(url) {
      window.location.href = url;
    };

    $scope.openAuthorsModal = function() {
      $('#authorsModal').modal('show');
    };

    $scope.openConfirmDeleteModal = function () {
      var longId = $scope.pageId;
      if (longId.split('_')[0] !== 'Page') {
        longId = 'Page_' + longId;
      }
      $scope.entityPendingDelete = {uid: longId};
      $('#confirmDeleteModal').modal('show');
    };

    $scope.handleClickInviteAuthors = function() {
      $scope.$root.redirect = null;
      $scope.openAuthorshipModal = true;
      $('#authorsModal').modal('hide');
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

      Api.pages.removeAuthor($scope.pageId, author.uid)
        .then(function (response) {
          if (response.data) {
            // The author modal is rendered server-side, so now we have to
            // reload.
            $window.location.reload();
          } else {
            throw new Error("Unable to remove editor from book: " + author.uid);
          }
        });
    };

    $scope.handleCloseRemove = function() {
      $scope.openRemoveAuthorModal = false;
      $('#removeAuthorModal').modal('hide');
    };

    $scope.handleClickCloseAuthors = function() {
      $scope.openAuthorshipModal = false;
      $('#authorsModal').modal('hide');
    };

    // Hacks to deal with nested bootstrap modals
    $('#authorsModal').on('hidden.bs.modal', function () {
      if ($scope.openAuthorshipModal === true) {
        $('#authorshipModal').modal('show');
        // CAM: what? supposed to be assignment?
        // $scope.openAuthorshipModal === false;
        $scope.openAuthorshipModal = false;
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


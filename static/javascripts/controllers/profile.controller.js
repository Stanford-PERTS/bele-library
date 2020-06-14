// Angular controller for profile pages

/* global util */

angular.module('mskApp')
  .controller('ProfileCtrl', ['$scope', '$q', 'Api', 'User', '$window',
    function ($scope, $q, Api, User, $window) {

    'use strict';

    $scope.resources = [];
    $scope.loading = true;
    $scope.password = '';
    $scope.repeatPassword = '';
    $scope.updating = false;
    $scope.updated = false;
    $scope.errorMessage = '';
    $scope.resultType = 'books';
    // Used for pagination
    $scope.pageSize = 20;
    $scope.page = 0;
    $scope.shouldPaginate = false;


    $scope.init = function(user) {
      if (user) {

        $scope.profileUser = user;
        $scope.fetchResults();

      } else {

        // Update user once it's been fetched.
        $scope.$on('user:updated', function(event, data) {

          $scope.profileUser = User.currentUser();

          // Fetch pages if a user is found.
          if ($scope.profileUser) {
            $scope.fetchResults();
          }

        });

      }
    };

    $scope.initEditBookModal = function() {
      $('#editBookModal').modal('show');
    };

    $scope.setResultType = function (type) {

      // Reset variables
      $scope.resultType = type;
      $scope.resources = [];

      $scope.fetchResults();
    };

    $scope.fetchResults = function () {

      $scope.loading = true;
      $scope.shouldPaginate = false;

      let functionNames;

      if ($scope.resultType === 'books') {
        functionNames = ['fetchBooks'];
      } else if ($scope.resultType === 'pages') {
        functionNames = ['fetchPages'];
      } else if ($scope.resultType === 'likes') {
        functionNames = ['fetchVotes'];
      }
      const promises = functionNames.map(functionName => Api.users[functionName]($scope.profileUser, $scope.page));
      $q.all(promises)
        .then(function (responses) {
          // Combine data from all responses into an array
          const data = responses.reduce((acc, curr) => acc = acc.concat(curr.data), []);
          console.log(functionNames[0], data);
          $scope.loading = false;

          if (data && data.length > 0) {

            // Handle pagination if page past 0
            if ($scope.page < 1) {
              $scope.resources = data;
            } else {
              $scope.resources = $scope.resources.concat(data);
            }

            // Fix view not updating after fetch
            forEach($scope.resources, function (result) {
              if(Array.isArray(result.tags)) {
                result.array = true;
              }
            });

            if (data.length >= $scope.pageSize) {
              $scope.shouldPaginate = true;
            }
          }
          return Promise.resolve();
        })
        .then(() => $scope.$apply());
    };

    // Loads more results without changing query

    $scope.loadMore = function() {

      $scope.page += 1;
      $scope.fetchResults();

    };

    $scope.deletePage = function (page) {

      // Confirm and delete!

      if (confirm('Are you sure you want to delete this?')) {
        Api.pages.delete(page)
          .then(function (response) {
            // Remove page from UI
            var index = $scope.resources.indexOf(page);
            $scope.resources.splice(index, 1);
          });
      }

    };

    $scope.editPage = function (page) {

      // Send to edit page
      // @todo: add Mixpanel tracking!!

      $window.location.href = '/pages/edit/' + page.short_uid;

    };

    // Username regex... unused at the moment.
    var userRegex = new RegExp('[A-Za-z0-9\_\-]*');

    $scope.updateInfo = function (isValid) {

      $scope.submitted = true;

      if (isValid) {

        $scope.errorMessage = '';

        //@todo: check for the username to be valid!!!!

        if ($scope.profileUser) {

          var params = {};
          params.first_name = $scope.profileUser.first_name;
          params.last_name = $scope.profileUser.last_name;
          params.email = $scope.profileUser.email;
          params.username = $scope.profileUser.username;
          params.short_bio = $scope.profileUser.short_bio;
          params.receives_updates = $scope.profileUser.receives_updates;

          $scope.updating = true;

          Api.users.update($scope.profileUser, params)
            .then(function (response) {

              if (response.error) {
                $scope.updating = false;

                if (response.message.contains('DuplicateEmail')) {
                  $scope.errorMessage = 'Email already in use.';
                  $scope.userForm.email.$setValidity('email', false);
                } else if (response.message.contains('InvalidUsername')) {
                  $scope.errorMessage = 'Username can only contain letters, numbers, _\'s and -\'s.';
                  $scope.userForm.username.$setValidity('username', false);
                } else if (response.message.contains('DuplicateUsername')) {
                  $scope.errorMessage = 'Username already in use.';
                  $scope.userForm.username.$setValidity('username', false);
                } else {
                  $scope.errorMessage = 'Error with data. Try again.';
                }
              } else {

                if ($scope.file) {
                  $scope.uploadImage();
                } else {
                  $window.location.reload();
                }
              }
            });
        }

      } else {
        $scope.errorMessage = 'Missing or invalid parameters.';
      }

    };

    $scope.uploadImage = function() {

      $scope.uploading = true;

      Api.users.uploadImage($scope.file)
        .then(function (response) {
          $scope.uploading = false;
          $window.location.reload();
        }, function (error) {
          $scope.error = 'Error uploading image, try another.';
          $scope.uploading = false;
        });

    };

    // Opens password update modal

    $scope.showPasswordModal = function() {
      $('#editModal').modal('toggle');
      $('#passwordModal').modal('toggle');
      $scope.errorMessage = '';
    };

    // Updates password

    $scope.updatePassword = function (isValid) {

      $scope.submitted = true;

      if (isValid) {

        $scope.errorMessage = '';

        var params = {};

        if ($scope.password.length > 0) {
          if ($scope.repeatPassword === $scope.password) {
            params.password = $scope.password;
          } else {
            $scope.password = '';
            $scope.repeatPassword = '';
            $scope.errorMessage = 'Passwords do not match.';
            return;
          }
        }

        $scope.updating = true;

        Api.users.update($scope.profileUser, params)
          .then(function (response) {

            if (response.error) {
              $scope.updating = false;

              if (response.message.contains('BadPassword')) {
                $scope.errorMessage = 'At least 8 characters, ASCII only.';
              } else {
                $scope.errorMessage = 'Error with data. Try again.';
              }
            } else {
              $window.location.reload();
            }
          });

      } else {
        $scope.errorMessage = 'Missing or invalid parameters.';
      }

    };

    $scope.isPage = function (content) {

      return (util.getKind(content.uid) === 'Page');

    };

  }]);

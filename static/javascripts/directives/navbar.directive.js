angular.module('mskApp')
  .directive('navbar', ['$window', '$document', 'Api', function ($window, $document, Api) {
    'use strict';
    return {
      restrict: 'A',
      link: function(scope, element, attrs) {

        scope.showOptions = false;
        scope.searchQuery = '';

        scope.showLogin = function () {
          scope.$root.redirect = null;
          $('#loginModal').modal('show');
          scope.showOptions = false;
          // STILL NEED TO RESET GOOGLE URL
        };

        scope.showSignup = function () {
          scope.$root.redirect = null;
          $('#signupModal').modal('show');
          scope.showOptions = false;
          // STILL NEED TO RESET GOOGLE URL
        };

        scope.logout = function () {
          $window.location.href = '/logout';
        };

        scope.viewProfile = function () {
          $window.location.href = '/profile';
        };

        scope.goToAdmin = function () {
          $window.location.href = '/manage';
          console.log($window.location.href);
        };

        scope.openApp = function (app) {
          $window.location.href = app.path;
        };

        // Option togglers - adds hide toggle on $document
        // IMPORTANT: Be sure to have id 'toggler' on ALL trigger elements

        scope.toggleDropdown = function(dropdown) {

          var hideDropdowns = function (event) {
            if (!($(event.target).hasClass('no-propagation'))) {
              scope.showOptions = false;
              scope.showCourses = false;
              scope.showAudiences = false;
              scope.$apply();
              $document.off('click', hideDropdowns);
            }
          };

          // Binds a method to close all dropdowns on a click
          $document.on('click', hideDropdowns);
          scope[dropdown] = !scope[dropdown];

          // Makes sure any other dropdowns close when one opens
          if (dropdown === 'showOptions') {
            scope.showCourses = false;
          } else if (dropdown === 'showCourses') {
            scope.showOptions = false;
          }

        };

        // Search function
        scope.newSearch = function() {
          $window.location.href = '/search?q=' + scope.searchQuery;
        };

      }
    };
  }]);
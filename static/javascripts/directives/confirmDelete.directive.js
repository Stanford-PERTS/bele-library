angular.module('mskApp').directive('confirmDeleteModal', ['$window', '$timeout','Api', 'User', 'hostingDomain', '$q', function ($window, $timeout, Api, User, hostingDomain, $q) {
    'use strict';
    var linker = function(scope, element, attrs) {
      scope.$watch('entityPendingDelete', function (entity) {
        if (!entity) { return; }
        scope.kind = entity.uid.split('_')[0];
      });

      scope.handleDelete = function (entityId) {
        scope.isDeleting = true;

        var apiPromise;
        if (scope.kind === 'Book') {
          apiPromise = Api.books.remove(entityId);
        } else if (scope.kind === 'Page') {
          apiPromise = Api.pages.remove(entityId);
        }
        return apiPromise.then(function (response) {
          console.log("delete response", response);
          if (!response.error) {
            $window.location.href = '/profile';
          } else {
            scope.isDeleting = false;
            scope.errorMessage = response.message || 'Delete failed. Please try again later.';
          }
        });
      };

    };
    return {
      restrict: 'E',
      // scope: {}, // share scope with the content manager to get content
      link: linker,
      templateUrl: '/static/directives/modal_confirm_delete.html',
      transclude: true,
    };
  }]);

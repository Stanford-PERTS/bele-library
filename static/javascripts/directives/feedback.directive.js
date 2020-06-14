angular.module('mskApp')
  .directive('feedbackModal', ['$window', '$timeout','Api', function ($window, $timeout, Api) {
    'use strict';
    return {
      restrict: 'A',
      link: function(scope, element, attrs) {

        scope.postFeedback = function () {

          if (scope.body) {

            scope.postingFeedback = true;

            // Format fields for api request
            var params = {};
            params.body = scope.body;
            params.path = $window.location.pathname || '';
            if (scope.email) { 
              params.email = scope.email; 
            }

            // Api call to submit feedback
            Api.feedback.create(params)
              .then( function (response) {
                $('#feedbackModal').modal('hide');

                $timeout( function () {
                  scope.postingFeedback = false;
                  scope.body = '';
                  scope.email = '';
                }, 1000);
              });

          } else {

            // Validation should already be in form,
            // but close modal if it's still an issue
            $('#feedbackModal').modal('hide'); 

          }

        };        

      }
    };
  }]);
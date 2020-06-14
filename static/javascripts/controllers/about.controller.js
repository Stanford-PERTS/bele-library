// Angular controller for about page

angular.module('mskApp')
  .controller('AboutCtrl', ['$scope', function ($scope) {

    'use strict';

    $scope.trackDownload = function (fileName) {

      mixpanel.track('File Download', {
        'Content Type': 'About Page',
        'File Name': fileName
      });

    };

  }]);
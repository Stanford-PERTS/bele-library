// Angular controller for handling practices on landing page

angular.module('mskApp')
	.controller('LandingCtrl', ['$scope', 'Api',
		function ($scope, Api) {

		'use strict';

    $scope.books = [];

    Api.books.find({ n: 10 })
      .then(response => $scope.books = response.data);

    $scope.initEditBookModal = function() {
      $('#editBookModal').modal('show');
    };
	}]);

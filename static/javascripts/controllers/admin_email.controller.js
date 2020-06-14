angular.module('mskApp').controller('EmailController', [
    '$scope', 'Api',
    function ($scope, Api) {

        'use strict';
        
        $scope.fromAddresses = [''];

        $scope.email = {from_address: ''};

        $scope.userMessage = function (type, message) {
            $scope.emailAlert = {type: type, message: message};
        };

        $scope.clearMessage = function () {
            $scope.emailAlert = false;
        };

        $scope.send = function (n) {
            $scope.clearMessage();

            if ($scope.emailForm.$invalid) {
                $scope.userMessage('danger', 'All fields are required.');
                return;
            }

            if (!confirm(
                'Really send an email to ' + $scope.email.to_address + '?')) {
                return;
            }

            $scope.email.reply_to = $scope.email.from_address;
            $scope.email.scheduled_date = (new Date()).toDateString('UTC');

            Api.email.create($scope.email).then(function (response) {
                if (!response.error) {
                    $scope.userMessage('success', 'Email sent to ' + $scope.email.to_address);
                } else {
                    $scope.userMessage('danger', 'Error');
                }
            });

        };
    }
]);
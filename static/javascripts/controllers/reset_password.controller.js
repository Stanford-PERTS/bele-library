angular.module('mskApp').controller('ResetPasswordController', [
    '$scope', 'token', 'validToken', 'Api',
    function ($scope, token, validToken, Api) {
        
        'use strict';

        // Mutually exclusive page modes:
        // * 'validToken' - show the reset password form
        // * 'invalidToken' - show a warning
        // * 'passwordChanged' - show a confirmation and link to login
        $scope.mode = validToken ? 'validToken' : 'invalidToken';

        // There are also two small warning messages on the form, triggered by
        // $scope.passwordMismatch and $scope.badPassword.

        $scope.passwordsMatch = function () {
            if (!$scope.newPassword || !$scope.repeatPassword) {
                return false;
            } else {
                return $scope.newPassword === $scope.repeatPassword;
            }
        };

        $scope.resetPassword = function () {
            $scope.success = null;
            $scope.passwordMismatch = false;
            $scope.badPassword = false;

            if (!$scope.passwordsMatch()) {
                $scope.passwordMismatch = true;
                return;
            }

            Api.resetPasswordWithToken(token, $scope.newPassword)
                .then(function (response) {
                    if (response.data === 'changed') {
                        $scope.mode = 'passwordChanged';
                    } else if (response.data === 'invalid_token') {
                        $scope.mode = 'invalidToken';
                    } else if (response.data === 'bad_password') {
                        $scope.badPassword = true;
                    }
                });
        };
    }
]);
// Angular controller for authorization (login and signup) modals

angular.module('mskApp').controller('AuthCtrl', ['$scope', '$window', 'Api', 'Facebook',
  function ($scope, $window, Api, Facebook) {

    'use strict';

    // Will be set when user attempts to login or register; can be:
    // * 'own'
    // * 'google'
    // * 'facebook'
    $scope.authType = undefined;
    $scope.shouldSubscribe = true;
    $scope.oauthing = false;

    // What permissions we request from user's facebook accounts.
    // var facebookPermissions = 'public_profile,email';

    var getEmailExistsMessage = function (errorCode) {
        // We have record of this email under a different auth
        // type. Advise the user to try something else.
        var correctAuthType = errorCode.split(':')[1];
        var authTypeMap = {
            'own': 'logging in with your email and password',
            'google': 'using your Google account',
            'facebook': 'using your Facebook account',
        };
        return 'You already have an account with us. Try ' +
          authTypeMap[correctAuthType] + '.';
    };

    // Users may return from google login with error codes.
    var googleLoginError = util.queryString('google_login_error') || '';
    if (googleLoginError.contains('email_exists')) {
      $scope.googleLoginErrorMessage = getEmailExistsMessage(googleLoginError);
    }

    var postSuccessRedirect = function (user) {
      // Be sure to remove any hash that may be present (the #login hash
      // triggers the login modal) before reloading.
      location.hash = '';

      // Redirect using $root variable set on modal open (currently for
      // practice upload only).
      if ($scope.$root.redirect) {
        $window.location.href = $scope.$root.redirect;
      } else {
        $window.location.reload();
      }
    };

    $scope.showFields = function () {
      $scope.errorMessage = '';
      $scope.showEmail = true;
    };

    $scope.submitLogin = function () {
      // May be a login request OR a reset password request.
      if ($scope.forgotPassword) {
        mixpanel.track('Password Reset');
        $scope.sendPasswordReset();
      } else {
        $scope.login();
      }
    };

    $scope.sendPasswordReset = function () {
      $scope.errorMessage = '';
      $scope.successMessage = '';

      Api.sendPasswordReset($scope.email)
        .then(function (response) {
          if (response.data === 'sent') {
            $scope.successMessage = 'We have sent you an email to reset ' +
                                    'your password. If it does not arrive, ' +
                                    'please check your spam folder and mark ' +
                                    'as \'not spam\'.';
          } else {
            $scope.errorMessage = 'We have no record of that email address.';
          }
        });
    };

    $scope.login = function() {
      mixpanel.track('Login', {
        'method': 'email'
      });

      $scope.loading = true;
      $scope.authType = 'own';
      $scope.errorMessage = '';

      var data = {
        auth_type: 'own',
        email: $scope.email,
        password: $scope.password
      };

      Api.auth.login(data).then(function (response) {
        loginCallback(response);
      });
    };

    $scope.register = function() {
      mixpanel.track('Sign Up', {
        'method': 'email'
      });

      $scope.loading = true;
      $scope.errorMessage = '';

      var data = {
        auth_type: 'own',
        first_name: $scope.firstName,
        last_name: $scope.lastName,
        email: $scope.email,
        password: $scope.password
      };

      // Checks for subscription on checkbox
      if ($scope.shouldSubscribe) {
        data.should_subscribe = true;
      }

      Api.auth.register(data).then(function (response) {
        registerCallback(response);
      });
    };

    // Facebook login and register button actions

    $scope.facebookLogin = function () {
      $scope.authType = 'facebook';
      $scope.errorMessage = '';
      $scope.oauthing = true;

      Facebook.login().then(function (response) {
        loginCallback(response);
      });
    };

    $scope.facebookRegister = function () {
      $scope.authType = 'facebook';
      $scope.errorMessage = '';
      $scope.oauthing = true;

      Facebook.register($scope.shouldSubscribe)
        .then(function (response) {
          registerCallback(response);
        });
    };

    var loginCallback = function(response) {
      // Potential responses from /api/login are:
      // * 'credentials_missing' - means there was a problem stitching together
      //   third party links/cookies/stuff; never good.
      // * 'credentials_invalid' - either the account doesn't exist, or the
      //   provided password doesn't match the account.
      // * 'email_not_found' - only for facebook, happens when the account is
      //   real but it doesn't share any email address.
      // * 'email_exists:[auth_type]' - the email the user gave exists on some
      //   other account. For instance, if they initially registered with
      //   their google account, and then they later try to sign in by entering
      //   their gmail address and a password, the server will say
      //   'email_exists:google'.
      var d = response.data;

      console.log('Login callback: ', response);

      if (d.uid) {
        // Track success in Mixpanel
        var method = 'email';
        if ($scope.authType !== 'own') {
          method = $scope.authType;
        }
        mixpanel.track('Login Success', {
          'method': method
        });
        postSuccessRedirect(d);

      } else if (d=== 'email_not_found') {
        $scope.oauthing = false;
        $scope.errorMessage = 'We\'re unable to use your Facebook account' +
          ' to sign you up. Please use another method.';
        $scope.loading = false;

      } else if (d === 'credentials_missing') {
        // This shouldn't happen, unless we have our javascript
        // wrong.
        $scope.oauthing = false;
        throw new Error('Bug in login page, got \'credentials_missing\'.');

      } else if (d === 'credentials_invalid') {

        if ($scope.authType === 'own') {
          $scope.oauthing = false;
          $scope.errorMessage = 'Unrecognized email or password.';
          $scope.loading = false;
        } else if ($scope.authType === 'facebook') {
          // So they don't have an account yet, no big deal. Register them.
          $scope.facebookRegister();
        }

      } else if (d.contains('email_exists')) {
        $scope.oauthing = false;
        $scope.errorMessage = getEmailExistsMessage(d);
      } else {

        $scope.oauthing = false;
        throw new Error('Unrecognized response: ' + d + ' (' + (typeof d) + ')');

      }
    };

    var registerCallback = function(response, status, xhr) {
      // Potential responses from /api/register are:
      // * 'credentials_missing' - means there was a problem stitching
      //   together third party links/cookies/stuff; never good. This can
      //   happen if a facebook user doesn't share an email with us.
      // * 'bad_password' - provided password doesn't pass muster, see
      //   config.password_pattern.
      // * 'email_exists:[auth_type]' - the email the user gave exists on some
      //   other account. For instance, if they initially registered with
      //   their google account, and then they later try to register *again*
      //   the same way, the server will say 'email_exists:google'.

      // Keep loading going so the button doesn't appear before redirect
      // $scope.loading = false;
      var d = response.data;

      console.log('Register callback: ', response);

      if (d.uid) {
        var method = 'email';
        if ($scope.authType !== 'own') {
          method = $scope.authType;
        }
        mixpanel.track('Sign Up Success', {
          'method': method
        });

        postSuccessRedirect(d);
      } else if (d === 'credentials_missing' || d === 'email_not_found') {
        $scope.loading = false;
        $scope.oauthing = false;
        if ($scope.authType === 'facebook') {
          $scope.errorMessage = 'We\'re unable to use your Facebook account' +
            ' to sign you up. Please use another method.';
        } else {
          // This shouldn't happen, unless we have our javascript
          // wrong.
          throw new Error(
            'Bug in register page, got \'credentials_missing\'.');
        }
      } else if (d === 'bad_password') {
        $scope.loading = false;
        $scope.oauthing = false;
        $scope.errorMessage = 'Password must be at least 8 characters, ' +
          'ASCII only.';
      } else if (d.contains('email_exists')) {
        $scope.loading = false;
        // If someone with a valid account is registering via the same
        // method, just log them in.
        var existsAuthType = d.split(':')[1];
        if (existsAuthType === $scope.authType &&
            $scope.authType === 'facebook') {
            $scope.facebookLogin();
        } else if (existsAuthType === $scope.authType &&
                   $scope.authType === 'google') {
          $scope.oauthing = false;
          throw new Error('Google authentication is not asynchronous, ' +
                          'so this should never happen.');
        } else {
          $scope.oauthing = false;
          $scope.errorMessage = getEmailExistsMessage(d);
        }
      } else {
        $scope.oauthing = false;
        $scope.loading = false;
        throw new Error('Unrecognized response: ' + d +
                        ' (' + (typeof d) + ')');
      }

    };

  }]);
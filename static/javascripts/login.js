$(function () {
    'use strict';
    var login = function (kwargs) {
        $.ajax({
            url: '/api/login',
            data: kwargs,
            dataType: 'json',
            type: 'POST',
            error: function(xhr, status, error) {
                throw new Error("Ajax error: " + error);
            },
            success: loginCallback
        });
    };

    var loginCallback = function(response) {
        var d = response.data;
        if (d.uid) {
            // The matching user was returned, and the server has
            // logged the person in, send them on.
            var user = d;
            var redirect, rawRedirect = util.queryString('redirect');
            if (rawRedirect) {
                redirect = decodeURIComponent(rawRedirect);
            } else if (user.is_admin) {
                redirect = window.adminHomePage;
            } else {
                redirect = window.normalHomePage;
            }
            window.location.href = redirect;
        } else if (d === 'credentials_missing') {
            // This shouldn't happen, unless we have our javascript
            // wrong.
            throw new Error(
                "Bug in login page, got 'credentials_missing'.");
        } else if (d === 'credentials_invalid') {
            $('#userAlertDiv')
                .addClass('alert-danger')
                .html("Unrecognized email or password.")
                .show();
        } else if (d.contains('email_exists')) {
            // We have record of this email under a different auth
            // type. Advise the user to try something else.
            var correctAuthType = d.split(':')[1];
            var authTypeMap = {
                'own': 'using your email and password',
                'google': 'using your google account',
                'facebook': 'using your facebook account',
            };
            $('#userAlertDiv')
                .addClass('alert-danger')
                .html("Sign in unsuccessful. Try " +
                      authTypeMap[correctAuthType] + ".")
                .show();
        } else {
            throw new Error("Unrecognized response: " + d +
                            " (" + (typeof d) + ")");
        }
    };

    window.fbLoginCallback = function () {
        // The user clicked the facebook login button, and we can expect they
        // have successfully logged in to fb. This may have been transparent to
        // the user if they were logged in to fb before they clicked. But their
        // intent is to log in to OUR site WITH their fb account. So let's do
        // that.
        FB.getLoginStatus(function (response) {
            login({
                auth_type: 'facebook',
                facebook_access_token: response.authResponse.accessToken,
            });
        });
    };

    var loginOwn = function () {
        login({
            auth_type: 'own',
            email: $('#email').val(),
            password: $('#password').val()
        });
    };

    $('#loginButton').click(loginOwn);
});
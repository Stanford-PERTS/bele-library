

/* global console, util, FastClick, mixpanel */

var debug = util.isDevelopment();

// Global configuration for a main angular app.
(function () {
    'use strict';

    var mskApp = angular.module('mskApp',
        ['ngFileUpload', 'ngCookies', 'ui.bootstrap', 'ui.slider', 'angular-redactor', 'ui.tinymce', 'dndLists']);

    mskApp.config([
        '$compileProvider',
        '$interpolateProvider',
        '$locationProvider',
        '$httpProvider',
        config
    ]);
    function config($compileProvider, $interpolateProvider, $locationProvider, $httpProvider) {
        // For angular 1.4.3 (using in BELE Library as of 2019-08-02), the
        // original whitelist is /^\s*(https?|ftp|local|file|data|blob):/,
        // which you can see like this:
        //     var originalWhitelist = $compileProvider.aHrefSanitizationWhitelist();
        //     console.log("whitelist", originalWhitelist.toString());
        // See also https://code.angularjs.org/1.4.3/docs/api/ng/provider/$compileProvider
        // We want to allow mailto links, so the new one is:
        var whitelistWithMailto = /^\s*(https?|ftp|local|file|data|blob|mailto):/;
        $compileProvider.aHrefSanitizationWhitelist(whitelistWithMailto);

        // Change the default bracket notation, which is normally {{ foo }},
        // so that it doesn't interfere with jinja (server-side templates).
        // That means angular interpolation is done like this: {[ foo ]}.
        $interpolateProvider.startSymbol('{[');
        $interpolateProvider.endSymbol(']}');

        // Angular url location w/o preceeding '#'
        $locationProvider.html5Mode(true);
        $locationProvider.hashPrefix('!');

        /* jshint sub: true */  // allow unecessary square-bracket notation
        $httpProvider.defaults.useXDomain = true;
        // $httpProvider.defaults.withCredentials = true;
        delete $httpProvider.defaults.headers.common["X-Requested-With"];
        $httpProvider.defaults.headers.common["Accept"] = "application/json";
        $httpProvider.defaults.headers.common["Content-Type"] = "application/json";
    }


    // Angular 'run' occurs after all assets loading,
    // can replace jQuery function((){...}());
    // Put all universal javascript inside this function
    mskApp.run(['$window', '$rootScope', 'Api', 'User', function ($window, $rootScope, Api, User) {

        // Init mixpanel
        mixpanel.init("b8e50e5cf09fb9847ca1e77c70d24d62");

        // Prevent delay on iPhone taps
        FastClick.attach(document.body);

        // Using production variable for mixpanel tracking
        $rootScope.production = !util.isDevelopment();

        // Allow a hash to trigger the login modal on page load. That way we can
        // write links that automatically go to login.
        if ($window.location.hash === '#login') {
            $('#loginModal').modal();
        }

        // Track page view
        mixpanel.track("Page View");

        // Links user from server into Angular
        $rootScope.setUser = function (user) {
            User.setUser(user);
        };

        // Prevents upload page access if not logged in
        $rootScope.uploadPractice = function() {

            mixpanel.track("Click Upload Button");
            $rootScope.redirect = '/practices/upload';
            if (!User.currentUser()) {
                // Modify the google button to go to the practices upload page,
                // rather than the current page.
                Api.getGoogleLoginLink($rootScope.redirect).then(function (response) {
                    var newUrl = response.data;
                    $('#google-login, #google-signup').attr('href', newUrl);
                    $('#signupModal').modal('show');
                });
            } else {
                $window.location.href = $rootScope.redirect;
            }

        };

        // Search function
        $rootScope.newSearch = function() {
          $window.location.href = '/search?q=' + $rootScope.searchQuery;
        };

        // Inits bootstrap tooltips
        $('[data-toggle="tooltip"]').tooltip();

        // Function to scroll page on #id links
        // handle links with @href started with '#' only
        $(document).on('click', 'a[href^="#"]', function (e) {
            // target element id
            var id = $(this).attr('href');

            // target element
            var $id = $(id);
            if ($id.size() === 0) {
                return;
            }

            // prevent standard hash navigation (avoid blinking in IE)
            e.preventDefault();

            // top position relative to the document
            var pos = $('.full-container').scrollTop() + $(id).offset().top;

            // animated top scrolling
            $('.full-container').animate({scrollTop: pos}, 500);
        });

        // Handle scrolling to topic on special course pages with # symbol
        if ($window.location.hash) {
            var hash = $window.location.hash.split('#')[1];
            var scrollPlace = document.getElementById(hash);
            if (scrollPlace) {
                // top position relative to the document
                var pos = $('.full-container').scrollTop() + $(scrollPlace).offset().top - 100;
                // animated top scrolling
                $('.full-container').animate({scrollTop: pos}, 500);
            }
        }

        // Sets scrollTop for affixing elements
        // Currently only for mainSidepanel element on main.html
        if (document.getElementById('mainSidepanel')) {
            $rootScope.mainSidepanelScrollTop = document.getElementById('mainSidepanel').offsetTop - 30;
        }

    }]);


    // **********************
    // Custom Angular helpers
    // **********************


    // A promise-based $http wrapper.
    mskApp.factory('$ajax', function ($http, $q) {
        return function $ajax(kwargs) {
            kwargs = util.defaults(kwargs, {
                params: {},
                method: 'GET',
                successMessage: null,
                errorMessage: 'Error, please reload'
            });

            // // display in the UI that we've started the call
            // util.displayUserMessage('info', "Loading...");

            // Make the call, anticipating the server's use of 'error' to
            // indicate whether or not an error occurred.
            var deferred = $q.defer();
            // The 'success' callback here is in terms of HTTP; the server
            // responded with a 200.
            $http(kwargs).success(function (response, status) {
                // The sense of 'error' here is whether any exception was
                // caught on the server during the call.
                if (response.error) {
                    if (debug) { console.error(response); }
                    deferred.reject(response.message);
                    // util.displayUserMessage('error', kwargs.errorMessage);
                } else {
                    deferred.resolve(response.data);
                    // if (kwargs.successMessage) {
                    //     util.displayUserMessage('info', kwargs.successMessage);
                    // }
                    // util.clearUserMessage(1200);
                }
            }).error(function (response, status) {
                // The sense of 'error' here is in terms of HTTP; the server
                // responded with a 500 or similar.
                if (debug) { console.error(response); }
                deferred.reject(response.message);
                // util.displayUserMessage('error', kwargs.errorMessage);
            });
            return deferred.promise;
        };
    });


    // A service which you can call to create an immediately-resolving promise
    // (rather than one which only resolves after some future async event).
    // This is useful if your code is branching between sync and async options,
    // but you want the results to be uniform.

    // In this example, the function foo() always returns a promise, which is
    // nice. And if it's ready, the promise it returns resolves immediately,
    // which is appropriate.

    // function foo(ready) {
    //     if (ready) {
    //         return $emptyPromise('readyToRock');
    //     } else {
    //         return someAsyncProcess();  // returns a promise
    //     }
    // }
    //
    // foo(maybeReady).then(function (resolveValue) { ... do stuff ... });

    mskApp.factory('$emptyPromise', function ($q) {
        return function $emptyPromise(valueToPass) {
            // Create an immediately-resolving promise. Used to imitate the
            // promises created by ajax calls, e.g. in program app testing.
            var deferred = $q.defer();
            deferred.resolve(valueToPass);
            return deferred.promise;
        };
    });

    // A utility function that can run for-like loops with asynchronous
    // processes. Use just like forEach, but you can launch something like an
    // ajax call in the loop, as long as you return a promise. You can choose
    // to run the calls in serial (one after the other) or in parallel
    // (launching them all at once). Either way, you can attach a callback when
    // they're all done with .then. For example, this would call doAsyncJob()
    // for every item in myList, one after the other, and run doSomethingElse()
    // once those were all done:

    // $forEachAsync(myList, function (item) {
    //     return doAsyncJob(item);
    // }, 'serial').then(function () {
    //     doSomethingElse();
    // });

    mskApp.factory('$forEachAsync', function ($q) {
        return function forEachAsync(arrayOrDict, f, serialOrParallel) {
            if (serialOrParallel === 'parallel') {
                // Iterate over the data, calling f immediately for each data
                // point. Collect all the resulting promises together for return
                // so further code can be executed when all the calls are done.
                return $q.all(forEach(arrayOrDict, f));
            }
            if (serialOrParallel === 'serial') {
                // Set up a deferred we control as a zeroth link in the chain,
                // which makes writing the loop easier.
                var serialDeferred = $q.defer(),
                    serialPromise = serialDeferred.promise;
                // Do NOT make all the calls immediately, instead embed each data
                // point and chain them in a series of 'then's.
                forEach(arrayOrDict, function (a, b) {
                    serialPromise = serialPromise.then(f.partial(a, b));
                });
                // Fire off the chain.
                serialDeferred.resolve();
                // Return the whole chain so further code can extend it.
                return serialPromise;
            }
            throw new Error(
                "Must be 'serial' or 'parallel', got " + serialOrParallel
            );
        };
    });

    mskApp.directive('ngFocus', function () {
        return {
            restrict: 'A',
            require: 'ngModel',
            link: function (scope, element, attrs) {
                element.bind('focus', function () {
                    scope.$apply(attrs.ngFocus);
                });
            }
        };
    });

    mskApp.directive('ngBlur', function () {
        return {
            restrict: 'A',
            require: 'ngModel',
            link: function (scope, element, attrs) {
                element.bind('blur', function () {
                    scope.$apply(attrs.ngBlur);
                    element.addClass('msk-blurred');
                });
            }
        };
    });

    // A generic link function for directives that transform text as it is
    // typed in an input box. Uses apply() to run the provided method with
    // provided args on the current text.
    // http://stackoverflow.com/questions/14419651/angularjs-filters-on-ng-model-in-an-input
    var transformInput = function (stringMethod, args) {
        args = args instanceof Array ? args : [];
        return function (scope, element, attrs, modelCtrl) {
            modelCtrl.$parsers.push(function (inputValue) {
                if (typeof inputValue !== 'string') { return; }
                var transformedInput = stringMethod.apply(inputValue, args);
                if (transformedInput !== inputValue) {
                    modelCtrl.$setViewValue(transformedInput);
                    modelCtrl.$render();
                }
                return transformedInput;
            });
        };
    };

    mskApp.directive('toLowerCase', function () {
        return {
            require: 'ngModel',
            link: transformInput(String.prototype.toLowerCase)
        };
    });

    mskApp.directive('toUpperCase', function () {
        return {
            require: 'ngModel',
            link: transformInput(String.prototype.toUpperCase)
        };
    });

    // Takes out anything besides upper and lower case letters and spaces
    mskApp.directive('alphaOnly', function () {
        return {
            require: 'ngModel',
            link: transformInput(String.prototype.replace, [/[^a-zA-Z ]/g, ''])
        };
    });

    // Allows ordering in ng-repeat if you're iterating over an object.
    // Ordering is normally only possible if you're iterating over an array.
    // In this example, obj is a hash of ids to to data objects, where each
    // data object has a name property. The filter orders the data objects
    // by their name.

    // <tbody ng-repeat="(id, data) in obj | orderObjectBy:'name'">
    mskApp.filter('orderObjectBy', function() {
        return function (dict, prop, reverse) {
            var filtered = forEach(dict, function(k, v) {
                return v;
            });
            filtered.sort(function (a, b) {
                return a[prop] > b[prop] ? 1 : -1;
            });
            if (reverse) {
                filtered.reverse();
            }
            return filtered;
        };
    });

    // Capitalize first letter in a string
    mskApp.filter('capitalize', function() {
        return function(input, all) {
            return (!!input) ? input.replace(/([^\W_]+[^\s-]*) */g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();}) : '';
        };
    });

    // Create a nice date string
    mskApp.filter('prettyDate', function() {
        return function (input) {
            return util.prettyDate(input);
        };
    });

    mskApp.filter('encodeURIComponent', ['$window', function ($window) {
        return $window.encodeURIComponent;
    }]);

    // Scroll directive handles affix-ing elements (and whatever else)
    mskApp.directive("scroll", ['$window', function ($window) {
        return function(scope, element, attrs) {
            element.bind("scroll", function() {
                // Variable set in 'run', maybe add logic if we have more ever
                var scrollCheck = scope.$root.mainSidepanelScrollTop || 530;
                if (this.scrollTop >= scope.mainSidepanelScrollTop) {
                    scope.affixSidePanel = true;
                } else {
                    scope.affixSidePanel = false;
                }
                scope.$digest();
            });
        };
    }]);

    var isEmpty = function (value) {
      return (angular.isUndefined(value) || value === '' || value === null ||
              value !== value);
    };

    mskApp.directive('ngMin', function () {
        return {
            restrict: 'A',
            require: 'ngModel',
            link: function (scope, elem, attr, ctrl) {
                scope.$watch(attr.ngMin, function(){
                    ctrl.$setViewValue(ctrl.$viewValue);
                });
                var minValidator = function (value) {
                    var min = scope.$eval(attr.ngMin) || 0;
                    elem.attr('min', min);
                    if (!isEmpty(value) && value < min) {
                        ctrl.$setValidity('ngMin', false);
                        return undefined;
                    } else {
                        ctrl.$setValidity('ngMin', true);
                        return value;
                    }
                };

                ctrl.$parsers.push(minValidator);
                ctrl.$formatters.push(minValidator);
            }
        };
    });

    mskApp.directive('ngMax', function () {
        return {
            restrict: 'A',
            require: 'ngModel',
            link: function (scope, elem, attr, ctrl) {
                scope.$watch(attr.ngMax, function (){
                    ctrl.$setViewValue(ctrl.$viewValue);
                });
                var maxValidator = function (value) {
                    var max = scope.$eval(attr.ngMax) || Infinity;
                    elem.attr('max', max);
                    if (!isEmpty(value) && value > max) {
                        ctrl.$setValidity('ngMax', false);
                        return undefined;
                    } else {
                        ctrl.$setValidity('ngMax', true);
                        return value;
                    }
                };

                ctrl.$parsers.push(maxValidator);
                ctrl.$formatters.push(maxValidator);
            }
        };
    });
}());

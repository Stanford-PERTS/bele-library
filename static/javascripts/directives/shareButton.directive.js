angular.module('mskApp')
  .directive('shareButton', ['$window', function ($window) {
    'use strict';

    return {
      restrict: 'A',
      scope: {
      },
      link: function(scope, element, attrs) {

        scope.content = attrs.shareButton;
        if (scope.content) {
          scope.contentType = scope.content.split('_')[0];
        }

        var updateShareHref = function () {

          var url = attrs.shareUrl || $window.location.href;
          var type = attrs.shareType || '';
          var text = attrs.shareText || '';
          var href = '';

          if (type === 'facebook') {
            href = 'https://www.facebook.com/sharer.php?u=' + url;
          } else if (type === 'twitter') {
            href = 'https://twitter.com/share?text=' + text + '&url=' + url;
          } else if (type === 'google') {
            href = 'https://plus.google.com/share?url=' + url;
          } else if (type === 'email') {
            href = 'mailto:?body=' + text + url;
          }

          element.attr('href', href);

        };

        element.attr('target', '_blank');
        updateShareHref();

        attrs.$observe('shareUrl', function(value) {
          if (value) {
            updateShareHref();
          }
        });

        attrs.$observe('shareText', function(value) {
          if (value) {
            updateShareHref();
          }
        });

        element.on('click', function (event) {

          // Track share on mixpanel with type
          mixpanel.track('Share Content', {
            'Share Type': attrs.shareType,
            'Content Type': scope.contentType,
            'Content Id': scope.content
          });

        });

      }
    };
  }]);
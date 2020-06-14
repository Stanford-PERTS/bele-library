angular.module('mskApp')
  .directive('imageLoader', ['$timeout', function ($timeout) {

    'use strict';

    function getWidth() {
      if (document.documentElement && document.documentElement.clientHeight) {
        return document.documentElement.clientWidth;
      }
      if (document.body) {
        return document.body.clientWidth;
      }
    }

    return {
      template: '',
      restrict: 'A',
      scope: true,
      link: function (scope, element, attrs) {

        var imageUrl;

        var img = new Image();
        img.onload = function() {
          $timeout(function(){
            element.removeClass('loading');
            element.addClass('loaded');
          }, 100);
        };

        if (attrs.mobile && getWidth() <= 767) {
          imageUrl = attrs.mobile;
        } else {
          imageUrl = attrs.image;
        }

        img.src = imageUrl;

        if (!img.complete) {
          element.addClass('loading');
        }
        element.css('background-image', 'url(' + imageUrl + ')');

        scope.$watch( function() { return attrs.image; }, function() {
          if (attrs.image) {

            var oldImage = imageUrl;

            if (attrs.mobile && getWidth() <= 767) {
              imageUrl = attrs.mobile;
            } else {
              imageUrl = attrs.image;
            }

            // Prevents re-animating the same image
            if (oldImage === imageUrl) {
              return;
            }

            img.src = imageUrl;

            if (!img.complete) {
              element.removeClass('loaded');
              element.addClass('loading');
            }
            element.css('background-image', 'url(' + imageUrl + ')');
          }

        });

      }
    };
  }]);
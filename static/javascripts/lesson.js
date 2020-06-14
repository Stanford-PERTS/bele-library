// Javascript functions for lesson pages

$(function () {
  'use strict';

  var originalHeight = $('.lesson-header').height();

  // Handle resizing header on scroll
  var headerResized = false;

  $('.full-container').scroll(function () {

    // Animations in introduction section
    var scrollPos = $(this).scrollTop();

    if (scrollPos > originalHeight) {
      if (!headerResized) {
        $('.lesson-header.sticky').addClass('active');
        headerResized = true;
      }
    } else {
      if (headerResized) {
        $('.lesson-header.sticky').removeClass('active');
        headerResized = false;
      }
    }
  });

});

var setupResultsButton = function(questionCount, successCallback) {
  'use strict';

  $('#getResults').on('click', function () {
    $('.error-message').removeClass('active');

    // Determine if any are checked
    var inputs = $('input[type="radio"]:checked');
    if (inputs.length >= questionCount) {
      $('.survey-results').addClass('active');
      // Success! Run callback function.
      if (typeof successCallback === 'function') {
        successCallback(inputs);
      }
    } else {
      $('.error-message').addClass('active');
    }
  });
};

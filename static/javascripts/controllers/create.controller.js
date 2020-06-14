// Angular controller for practice uploading (create) page

angular.module('mskApp')
  .controller('CreateCtrl',
    ['$scope', '$q', '$window', 'Api', 'User', 'hostingDomain',
    function ($scope, $q, $window, Api, User, hostingDomain) {

    'use strict';

    // Initialize all variables used by view.

    $scope.resetVariables = function() {

      $scope.files = [];
      $scope.freshFiles = [];
      $scope.oldFiles = []; // For editing...

      $scope.step = 1; // Change to 2 or 3 for testing
      $scope.practiceName = '';
      $scope.practiceSummary = '';
      $scope.practiceBody = '';
      $scope.resourceType = '';
      $scope.validated = false;
      $scope.practiceUrl = '/practice';
      $scope.created = false; // Used for catching file upload error after creation
      $scope.shareUrl = 'https://' + hostingDomain + '/practices';
      $scope.shareText = encodeURIComponent('I just uploaded a new #mindset practice - ');

      $scope.pageIcon = null;

      $scope.mindsetTags = [
        {
          'name': 'Growth Mindset',
          'active': false
        },{
          'name': 'Belonging',
          'active': false
        },{
          'name': 'Purpose & Relevance',
          'active': false
        },{
          'name': 'Self-efficacy',
          'active': false
        }
      ];

      $scope.practiceTags = [
        {
          'name': 'Participation',
          'active': false
        },{
          'name': 'Attendance',
          'active': false
        },{
          'name': 'Messaging/framing',
          'active': false
        },{
          'name': 'Classroom Mgmt',
          'active': false
        },{
          'name': 'Feedback',
          'active': false
        },{
          'name': 'Assessment',
          'active': false
        },{
          'name': 'Lesson Plans',
          'active': false
        },{
          'name': 'Discussions',
          'active': false
        },{
          'name': 'Collaboration',
          'active': false
        },{
          'name': 'Professional Dev.',
          'active': false
        }
      ];

      // Initial values for grade level slider
      $scope.gradeSlider = [0, 13];

      // Used to associate grade level integers with names
      $scope.gradeLevels = [
        'Kindergarten',
        '1st',
        '2nd',
        '3rd',
        '4th',
        '5th',
        '6th',
        '7th',
        '8th',
        '9th',
        '10th',
        '11th',
        '12th',
        'Postsecondary'
      ];

      $scope.schoolSubjects = [
        {
          'name': 'Math',
          'active': false
        },{
          'name': 'English / Lit.',
          'active': false
        },{
          'name': 'Science',
          'active': false
        },{
          'name': 'Social Studies',
          'active': false
        },{
          'name': 'Other',
          'active': false
        }
      ];

      $scope.yearTimes = ['Anytime', 'Beginning', 'Middle', 'End'];
      $scope.classPeriods = ['Anytime', 'Beginning', 'End'];

      $scope.yearTime = 'Anytime';
      $scope.classPeriod = 'Anytime';

      $scope.classDrop = false;
      $scope.yearDrop = false;

    };

    // Determines if a valid Youtube link has been shared and
    // extracts ID for practice upload
    $scope.getYoutubeId = function () {

      var reg = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
      var match = $scope.youtubeSource.match(reg);

      if (match && match[2].length === 11) {
        $scope.youtubeValid = true;
        $scope.youtubeInvalid = false;
        $scope.youtubeId = match[2];
      } else if ($scope.youtubeSource.length > 0) {
        $scope.youtubeValid = false;
        $scope.youtubeInvalid = true;
        $scope.youtubeId = '';
      } else {
        $scope.youtubeValid = false;
        $scope.youtubeInvalid = false;
        $scope.youtubeId = '';
      }
    };

    // Determines if a valid iFrame src has been shared and
    // extracts src for practice upload
    $scope.getIframeSrc = function () {

      var reg = /<iframe[\S\s]*src=['"]([\S]*)['"][\s\>$]/;
      var match = $scope.embedCode.match(reg);

      console.log(match);

      if (match && match[1].length >= 6) {
        $scope.iframeSrcValid = true;
        $scope.iframeSrcInvalid = false;
        $scope.iframeSource = match[1];
      } else if ($scope.iframeSource.length > 0) {
        $scope.iframeSrcValid = false;
        $scope.iframeSrcInvalid = true;
        $scope.iframeSource = '';
      } else {
        $scope.iframeSrcValid = false;
        $scope.iframeSrcInvalid = false;
        $scope.iframeSource = '';
      }
    };

    // Removes any videos, Youtube by default
    $scope.removeVideo = function () {

      $scope.youtubeSource = '';
      $scope.getYoutubeId();

    };

    // Removes any iFrame sources
    $scope.removeIframe = function () {

      $scope.iframeSource = '';
      $scope.embedCode = '';
      $scope.getIframeSrc();

    };

    $scope.setEditPage = function(practice) {

      $scope.practiceName = practice.name;
      $scope.practiceSummary = practice.summary;
      $scope.practiceBody = practice.body;
      $scope.practiceType = practice.type;

      $scope.yearTime = practice.time_of_year;
      $scope.classPeriod = practice.class_period;

      if (practice.youtube_id) {
        $scope.youtubeSource = 'https://youtu.be/' + practice.youtube_id;
        $scope.getYoutubeId();
      }

      if (practice.iframe_src) {
        $scope.embedCode = '<iframe src="' + practice.iframe_src + '"></iframe>';
        $scope.getIframeSrc();
      }

      if (practice.has_files) {
        $scope.oldFiles = practice.json_properties.files;
      }

      if (practice.max_grade) {
        $scope.gradeSlider = [practice.min_grade, practice.max_grade];
      }

      setTagsFromArray($scope.mindsetTags, practice.tags);
      setTagsFromArray($scope.practiceTags, practice.tags);
      setTagsFromArray($scope.schoolSubjects, practice.subjects);
      // setTagsFromArray($scope.gradeLevels, practice.grade_levels);

      $scope.editPage = true;
      $scope.editingPractice = practice;

    };

    // ************************************
    // Code to run on init...
    // ************************************

    $scope.resetVariables();

    // Regular expression to recognize edit URL
    var editReg = /^.*(\/practices\/edit\/)(.{16}).*/;
    var editing = false;

    // Check for url with /edit/<practice_id>
    // and pull <practice_id> to update form
    if ($window.location.href.match(editReg) && $window.location.href.match(editReg)[2]) {
      $scope.practiceId = $window.location.href.match(editReg)[2];
      editing = true;

      Api.practices.findById($scope.practiceId)
        .then( function (response) {

          if (response.data) {
            $scope.setEditPage(response.data);
          }

      });
    }

    mixpanel.track('Start Upload', {
      'Editing': editing
    });

    // Setup quill editor
    // TODO

    // var editor = new Quill('#editor', {
    //   theme: 'snow'
    // });
    // editor.addModule('toolbar', { container: '#toolbar' });

    // Dropdown tag methods

    $scope.setClassDrop = function(classTime) {
      $scope.classPeriod = classTime;
      $scope.classDrop = false;
    };

    $scope.setYearDrop = function(timeOfYear) {
      $scope.yearTime = timeOfYear;
      $scope.yearDrop = false;
    };

    // Function to move uploaded files from 'freshFiles' to 'files'
    // (Allows files to be managed outside input interface)
    $scope.handleFiles = function() {

      $scope.resourceType = 'files';

      if ($scope.freshFiles.length > 0) {
        forEach($scope.freshFiles, function (file) {
          $scope.files.push(file);
        });
        $scope.freshFiles = [];
      }

    };

    // Function to remove file from list of to-be-uploaded files
    $scope.removeFile = function(file) {
      // Check for file in files
      if ($scope.files.contains(file)) {
        $scope.files.remove(file);
      } else {

        // If not, check in oldFiles and delete completely
        if ($scope.oldFiles.contains(file)) {
          if (confirm('Are you sure you want to delete this file?')) {

            Api.practices.removeFile($scope.practiceId, file)
              .then( function (response) {
                $scope.oldFiles.remove(file);
              }, function (error) {
                // ERROR!
              });
          }
        }
      }
    };

    // Check step is validated and user can continue to next step
    $scope.checkValidation = function() {

      $scope.error = '';

      if ($scope.step === 1) {
        if ($scope.practiceName.length < 5) {
          $scope.validated = false;
          $scope.error = 'Practice name is too short';
        } else if ($scope.practiceSummary.length < 10) {
          $scope.validated = false;
          $scope.error = 'Practice summary is too short';
        } else if ($scope.practiceSummary.length > 250) {
          $scope.validated = false;
          $scope.error = 'Practice summary is too long';
        } else if (!$scope.youtubeId && $scope.practiceBody < 10) {
          $scope.error = 'Practice text is too short';
          $scope.validated = false;
        } else {
          $scope.validated = true;
        }
      }

      if (!User.currentUser()) {
        $scope.validated = false;
      }

      return $scope.validated;

    };

    // Moves user to the next step of the upload process
    $scope.nextStep = function() {

      if ($scope.checkValidation()) {
        $scope.step += 1;
        scrollToTop();

        mixpanel.track('Upload Tagging');

      }

    };

    // Moves user to the previous step of the upload process
    $scope.previousStep = function() {

      $scope.step += -1;
      $scope.checkValidation();

    };

    $scope.addResourceType = function (type) {

      $scope.resourceType = type;
      $scope.error = '';

    };

    $scope.createPractice = function () {
      // Function to finish process and upload the practice
      // Formats data entries for POST request

      if ($scope.checkValidation() && !$scope.creating) {

        // Indicate upload and disable button
        $scope.creating = true;

        mixpanel.track('Finish Upload', {
          'Type': $scope.practiceType,
          'Editing': $scope.editPage
        });

        var data = {};

        data.name = $scope.practiceName;
        data.summary = $scope.practiceSummary;
        data.tags = putTagsInArray($scope.mindsetTags.concat($scope.practiceTags));
        data.subjects = putTagsInArray($scope.schoolSubjects);
        data.max_grade = $scope.gradeSlider[1];
        data.min_grade = $scope.gradeSlider[0];
        data.time_of_year = $scope.yearTime;
        data.class_period = $scope.classPeriod;
        data.body = $scope.practiceBody;
        data.youtube_id = $scope.youtubeId || '';
        data.iframe_src = $scope.iframeSource || '';

        if (!$scope.editPage && !$scope.created) {

          Api.practices.create(data)
            .then(function (response) {
              $scope.practice = response.data;
              $scope.created = true;
              $scope.editingPractice = response.data;

              $scope.finishedCallback();
            });

        } else {

          Api.practices.update($scope.editingPractice, data)
            .then(function (response) {
              $scope.practice = response.data;

              $scope.finishedCallback();
            });
        }
      }

    };

    $scope.finishedCallback = function() {
      // Check for any files and upload
      if ($scope.files && $scope.files.length) {

        uploadFile($scope.files, 0).then(function (response) {
          $scope.showFinished();
        }, function (error) {
          $scope.error = 'Error uploading file, try another.';
          $scope.creating = false;
        });

      } else {
        $scope.showFinished();
      }
    };

    $scope.showFinished = function() {
      $scope.step = 3;
      $scope.practiceUrl = '/practices/' + $scope.practice.short_uid;
      $scope.shareUrl = 'https://' + hostingDomain + '/practices/' + $scope.practice.short_uid;
      scrollToTop();
    };

    // Reload page (currently just a page refresh)
    $scope.resetPage = function () {
      $window.location.href = '/practices/upload';
    };

    // Reload page (currently just a page refresh)
    $scope.viewPractice = function () {
      $window.location.href = $scope.practiceUrl;
    };

    // Helper functions....

    // Function to loop through files and upload one at time
    // Async uploading causes errors in json_properties on practice
    var uploadFile = function(files, index) {

      var def = $q.defer();
      var file = files[index];
      if (file) {
        Api.practices.uploadFile($scope.practice, file)
          .then(function (response) {
            uploadFile(files, index + 1).then(function (response) {
              // File added, run again.
              def.resolve(response);
            });
          }, function (error) {
            // Error occurred, break with rejection
            def.reject(error);
          });
      } else {
        // No more files, resolve!
        def.resolve();
      }
      return def.promise;
    };

    // Formats tag arrays into data for API
    var putTagsInArray = function (tags) {
      var array = [];
      for(var i=0;i<tags.length;i++) {
        var tag = tags[i];
        if (tag.active === true) {
          array.push(tag.name);
        }
      }
      return JSON.stringify(array);
    };

    // Formats tag arrays into data for API
    var setTagsFromArray = function (tags, array) {
      if (array) {
        for(var i=0;i<tags.length;i++) {
          var tag = tags[i];
          for(var j=0;j<array.length;j++) {
            if (tag.name === array[j]) {
              tag.active = true;
            }
          }
        }
      }
      return JSON.stringify(array);
    };

    // function to scroll to top of .full-container div
    var scrollToTop = function () {
      $('.full-container').animate({scrollTop: 0});
      $('.upload-container').animate({scrollTop: 0});
    };

    /*
     * New methods
     */

    $scope.handleAttachIcon = function(icon) {

      $scope.resourceType = 'files';

      if (!$scope.pageIcon) {
        $scope.pageIcon = icon;
      }

    };


  }]);

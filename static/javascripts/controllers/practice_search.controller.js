// Angular controller for handling practice search page

angular.module('mskApp')
  .controller('PracticeSearchCtrl', ['$scope', '$timeout', '$location', 'Api', function ($scope, $timeout, $location, Api) {

    'use strict';

    // Initialize all variables used by view.

    $scope.filterCount = 0;
    $scope.page = 0;
    $scope.shouldPaginate = false;

    $scope.showMindsetTags = false;
    $scope.showPracticeTags = false;
    $scope.showGrades = false;
    $scope.showSubjects = false;

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

    $scope.gradeLevels = [
      {
        'name': 'K-2nd',
        'active': false
      },{
        'name': '3rd-5th',
        'active': false
      },{
        'name': '6th-8th',
        'active': false
      },{
        'name': 'High School',
        'active': false
      },{
        'name': 'Postsecondary',
        'active': false
      }
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

    // Watch for tag updates
    $scope.$watch('mindsetTags', function() {
      $scope.updateSearch();
    }, true);
    $scope.$watch('practiceTags', function() {
      $scope.updateSearch();
    }, true);
    $scope.$watch('gradeLevels', function() {
      $scope.updateSearch();
    }, true);
    $scope.$watch('schoolSubjects', function() {
      $scope.updateSearch();
    }, true);

    $scope.textSearch = function (textSearchQueryString) {
      console.log('$scope.textSearch()', textSearchQueryString);
      if ($location.hash() !== textSearchQueryString) {
        console.log('...updating hash', $location.hash());
        $location.hash(textSearchQueryString);
      }
      Api.content.search(textSearchQueryString).then(function (response) {
          console.log('Search got response', response);
          $scope.practices = response.data;
      });
    };

    $scope.$watch(function () { return $location.hash(); }, function (hash) {
      if (!hash) { return; }
      if (hash !== $scope.textSearchQueryString) {
        console.log('Detected hash change', hash);
        $scope.textSearchQueryString = hash;
        $scope.textSearch(hash);
      }
    });

    $scope.updateSearch = function () {

      if (!$scope.loading) {

        $scope.loading = true;

        // Use timeout to allow for scope.$apply in update
        $timeout(function() {

          // $scope changes to reset UI while loading
          $scope.page = 0;
          $scope.practices = [];
          $scope.$apply();
          // $scope.loading = true;
          $scope.noData = false;
          $scope.shouldPaginate = false;

          // timeout for cleaner loading UI
          $timeout(function() {

            setQueryOptions();

            Api.practices.find($scope.options)
              .then( function (response) {
                if (response.data && response.data.length > 0) {
                  var practices = response.data;
                  $scope.practices = practices;

                  // Determine if pagination needed
                  if (practices.length === 20) {
                    $scope.shouldPaginate = true;
                  }

                } else {
                  $scope.practices = [];
                  $scope.noData = true;
                }
                $scope.loading = false;
              });

            }, 500);

        }, 0);

      }

    };

    $scope.filterCount = 0;

    $scope.toggleFilter = function(filter) {
      filter.active = !filter.active;

      if (filter.active) {
        $scope.filterCount+=1;
      } else {
        $scope.filterCount+=-1;
      }
    };

    $scope.removeFilters = function() {

      $scope.filterCount = 0;

      for(var i=0;i<$scope.mindsetTags.length;i++) {
        $scope.mindsetTags[i].active = false;
      }
      for(var j=0;j<$scope.practiceTags.length;j++) {
        $scope.practiceTags[j].active = false;
      }
      for(var k=0;k<$scope.gradeLevels.length;k++) {
        $scope.gradeLevels[k].active = false;
      }
      for(var l=0;l<$scope.schoolSubjects.length;l++) {
        $scope.schoolSubjects[l].active = false;
      }

      $scope.updateSearch();

    };

    // Loads more results without changing query

    $scope.loadMore = function() {

      $scope.page += 1;
      $scope.loading = true;
      $scope.shouldPaginate = false;

      // timeout for cleaner loading UI
      $timeout(function() {

        setQueryOptions();

        Api.practices.find($scope.options)
          .then( function (response) {
            if (response.data && response.data.length > 0) {
              var practices = response.data;

              // Add new practices to end of list
              $scope.practices = $scope.practices.concat(practices);

              // Determine if pagination needed
              if (practices.length === 10) {
                $scope.shouldPaginate = true;
              }

            }
            $scope.loading = false;
          });

        }, 500);

    };

    var setQueryOptions = function() {

      // set options based on inputs
      $scope.options = {};

      querifyTags($scope.mindsetTags, 'mindset_tags');
      querifyTags($scope.practiceTags, 'practice_tags');
      querifyTags($scope.schoolSubjects, 'subjects');
      querifyTags($scope.gradeLevels, 'grade_levels');

      $scope.options.listed = true;
      $scope.options.order = '-created';
      $scope.options.page = $scope.page;

    };

    var querifyTags = function(tags, query) {

      var tagArray = [];

      for(var i=0;i<tags.length;i++) {
        if (tags[i].active) {
          tagArray.push(tags[i].name);
        }
      }

      if (tagArray.length > 0) {
        $scope.options[query] = JSON.stringify(tagArray);
      }

    };

    // CREATE A FUNCTION TO WATCH TAGS TO TOGGLE RESULTS ON CLICKS

  }]);
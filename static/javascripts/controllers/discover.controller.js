// Angular controller for handling practice search page

// @todo: This has been adapted from the practice home page search controller,
// so it probably has useless a/o inappropriate stuff in it. Needs to be
// reivewed, extended, and trimmed.

angular.module('mskApp')
  .controller('DiscoverCtrl', ['$rootScope', '$scope', '$timeout', '$window', '$location', 'Api', 'ElasticSuggest',
    function ($rootScope, $scope, $timeout, $window, $location, Api, ElasticSuggest) {

    'use strict';

    // Initialize all variables used by view.

    $scope.filterCount = 0;
    $scope.page = 0;
    $scope.searchCount = 0;
    $scope.searchList = [];
    $scope.shouldPaginate = false;
    $scope.queryString = '';
    $scope.contentType = '';
    $scope.contentKind = '';
    $scope.pageSize = 20;

    $scope.startTime = new Date();

    $scope.showGrades = false;
    $scope.showSubjects = false;
    $scope.selectedTags = [];
    $scope.extraTags = [];

    $scope.tags = [
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
      },{
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

    // Random at the moment, maybe be better to base on data eventually.
    $scope.popularTags = [
      {
        'name': 'Growth Mindset',
        'active': false
      },{
        'name': 'Lesson Plans',
        'active': false
      },{
        'name': 'Assessment',
        'active': false
      },{
        'name': 'Belonging',
        'active': false
      }
    ];

    $scope.mindsetTags = [
      {
        'name': 'Framework',
        'description':
          'A conceptual framework for thinking about a particular ' +
          'focus area',
        'active': false,
      },{
        'name': 'External Service',
        'description':
          'A service provided to schools by a non-school organization ' +
          '(like an SSO), e.g., training, technical support.',
        'active': false,
      },{
        'name': 'Student Activity',
        'description':
          'A specific practice for students that is intended to advance ' +
          'equity, ideally with a “why,” “how,” and “what to watch out for.”',
        'active': false,
      },{
        'name': 'Adult Activity',
        'description':
          'A specific practice for adults that is intended to advance ' +
          'equity, ideally with a “why,” “how,” and “what to watch out for.”',
        'active': false,
      },{
        'name': 'Diagnostic',
        'description':
          'Tool(s) to identify barriers to opportunity or track progress ' +
          'addressing them.',
        'active': false,
      },{
        'name': 'Structural Change',
        'description': 'Organizational change on a larger scale.',
        'active': false,
      },
    ];

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

    // Initial values for grade level slider
    $scope.gradeSlider = [0, 13];

    $scope.gradeSliderOptions = {
      start: function (event, ui) {
      },
      stop: function (event, ui) {
        $scope.updateSearch();
        $scope.$apply();
      },
      'range': true
    };

    $scope.initEditBookModal = function() {
      $('#editBookModal').modal('show');
    };

    $scope.updateLocation = function () {
      var queryParams = $location.search();
      var newUrl = $window.location.href;

      // Make sure new location is still a search page
      if (newUrl.indexOf('discover') > -1) {

        // Clear results if page = 0
        if ($scope.page === 0) {
          $scope.results = null;
          delete queryParams.page;
        } else {
          queryParams.page = $scope.page;
        }

        if (!($.isEmptyObject(queryParams))) {

          var validParamFound = false;
          var contentTypeFound = false;
          var contentKindFound = false;
          for (var param in queryParams) {
            // Should compare to list of potential params
            // For now just recognizing a couple
            if (param === 'q') {
              $scope.queryString = queryParams[param];
              validParamFound = true;
            } else if (param === 'tags') {
              validParamFound = true;
            } else if (param === 'page' && queryParams[param] > 0) {
              validParamFound = true;
            } else if (param === 'content_type') {
              // Update fixes showing on page load
              $scope.contentType = queryParams[param];
              validParamFound = true;
              contentTypeFound = true;
            } else if (param === 'kind') {
              // Update fixes showing on page load
              $scope.contentKind = queryParams[param];
              validParamFound = true;
              contentKindFound = true;
            }
          }

          // Resets content type if removed from url
          if (!contentTypeFound) {
            $scope.contentType = '';
          }

          // Resets content type if removed from url
          if (!contentKindFound) {
            $scope.contentKind = '';
          }

          // Fetches results
          if (validParamFound) {
            $scope.fetchResults(queryParams);
          } else {
            $scope.fetchResults({});
          }

        } else if (newUrl.indexOf('discover') > -1) {
          // If no search params, and still a search url
          // reloads with blank search
          $scope.fetchResults({});
        }

      }

    };

    // Watch for tag updates
    $scope.$watch('schoolSubjects', $scope.updateSearch, true);

    // Watch for tag updates
    $scope.$watch('mindsetTags', $scope.updateSearch, true);

    // Watch $location.search() for updated parameters
    $rootScope.$on('$locationChangeStart', function (event, newUrl, oldUrl) {
      // Pull tags into active if exist on load
      // @todo: make this tie in better with existing tags...
      $scope.extraTags = [];
      angular.forEach($scope.selectedTags, function (tag) { tag.active = false; });
      $scope.selectedTags = [];
      if ($location.search().tags) {
        if (Array.isArray($location.search().tags)) {
          angular.forEach($location.search().tags, function (tag) {
            $scope.addUnknownTag(tag);
          });
        } else {
          $scope.addUnknownTag($location.search().tags);
        }
      }
      // @todo: remove page info from url
      $scope.updateLocation();

      $scope.queryString = $location.search().q;
    });

    $scope.addUnknownTag = function(tag) {

      var allTags = $scope.mindsetTags;
      var tagFound = false;
      forEach(allTags, function (existingTag) {
        if (existingTag.name === tag) {
          existingTag.active = true;
          tagFound = true;
          if ($scope.selectedTags.indexOf(existingTag) === -1) {
            $scope.selectedTags.push(existingTag);
          }
        }
      });

      // Unknown tag, add to new list (not sure if this works)
      // @todo: test this...
      if (!tagFound) {
        $scope.extraTags.push({
          'name': tag,
          'active': true
        });
      }

    };

    // Main search function

    $scope.fetchResults = function(queryParams) {
      $scope.loading = true;
      $scope.shouldPaginate = false;
      $scope.searchCount += 1;

      // Calculate params for Mixpanel
      $scope.searchList.push(queryParams.q);
      $scope.totalSearchTime = (new Date() - $scope.startTime)/1000;

      // Track search with all queryParams
      mixpanel.track('Search', {
        'Query': queryParams.q || '',
        'Search Count': $scope.searchCount,
        'Search List': $scope.searchList,
        'Total Search Time': $scope.totalSearchTime
      });

      Api.content.search(queryParams).then(function (response) {

        $scope.loading = false;

        if (response && response.data) {
          console.log("Filtering any Chapters from search response...");
          var data = response.data.filter(function (x) {
            return x.kind !== 'Chapter';
          });
          console.log('Search Response', data);
          if ($scope.page > 0) {
            $scope.results = $scope.results.concat(data);
          } else {
            $scope.results = data;
          }

          forEach($scope.results, function (result) {
            if(Array.isArray(result.tags)) {
              result.array = true;
            }
          });

          // Determine if should paginate
          if (data.length >= $scope.pageSize) {
            $scope.shouldPaginate = true;
          }
        }

      });

    };

    // Updates search params and passes to url string

    $scope.updateSearch = function() {
      $scope.suggestions = null;
      $scope.page = 0;

      var queryParams = {};
      queryParams.q = $scope.queryString || '';
      queryParams.tags = querifyTags(
        $scope.tags
          .concat($scope.popularTags)
          .concat($scope.mindsetTags)
          .concat($scope.extraTags)
      );
      queryParams.subjects = querifyTags($scope.schoolSubjects);
      if ($scope.gradeSlider[0] > 0) {
        queryParams.min_grade = $scope.gradeSlider[0];
      }
      if ($scope.gradeSlider[1] < 13) {
        queryParams.max_grade = $scope.gradeSlider[1];
      }
      if ($scope.contentType.length > 0) {
        queryParams.content_type = $scope.contentType;
      }
      if ($scope.contentKind.length > 0) {
        queryParams.kind = $scope.contentKind;
      }

      $location.search(queryParams);
    };

    $scope.clearExtraTags = function () {
      $scope.extraTags = [];
      $scope.updateSearch();
    };

    // Loads more results without changing query

    $scope.loadMore = function() {

      $scope.page += 1;
      $scope.updateLocation();
      // $location.search('page', $scope.page);

    };

    $scope.setContentType = function (type) {

      if (type && type.length > 0) {
        $scope.contentType = type;
      } else {
        $scope.contentType = '';
      }

      $scope.updateSearch();

    };

    $scope.setContentKind = function (kind) {

      if (kind && kind.length > 0) {
        $scope.contentKind = kind;
      } else {
        $scope.contentKind = '';
      }

      $scope.updateSearch();

    };

    $scope.toggleSubject = function(subject) {
      console.log('toggleSubject', subject, $scope.selectedTags);
      subject.active = !subject.active;
      if (subject.active) {
        if (!$scope.selectedTags.find(tag => tag.name === subject.name)) {
          $scope.selectedTags.push(subject);
        }
      } else {
        $scope.selectedTags.remove(subject);
      }
      $scope.updateSearch();
    };

    $scope.toggleFilter = function(filter) {
      console.log('toggleFilter', filter, $scope.selectedTags);
      filter.active = !filter.active;
      $scope.filterCount += filter.active ? 1 : -1;
      if (filter.active) {
        // Catch filters already there (from URL?)
        if (!$scope.selectedTags.find(tag => tag.name === filter.name)) {
          $scope.selectedTags.push(filter);
        }
      } else {
        $scope.selectedTags.remove(filter);
      }
      $scope.updateSearch();
    };

    $scope.removeFilters = function() {
      $scope.filterCount = 0;
      var allTags = $scope.tags.concat($scope.gradeLevels)
                               .concat($scope.schoolSubjects);
      forEach(allTags, function (tag) {
          tag.active = false;
      });
      $scope.updateSearch();
    };

    // Shows some super-useful suggestions for searches!

    $scope.getSuggestions = function() {

      // For now just do text suggestions...
      if ($scope.queryString.length > 0) {
        $scope.suggestions = ElasticSuggest.autocomplete($scope.queryString);
      } else {
        $scope.suggestions = null;
      }
    };

    $scope.useSuggestion = function(suggestion) {

      // Currently assumes a text-search suggestion
      // so just run a search on the normal string
      // @todo: make suggestions into full searches
      // eg. suggestion = {q: '', tags: 'Lesson Plans'}
      $scope.queryString = suggestion.value.q;
      $scope.updateSearch();

    };

    var querifyTags = function(tags) {

      var tagArray = [];

      angular.forEach(tags, function(tag) {
        if (tag.active) {
          tagArray.push(tag.name);
        }
      });

      return tagArray;

    };

  }]);
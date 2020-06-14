angular.module('mskApp')
  .service('ElasticSuggest', ['$q', function Api($q) {

    'use strict';

    var suggestions = [
    {
      name: 'Lesson Plans',
      value: {
        q: 'lesson plans'
      }
    },{
      name: 'Research',
      value: {
        q: 'research'
      }
    },{
      name: 'Growth Mindset',
      value: {
        q: 'growth mindset'
      }
    },{
      name: 'Belonging',
      value: {
        q: 'belonging'
      }
    },{
      name: 'Practice Recommendations',
      value: {
        q: 'practice recommendations'
      }
    }
    ];

    // @todos!!
    // Add weighting to suggestions
    // Add max on results

    var partialMatch = function(string, partialString) {

      // Looks for partial string anywhere in main string
      // Case insensitive!!

      if (string.toLowerCase().indexOf(partialString.toLowerCase()) > -1) {
        return true;
      } else {
        return false;
      }

    };

    this.autocomplete = function(partialString) {

      var results = [];

      // Add basic query
      results.push({
        name: partialString,
        value: {
          q: partialString
        }
      });

      if (partialString.length > 1) {

        for(var i=0; i < suggestions.length; i++) {

          var suggestion = suggestions[i];

          if (partialMatch(suggestion.name, partialString)) {
            results.push(suggestion);
          }

        }

      }

      return results;

    };

    this.basicAutocomplete = function(partialString, suggestionsArray) {

      var results = [];

      if (partialString.length > 0) {

        for(var i=0; i < suggestionsArray.length; i++) {

          var suggestion = suggestionsArray[i];

          // Returns matches unless it's a full match
          if (partialMatch(suggestion, partialString)) {
            results.push(suggestion);
          }

        }

      }

      return results;

    };

  }]);
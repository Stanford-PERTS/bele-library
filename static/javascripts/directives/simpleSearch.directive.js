angular.module('mskApp')
  .directive('simpleSearch', ['$window', '$timeout','Api', function ($window, $timeout, Api) {
    'use strict';
    var linker = function(scope, element, attrs) {
      scope.queryString = '';
      scope.entityType = attrs.entitytype;
      scope.model = {
        selectedPage: {
          'thisis': 'atest',
        },
      };

      scope.$watch('model.selectedPage', function(newValue, oldValue) {
        console.log('newValue', newValue);
        scope.updateSelectedPage({ page: newValue });
      });

      // TODO: redo all users search code using existing search framework and ElasticSuggest.
      // This was the MVP I could make given the time constraint, will try to revisit
      // this before code release to alleviate time complexity issues.
      // - Appstem AH 4/5/19
      scope.sanitizeData = (results) => results.map(result => {
        const { uid, title } = result;
        return ({
          data: { uid, title }, 
          lowercase: { uid: uid.toLowerCase(), title: title.toLowerCase() }
        });
      });

      // Updates suggestions from users search
      scope.updateSearch = function(searchOnKeystroke = false) {
        const results = scope.sanitizeData(scope.fetchedEntities);
        const whitelistedSearchFields = ['title'];
        let suggestions = [];

        results.forEach(searchResult => {
          const { data, lowercase } = searchResult;
          let passesFilter = false;
          whitelistedSearchFields.forEach(field => {
            if (lowercase.hasOwnProperty(field)) {
              if (lowercase[field].indexOf(scope.queryString.toLowerCase()) !== -1) {
                scope.selectedPage = data;
                passesFilter = true;
              }
            }
          });
          if (passesFilter) {
            suggestions.push(searchResult.data);
          }
        });
        // Ensure suggestions are unique
        suggestions = Array.from(new Set(suggestions));
        scope.suggestions = suggestions;
        console.log(suggestions);

      };

      scope.fetchEntities = function () {

        var params = {
          order: 'created'
        };

        const typesWhitelist = ['pages'];

        let entityType = typesWhitelist.includes(scope.entityType) ? scope.entityType : null;
        if (entityType) {
          return Api[entityType].find(params)
            .then( function (response) {
              if(!response.error && response.data && response.data.length > 0) {
                scope.fetchedEntities = response.data;
                scope.entities = {};
                response.data.forEach(entity => {
                  const { uid } = entity;
                  entity.selected = false;
                  scope.entities[uid] = entity;
                });
                console.log(response);
              }
            });
        }
      };

      // scope.selectItem = function(selectedItem) {
      //   const index = scope.users1WithSelected.findIndex(user => user.uid === selectedItem.uid);
      //   const suggestionIndex = scope.suggestions.findIndex(user => user.uid === selectedItem.uid);
      //   if (index === -1) {
      //     return false;
      //   }
      //   const result = !scope.users1WithSelected[index].selected;
      //   scope.users1WithSelected[index].selected = result;
      //   if (result === true) {
      //     scope.selectedItems.push(selectedItem);
      //   } else if (result === false) {
      //     scope.selectedItems.splice(scope.selectedItems.findIndex(user => user.uid === selectedItem.uid), 1);
      //   }
      //   scope.queryString = '';
      //   scope.suggestions = null;
      // };

      // scope.deselectItem = function(selectedItem) {
      //   const index = scope.users1WithSelected.findIndex(user => user.uid === selectedItem.uid);
      //   const targetUserIndex = scope.selectedItems.findIndex(user => user.uid === selectedItem.uid);
      //   if (targetUserIndex === -1) {
      //     return false;
      //   }
      //   scope.selectedItems.splice(targetUserIndex, 1);
      //   scope.users1WithSelected[index].selected = false;
      //   scope.updateSearch();
      // };

      // scope.inviteUsers = function() {
      //   const users = scope.selectedItems.map(selectedItem => scope.userData[selectedItem.uid].uid);
      //   const body = users;
      //   console.log(users, body, scope);
      //   scope.sendingInvites = true;
      //   Api[scope.entityType].inviteUsers(scope.entityId, body)
      //     .then(response => {
      //       scope.sendingInvites = false;
      //       $('#authorshipModal').modal('hide');
      //     })
      //     .catch(error => {
      //       console.error(error);
      //       scope.sendingInvites = false;
      //     });
      // };

      // Initial comment pull.
      scope.fetchEntities()
        .then(() => scope.updateSearch());
    };
    return {
      restrict: 'E',
      scope: {
        entityType: '=entitytype',
        updateSelectedPage: '&'
      },
      link: linker,
      templateUrl: '/static/directives/simple_search.html',
      transclude: true,
    };
  }]);
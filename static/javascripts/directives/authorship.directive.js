angular.module('mskApp')
  .directive('authorshipModal', ['$window', '$timeout','Api', function ($window, $timeout, Api) {
    'use strict';
    var linker = function(scope, element, attrs) {
      scope.selectedUsers = [];
      scope.users1WithSelected = [];
      scope.sendingInvites = false;
      const path = $window.location.pathname || '';
      const patt = /\/([^\/]*)$/gi;
      const match = patt.exec(path);
      const bookPagePatt = /books\/\w*\/\w*\/\w*$/gi;
      const bookPageMatch = bookPagePatt.exec(path);
      scope.entityId = match[1];
      scope.queryString = '';
      let entityType = attrs.entitytype;
      if (!entityType) {
        if (bookPageMatch) {
          entityType = 'pages';
        } else if (path.includes('pages')) {
          entityType = 'pages';
        } else if (path.includes('books')) {
          entityType = 'books';
        }
      }
      scope.myEntityType = entityType;
      scope.model = {
        selectedUser: null,
      };

      scope.$watch('model.selectedUser', function(newValue, oldValue) {
        console.log('newValue', newValue);
        // scope.updateSelectedPage({ page: newValue });
      });


      // TODO: redo all users search code using existing search framework and ElasticSuggest.
      // This was the MVP I could make given the time constraint, will try to revisit
      // this before code release to alleviate time complexity issues.
      // - Appstem AH 4/5/19
      scope.sanitizeUserData = (users) => users.map(user => {
        const { uid, email, username, canonical_username, first_name, last_name, selected } = user;
        const full_name = `${first_name && first_name.toLowerCase()} ${last_name && last_name.toLowerCase()}`;
        return ({
          data: { uid, email, username, first_name, last_name, selected }, 
          lowercase: { uid: uid.toLowerCase(), email: email.toLowerCase(), canonical_username, full_name }
        });
      });

      // Updates suggestions from users search
      scope.updateSearch = function(searchOnKeystroke = false) {
        scope.suggestions = null;
        let suggestions = [];
        if (scope.queryString.length < 2 && searchOnKeystroke) {
          suggestions = [];
          return false;
        }
        const result = scope.sanitizeUserData(scope.users1WithSelected);
        const whitelistedSearchFields = ['uid', 'email', 'canonical_username', 'full_name'];

        result.forEach(searchResult => {
          const { data, lowercase } = searchResult;
          let passesFilter = false;
          whitelistedSearchFields.forEach(field => {
            if (lowercase.hasOwnProperty(field)) {
              if (lowercase[field].indexOf(scope.queryString.toLowerCase()) !== -1) {
                if (scope.selectedUsers.findIndex(user => user.uid === data.uid) === -1) {
                  passesFilter = true;
                }
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

      };

      scope.fetchAuthors = function () {

        var params = { n: 100 };

        Api.users.get(params)
          .then( function (response) {
            if(!response.error && response.data && response.data.length > 0) {
              scope.users1 = response.data;
              scope.userData = {};
              response.data.forEach(user => {
                user.selected = false;
                scope.userData[user.uid] = user;
              });
              // Remove this
              scope.users1WithSelected = scope.users1.map(user => {
                user.selected = false;
                return user;
              });
            }
          });

      };

      scope.selectUser = function(selectedUser) {
        const index = scope.users1WithSelected.findIndex(user => user.uid === selectedUser.uid);
        const suggestionIndex = scope.suggestions.findIndex(user => user.uid === selectedUser.uid);
        if (index === -1) {
          return false;
        }
        const result = !scope.users1WithSelected[index].selected;
        scope.users1WithSelected[index].selected = result;
        if (result === true) {
          scope.selectedUsers.push(selectedUser);
        } else if (result === false) {
          scope.selectedUsers.splice(scope.selectedUsers.findIndex(user => user.uid === selectedUser.uid), 1);
        }
        scope.queryString = '';
        scope.suggestions = null;
      };

      scope.deselectUser = function(selectedUser) {
        const index = scope.users1WithSelected.findIndex(user => user.uid === selectedUser.uid);
        const targetUserIndex = scope.selectedUsers.findIndex(user => user.uid === selectedUser.uid);
        if (targetUserIndex === -1) {
          return false;
        }
        scope.selectedUsers.splice(targetUserIndex, 1);
        scope.users1WithSelected[index].selected = false;
        scope.updateSearch();
      };

      scope.inviteUsers = function() {
        console.log('inviteUsers', scope);
        const users = [scope.model.selectedUser].map(selectedUser => scope.userData[selectedUser.uid].uid);
        const body = users;
        console.log(users, body, scope);
        scope.sendingInvites = true;
        Api[scope.myEntityType].inviteUsers(scope.entityId, body)
          .then(response => {
            scope.sendingInvites = false;
            $('#authorshipModal').modal('hide');
          })
          .catch(error => {
            console.error(error);
            scope.sendingInvites = false;
          });
      };

      scope.hideAuthorshipModal = function() {
        $('#authorshipModal').modal('hide');
      };

      // Initial comment pull.
      scope.fetchAuthors();
    };
    return {
      restrict: 'E',
      scope: {
        entityType: '=entitytype'
      },
      link: linker,
      templateUrl: '/static/directives/modal_authorship.html',
      transclude: true,
    };
  }]);
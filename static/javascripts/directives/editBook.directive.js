angular.module('mskApp')
  .directive('editBookModal', ['$window', '$timeout','Api', 'User', 'hostingDomain', '$q', function ($window, $timeout, Api, User, hostingDomain, $q) {
    'use strict';
    var linker = function(scope, element, attrs) {
      scope.resetVariables = function() {
        // scope.bookName = '';
        // scope.bookSummary = '';
        scope.bookImage = '';
        scope.bookIcon = '';
        scope.models = {};
        scope.selectedTab = 'details';
        scope.editOrCreate = null;
        scope.modalTitle = 'Add Book';

        scope.models.bookName = {
          value: '',
          displayError: false,
          errorMessage: '',
          touched: false,
          dirty: false,
          isFocused: false,
        };
        scope.models.bookSummary = {
          value: '',
          displayError: false,
          errorMessage: '',
          touched: false,
          dirty: false,
          isFocused: false,
        };
        scope.models.bookAcknowledgements = {
          value: '',
          displayError: false,
          errorMessage: '',
          touched: false,
          dirty: false,
          isFocused: false,
        };
        scope.models.bookCitations = {
          value: '',
          displayError: false,
          errorMessage: '',
          touched: false,
          dirty: false,
          isFocused: false,
        };

        scope.filesInfoMap = {
          bookImage: {
            dataProp: 'book_image',
          },
          bookIcon: {
            dataProp: 'icon',
          }
        };

        // Files to upload for specific book fields with files
        scope.filesQueueMap = {
          bookImage: null,
          bookIcon: null
        };

        scope.filesInfoMap = {
          bookImage: {
            dataProp: 'book_image',
          },
          bookIcon: {
            dataProp: 'icon',
          }
        };

        scope.user = User.currentUser(); // get user from User service
      };

      scope.tinymceOptions = {
        plugins: 'link image code media lists',
        toolbar: 'formatselect | bold italic | alignleft aligncenter alignright | numlist bullist | code | media',
        relative_urls : false,
        remove_script_host : false,
        convert_urls : true,
        images_upload_handler: function(blobInfo, success, failure) {
          const file = new File([blobInfo.blob()], blobInfo.filename());
          return Api.books.uploadFile(undefined, file)
            .then(response => {
              const { files } = response.data.json_properties;
              const newFile = files[files.length - 1];
              success(newFile.link);
            })
            .catch(error => failure(error));
        },
      };

      scope.handleFocus = function(fieldName) {
        // We don't want to validate until the field has been touched, so flag it.
        scope.models[fieldName].isFocused = true;
        scope.models[fieldName].touched = true;
      };

      scope.handleBlur = function(fieldName) {
          // If there isn't already an error displayed, validate on blur...
          // so might as well just always validate on blur.
          // However, we don't want to validate if you click on a field and haven't
          // changed anything.
          scope.models[fieldName].isFocused = false;
          if (scope.models[fieldName].dirty === true) {
              scope.checkValidation(true);
          }
      };

      scope.handleChange = function(fieldName) {
          // Mark the field as dirty
          scope.models[fieldName].dirty = true;
          // If there is already an error displayed, we
          // want instant feedback to tell the user they've
          // passed validation.
          if (scope.models[fieldName].displayError) {
              scope.checkValidation(true);
          }
      };

      // Check step is validated and user can continue to next step
      scope.checkValidation = function(onlyCheckTouched = false) {
        const fieldsWithValidation = ['bookName', 'bookSummary'];
        fieldsWithValidation.forEach(fieldName => {
          scope.models[fieldName].displayError = false;
          scope.models[fieldName].errorMessage = '';
        });

        scope.error = '';
        scope.validated = true;
        let validated = true;
        if (!(onlyCheckTouched && !scope.models.bookName.dirty)) {
          if (scope.models.bookName.value.length < 5) {
            scope.validated = false;
            scope.error = 'Book name is too short';
            scope.models.bookName.displayError = true;
            scope.models.bookName.errorMessage = 'Book title must be at least 5 characters';
            validated = false;
          }
        }
        if (!(onlyCheckTouched && !scope.models.bookSummary.dirty)) {
          if (scope.models.bookSummary.value.length < 10) {
            scope.validated = false;
            scope.error = 'Book summary is too short';
            scope.models.bookSummary.displayError = true;
            scope.models.bookSummary.errorMessage = 'Book summary must be at least 10 characters';
            validated = false;
          } else if (scope.models.bookSummary.value.length > 250) {
            scope.validated = false;
            scope.error = 'Book summary is too long';
            scope.models.bookSummary.displayError = true;
            scope.models.bookSummary.errorMessage = 'Book summary cannot be longer than 250 characters';
            validated = false;
          }
        }
        if (validated) {
          scope.validated = true;
        }

        if (!User.currentUser()) {
          scope.validated = false;
        }
        return scope.validated;

      };

      scope.createBook = function () {
        console.log('creating book', scope);
        // Function to finish process and upload the book
        // Formats data entries for POST request

        if (scope.checkValidation() && !scope.creating) {

          console.log('validated');

          // Indicate upload and disable button
          scope.creating = true;

          mixpanel.track('Finish Upload', {
            'Type': scope.bookType,
            'Editing': scope.editPage
          });

          var data = {};

          data.title = scope.models.bookName.value;
          data.short_description = scope.models.bookSummary.value;
          data.acknowledgements = scope.models.bookAcknowledgements.value;
          data.preferred_citation = scope.models.bookCitations.value;

          console.log(data, scope.editPage, scope.created);

          if (!scope.editPage && !scope.created) {

            Api.books.create(data)
              .then(function (response) {
                scope.book = response.data;
                scope.created = true;
                scope.editingBook = response.data;

                console.log('book created', response, scope);
                scope.finishedCallback();
              });

          } else {

            Api.books.update(scope.editingBook, data)
              .then(function (response) {
                scope.book = response.data;

                scope.finishedCallback();
              });
          }
        }

      };

      // Function to move uploaded files from 'filesQueueMap' to scope
      // (Allows files to be managed outside input interface)
      scope.handleFiles = function(fieldName) {

        scope.resourceType = 'files';
        scope.filesQueueMap[fieldName] = scope[fieldName];
        console.log('handleFiles', fieldName, scope.filesQueueMap);
        scope[`${fieldName}TempPath`] = URL.createObjectURL(scope.filesQueueMap[fieldName]);
      };

      scope.finishedCallback = function() {
        // Check for any files and upload
        const filesToAdd = {};
        let filesInfoMapArray = Object.entries(scope.filesInfoMap);
        // Create object of files in queue using scope vars
        filesInfoMapArray.forEach(([scopeProp, dataPropObj]) => {
          const { dataProp } = dataPropObj;
          // Add file to filesToAdd if in queue
          if (!!scope.filesQueueMap[scopeProp]) {
            filesToAdd[dataProp] = scope[scopeProp];
          }
        });
        console.log('finishedCallback', filesToAdd);
        if (Object.entries(filesToAdd).length > 0) {

          uploadFile(filesToAdd, 0).then(function (response) {
            scope.showFinished();
          }, function (error) {
            scope.error = 'Error uploading file, try another.';
            scope.creating = false;
          });

        } else {
          scope.showFinished();
        }
      };

      scope.showFinished = function() {
        scope.resetVariables();
        $('#editBookModal').modal('hide');
        $window.location.href = '/books/manage/' + scope.book.short_uid;
        // scope.bookUrl = '/books/' + scope.book.short_uid;
        // scope.shareUrl = 'https://' + hostingDomain + '/books/' + scope.book.short_uid;
        // scrollToTop();
      };

      scope.handleTabSelect = function(selectedTab) {
        scope.selectedTab = selectedTab;
      };

      scope.setEditPage = function(book) {
        scope.modalTitle = 'Edit book';
        scope.models.bookName.value = book.title;
        scope.models.bookSummary.value = book.short_description;
        scope.bookType = book.type;
        scope.models.bookAcknowledgements.value = book.acknowledgements;
        scope.models.bookCitations.value = book.preferred_citation;
        scope.bookImageTempPath = book.book_image && JSON.parse(book.book_image).link + '?size=2100';
        scope.bookIconTempPath = book.icon && JSON.parse(book.icon).link + '?size=360';

        scope.yearTime = book.time_of_year;
        scope.classPeriod = book.class_period;

        Object.entries(scope.filesInfoMap).forEach(([scopeProp, dataPropObj]) => {
          const { dataProp } = dataPropObj;
          if (book[dataProp]) {
            let result = util.tryParseJSON(book[dataProp]);
            result.name = result.filename;
            scope[scopeProp] = result;
          }
        });

        // if (book.max_grade) {
        //   scope.gradeSlider = [book.min_grade, book.max_grade];
        // }

        // setTagsFromArray(scope.mindsetTags, book.tags);
        // setTagsFromArray(scope.bookTags, book.tags);
        // setTagsFromArray(scope.schoolSubjects, book.subjects);
        // setTagsFromArray(scope.gradeLevels, book.grade_levels);

        scope.editPage = true;
        scope.editingBook = book;
        scope.checkValidation();

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

      // Helper functions....

      // Function to loop through files and upload one at time
      // Async uploading causes errors in json_properties on book
      var uploadFile = function(filesToAdd, index) {

        var def = $q.defer();
        const files = Object.entries(filesToAdd);
        const file = files[index];
        console.log('uploadFile: files:', files, 'file:', file);
        const fields = { entity_field: file && file[0] };
        console.log('files:', files, 'file:', file, 'file[0]', file && file[0]);
        if (file) {
          Api.books.uploadFile(scope.book, file[1], fields)
            .then(function (response) {
              uploadFile(filesToAdd, index + 1).then(function (response) {
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

      scope.resetVariables();

      const path = window.location.pathname;
      const managePatt = /\/books\/manage\/(\w*)$/gi;
      const profilePatt = /profile$/gi;
      const isManage = managePatt.exec(path);
      const isProfile = profilePatt.exec(path);
      if (isManage) {
        scope.bookId = isManage[1];
        scope.editOrCreate = 'edit';
        Api.books.findById(scope.bookId)
          .then( function (response) {
            if (response.data) {
              console.log(response.data);
              scope.setEditPage(response.data);
            }

        });
      } else if (isProfile) {
        scope.editOrCreate = 'create';
      }

      console.log(isManage, isProfile, scope.editOrCreate);

      scope.$on('user:updated', function(event, data) {
        scope.user = User.currentUser();
      });

    };
    return {
      restrict: 'E',
      scope: {
      },
      link: linker,
      templateUrl: '/static/directives/modal_edit_book.html',
      transclude: true,
    };
  }]);
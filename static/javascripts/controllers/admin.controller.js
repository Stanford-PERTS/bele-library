// Angular controller for Administration Page

angular.module('mskApp')
  .controller('AdminController', ['$scope', '$window', '$timeout', 'Api', function ($scope, $window, $timeout, Api) {

    'use strict';

    // Universal variables
    $scope.page = 'main';

    // Kit variables
    $scope.model = 'theme';
    $scope.object = null;
    $scope.newObject = {};
    $scope.childModelPage = 0;

    // Practices variables
    $scope.status = 'pending';

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

      $scope.subjectTags = [
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


    // Operations to switch pages
    $scope.setPage = function(page) {

      $scope.page = page;
      $scope.status = 'pending';

      if (page === 'practices') {
        $scope.fetchPractices(0, true);
      } else if (page === 'pages') {
        $scope.fetchPages($scope.status);
      } else if (page === 'books') {
        $scope.fetchBooks($scope.status);
      } else if (page === 'kits') {
        $scope.model = 'theme';
        $scope.object = null;
        fetchModel('theme', 0);
      } else if (page === 'feedback') {
        $scope.fetchFeedback(0);
      } else { return; }
      $window.location.hash = page;
    };

    $scope.setModel = function(model) {

      $scope.model = model;
      $scope.objects = [];

      if (model === 'theme') {
        fetchModel(model, 0);
      } else if (model === 'topic') {
        fetchModel(model, 0);
      } else if (model === 'lesson') {
        fetchModel(model, 0);
      } else if (model === 'book') {
        fetchModel(model, 0);
      } else if (model === 'chapter') {
        fetchModel(model, 0);
      }
    };

    // Mindset Kit page methods

    $scope.deleteObject = function(object) {

      if (confirm('Are you sure you want to delete this ' + $scope.model + '?')) {

        Api[$scope.model + 's'].delete(object)
          .then( function (response) {

            // Timeout to wait for delete to complete.
            // Plus this shouldn't be a rapid event
            // $timeout(function() {
            //   $scope.fetchModel($scope.model, 1);
            // }, 250);

          });
      }
    };

    $scope.createObject = function() {

      $scope.error = '';

      if ($scope.validateFields($scope.newObject, $scope.model)) {

        $scope.saving = true;

        Api[$scope.model + 's'].create($scope.newObject)
          .then( function(response) {
            $scope.saving = false;
            if (!response.error) {
              $('#adminModal').modal('hide');
              $scope.objects.push(response.data);
              $scope.newObject = {};
            } else {
              $scope.error = 'Error saving data...';
            }
          });

      } else {

        $scope.error = 'Error saving, please check fields';

      }

    };

    // Validation functions

    $scope.validateFields = function(fields, model) {

      if (fields.name.length > 5) {
        if (fields.id.length > 5) {
          if (model === 'lesson' || isColor(fields.color)) {
            if (fields.summary.length > 5) {
              return true;
            }
          }
        }
      }

      return false;

    };

    var isColor = function(colorString) {
      return colorString.match(/^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/);
    };

    $scope.viewObject = function(object) {

      $scope.object = object;
      // Resets update button in editor
      $scope.updated = false;
      // Gets name of model from object uid (ex. Topic_19HFSLA3)
      $scope.model = object.uid.split('_')[0].toLowerCase();
      // Resets children objects before fecthing
      $scope.children = [];

      if ($scope.model === 'theme') {
        $scope.childModel = 'topic';
        $scope.fetchChildren();
      } else if ($scope.model === 'topic') {
        $scope.childModel = 'lesson';
        $scope.fetchChildren();
      } else {
        $scope.childModel = '';
        $scope.loadTags();
      }

    };

    // Individual object pages

    $scope.fetchChildren = function() {

      $scope.submodelObjects = [];
      $scope.existingChild = false;

      Api[$scope.model + 's'].fetchChildren($scope.object)
        .then( function (response){
          if (!response.error && response.data.length > 0) {
            $scope.children = response.data;
          } else {
            $scope.children = [];
          }

          // Load first page of all child model
          // Used for finding children in 'Add' modal
          $scope.loadChildModel(0);

        });

      // Find all lessons if current model is 'theme'
      // And determine which are in 'popular_lessons'
      if ($scope.model === 'theme') {
        $scope.popularLessons = [];

        Api.themes.fetchLessons($scope.object)
          .then( function (response) {
            if (!response.error && response.data.length > 0) {
              $scope.themeLessons = response.data;

              // Then determine popular by examining 'popular_lessons' field
              var popularLessons = $scope.object.popular_lessons;
              if (popularLessons && popularLessons.length > 0) {

                for(var i=0;i<popularLessons.length;i++) {
                  for(var j=0;j<$scope.themeLessons.length;j++) {
                    // Find matching lesson and push
                    if ($scope.themeLessons[j].uid === popularLessons[i]) {
                      $scope.popularLessons.push($scope.themeLessons[j]);
                    }
                  }
                }
              }

            } else {
              $scope.themeLessons = [];
            }
          });
      } else {
        $scope.themeLessons = [];
        $scope.popularLessons = [];
      }

    };

    $scope.loadChildModel = function(page) {

      $scope.childModelPage = page;
      $scope.willLoadMoreChildModel = false;

      Api[$scope.childModel + 's'].fetchAll(page)
        .then( function (response){
          if (!response.error && response.data.length > 0) {

            // Determine if 'load more' button should show
            if (response.data.length >= 20) {
              $scope.willLoadMoreChildModel = true;
            }

            // If not the first page, add items to array
            if (page < 1) {
              $scope.submodelObjects = response.data;
            } else {
              $scope.submodelObjects = $scope.submodelObjects.concat(response.data);
            }

            // Remove children from potential subobjects (no repeats)
            var removeArray = [];
            forEach($scope.submodelObjects, function(x) {
              forEach($scope.children, function(y) {
                if (x.name === y.name) {
                  removeArray.push(x);
                }
              });
            });
            forEach(removeArray, function(x) {
              $scope.submodelObjects.remove(x);
            });

          } else {
            // Only set to empty array if this is first page
            if (page < 1) {
              $scope.submodelObjects = [];
            }
          }
        });

    };

    $scope.loadMoreChildModel = function() {

      $scope.loadChildModel($scope.childModelPage + 1);

    };

    $scope.removeChild = function(child) {

      if (confirm('Remove this ' + $scope.childModel + ' from this ' + $scope.model)) {

        Api[$scope.model + 's'].removeChild($scope.object, child)
          .then( function (response) {
            $scope.children = $scope.children.remove(child);
          });

      }

    };

    $scope.removePopularLesson = function(child) {

      if (confirm('Remove popular lesson from this ' + $scope.model)) {

        Api[$scope.model + 's'].removeChild($scope.object, child)
          .then( function (response) {
            $scope.popularLessons = $scope.popularLessons.remove(child);
          });

      }

    };

    $scope.setExistingChild = function(object) {

      $scope.existingChild = object;
      $scope.newChild = {};
      $scope.showChildrenDropdown = false;

    };

    $scope.addExistingChild = function() {
      if ($scope.existingChild && $scope.existingChild.uid) {
        $scope.saving = true;
        Api[$scope.model + 's'].addChild($scope.object, $scope.existingChild)
          .then( function (response) {

            $scope.saving = false;
            if (!response.error) {
              $('#childModal').modal('hide');
              $scope.children.push($scope.existingChild);
              $scope.submodelObjects.remove($scope.existingChild);
              $scope.newChild = {};
              $scope.existingChild = null;
            } else {
              $scope.error = 'Error saving data...';
            }

          });
      }
    };

    $scope.addPopularLesson = function(lesson) {

      if ($scope.model === 'theme' && lesson) {
        $scope.saving = true;
        Api.themes.addChild($scope.object, lesson)
          .then( function (response) {

            $scope.saving = false;
            if (!response.error) {
              $('#popularModal').modal('hide');
              $scope.popularLessons.push(lesson);
            } else {
              $scope.error = 'Error saving data...';
            }

          });
      }

    };

    $scope.addChild = function() {

      $scope.error = '';

      if ($scope.validateFields($scope.newChild, $scope.childModel)) {

        $scope.saving = true;
        $scope.newChild.parent_uid = $scope.object.uid;

        Api[$scope.childModel + 's'].create($scope.newChild)
          .then( function (response) {
            $scope.saving = false;
            if (!response.error) {
              $('#childModal').modal('hide');
              $scope.children.push(response.data);
              $scope.newChild = {};
            } else {
              $scope.error = 'Error saving data...';
            }
          });

      } else {

        $scope.error = 'Error saving, please check fields';

      }

    };

    $scope.reorderChild = function(child, moveUp) {

      Api[$scope.model + 's'].reorderChild($scope.object, child, moveUp)
        .then( function (response) {
          if (!response.error) {
            // Reorders entities manually in the interface

            var position = $scope.children.indexOf(child);
            if (moveUp) {
              position = position - 1;
            } else {
              position = position + 1;
            }
            $scope.children.remove(child);
            $scope.children.splice(position, 0, child);
          }
        });

    };

    $scope.reorderPopular = function(lesson, moveUp) {

      Api[$scope.model + 's'].reorderChild($scope.object, lesson, moveUp)
        .then( function (response) {
          if (!response.error) {
            // Reorders entities manually in the interface

            var position = $scope.popularLessons.indexOf(lesson);
            if (moveUp) {
              position = position - 1;
            } else {
              position = position + 1;
            }
            $scope.popularLessons.remove(lesson);
            $scope.popularLessons.splice(position, 0, lesson);
          }
        });

    };

    $scope.updateObject = function(object) {

      var params = object;

      if ($scope.model === 'lesson') {
        params.tags = putTagsInArray($scope.mindsetTags.concat($scope.practiceTags));
        params.subjects = putTagsInArray($scope.subjectTags);
      } else {
        delete params.tags;
        delete params.subjects;
      }

      Api[$scope.model + 's'].update(object, params)
        .then( function (response) {
          $scope.updated = true;
        });

    };

    $scope.loadTags = function() {

      if ($scope.object && $scope.model === 'lesson') {

        setTagsFromArray($scope.mindsetTags, $scope.object.tags);
        setTagsFromArray($scope.practiceTags, $scope.object.tags);
        setTagsFromArray($scope.subjectTags, $scope.object.subjects);

      }

    };

    $scope.saveTags = function(object) {

      $scope.saving = true;
      $scope.error = '';

      var data = {};

      data.tags = putTagsInArray($scope.mindsetTags.concat($scope.practiceTags));
      data.subjects = putTagsInArray($scope.subjectTags);

      Api[$scope.model + 's'].update(object, data)
        .then(function (response) {

          $scope.saving = false;
          if (!response.error) {
            $scope.saving = false;
            $('#taggingModal').modal('hide');
          } else {
            $scope.error = 'Error saving data...';
          }

        });
    };

    // Practices page methods

    $scope.setStatus = function(status, model='practice') {
      fetchModel(model, status);
      $scope.status = status;
    };

    function fetchModel(model, status = 'pending') {
      switch (model) {
        case 'book':
          $scope.fetchBooks(status);
          break;
        case 'page':
          $scope.fetchPages(status);
          break;
        default:
          $scope.fetchPractices(0, true);
          break;
      }
    }

    // Practice page methods

    $scope.fetchPractices = function(page, pending, listed, promoted) {

      $scope.practices = [];
      $scope.loading = true;
      $scope.practicePage = 0;
      $scope.shouldPaginate = false;

      var params = {
        pending: pending,
        listed: listed,
        order: '-created'
      };

      if (promoted) {
        params.promoted = true;
      }

      // timeout for cleaner loading UI
      $timeout(function() {

        Api.practices.find(params)
          .then(function (response) {

            $scope.practices = response.data;
            $scope.loading = false;

            // Determine if pagination needed
            if ($scope.practices && $scope.practices.length >= 20) {
              $scope.shouldPaginate = true;
            }

          });

      }, 250);

    };

    $scope.loadMorePractices = function() {

      $scope.practicePage += 1;
      $scope.loading = true;
      $scope.shouldPaginate = false;

      var options = {order: '-created'};
      options.page = $scope.practicePage;

      if ($scope.status === 'pending') {
        options.pending = true;
        options.listed = false;
      } else if ($scope.status === 'promoted') {
        options.promoted = true;
        options.pending = false;
        options.listed = true;
      } else if ($scope.status === 'approved') {
        options.pending = false;
        options.listed = true;
      } else if ($scope.status === 'rejected') {
        options.pending = false;
        options.listed = false;
      }

      Api.practices.find(options)
        .then(function (response) {

          if (response.data && response.data.length > 0) {
            $scope.practices = $scope.practices.concat(response.data);
            // Determine if pagination needed
            if (response.data.length >= 20) {
              $scope.shouldPaginate = true;
            }
          }
          $scope.loading = false;

        });

    };

    $scope.editPractice = function(practice) {

      $window.location = 'practices/edit/' + practice.short_uid;

    };

    $scope.promotePractice = function(practice) {

      if (practice) {
        var promoted = !practice.promoted;

        Api.practices.update(practice,
          {
            listed: true,
            pending: false,
            promoted: promoted
          }).then( function (response) {

            practice.pending = false;
            practice.listed = true;
            practice.promoted = promoted;

          });
      }

    };

    $scope.approvePractice = function(practice, approved) {

      if (practice) {
        var params = {
          listed: approved,
          pending: false
        };
        if (!approved) {
          params.promoted = false;
        }
        Api.practices.update(practice, params)
          .then( function (response) {

            practice.pending = false;
            practice.listed = approved;
            practice.promoted = params.promoted;

          });
      }
    };

    $scope.destroyPractice = function(practice) {

      if (practice) {
        if (confirm('Are you sure you want to destroy this practice?')) {
          var params = {
            deleted: true
          };
          Api.practices.update(practice, params)
            .then( function (response) {

              practice.deleted = true;
              $scope.practices.remove(practice);

            });
        }
      }
    };

    $scope.initAssociation = function(practice) {

      $scope.associatingPractice = practice;
      $('#associationModal').modal('show');

      Api.themes.fetchAll().then( function (response) {
        if (response.data) {
          $scope.associationOptions = response.data;
          angular.forEach(response.data, function (value, key) {
            var theme = value;
            if (theme.name === 'Growth Mindset for Teachers') {
              // Cannot directly associate with Teacher theme
              $scope.associationOptions.splice(key, 1);
              // Only fetch specific topics for Teacher theme
              Api.themes.fetchChildren(theme).then( function (response) {
                $scope.associationOptions = $scope.associationOptions.concat(response.data);
              });
            }
          });
        }
      });

    };

    $scope.associateContent = function(content) {

      // Use practice from $scope.associatingPractice
      // Use Api call to associate (just setting one thing)

      Api.practices.associateContent($scope.associatingPractice, content)
        .then(function (response) {

          if (!response.error) {
            $scope.associatingPractice.associated_content = content.uid;
          }

          // Close modal
          $('#associationModal').modal('hide');

        });

    };

    // Book page methods

    $scope.fetchBooks = function(status) {

      $scope.books = [];
      $scope.loading = true;
      $scope.bookPage = 0;
      $scope.shouldPaginate = false;

      var params = {
        status,
        order: '-created'
      };

      // timeout for cleaner loading UI
      $timeout(function() {

        Api.books.find(params)
          .then(function (response) {
            console.log(params, response);
            $scope.books = response.data;
            $scope.loading = false;

            // Determine if pagination needed
            if ($scope.books && $scope.books.length >= 20) {
              $scope.shouldPaginate = true;
            }

          });

      }, 250);

    };

    $scope.loadMoreBooks = function() {

      $scope.bookPage += 1;
      $scope.loading = true;
      $scope.shouldPaginate = false;

      var options = {order: '-created'};
      options.page = $scope.bookPage;

      if ($scope.status === 'pending') {
        options.pending = true;
        options.listed = false;
      } else if ($scope.status === 'promoted') {
        options.promoted = true;
        options.pending = false;
        options.listed = true;
      } else if ($scope.status === 'approved') {
        options.pending = false;
        options.listed = true;
      } else if ($scope.status === 'rejected') {
        options.pending = false;
        options.listed = false;
      }

      Api.books.find(options)
        .then(function (response) {

          if (response.data && response.data.length > 0) {
            $scope.books = $scope.books.concat(response.data);
            // Determine if pagination needed
            if (response.data.length >= 20) {
              $scope.shouldPaginate = true;
            }
          }
          $scope.loading = false;

        });

    };

    $scope.editBook = function(book) {

      $window.location = 'books/manage/' + book.short_uid;

    };

    $scope.promoteBook = function(book) {

      if (book) {
        var promoted = !book.promoted;

        Api.books.update(book,
          {
            listed: true,
            pending: false,
            promoted: promoted
          }).then( function (response) {

            book.pending = false;
            book.listed = true;
            book.promoted = promoted;

          });
      }

    };

    $scope.approveBook = function(book, approved) {

      if (book) {
        var params = {
          listed: approved,
          status: 'approved',
          pending: false
        };
        if (!approved) {
          params.promoted = false;
          params.status = 'rejected';
        }
        Api.books.update(book, params)
          .then( function (response) {
            var updatedBook = response.data;
            book.pending = updatedBook.pending;
            book.listed = updatedBook.listed;
            book.promoted = updatedBook.promoted;
            book.status = updatedBook.status;

          });

        const chapterParams = {
          listed: approved,
        };

        const approveChapterPromiseChain = (remainingChapters) => {
          if (remainingChapters.length > 0) {
            const nextChapter = remainingChapters.shift();
            Api.chapters.update(nextChapter, chapterParams)
              .then(() => approveChapterPromiseChain(remainingChapters));
          }
        };

        approveChapterPromiseChain(book.chapters);
      }
    };

    $scope.destroyBook = function(book) {

      if (book) {
        if (confirm('Are you sure you want to destroy this book?')) {
          var params = {
            deleted: true,
            listed: false,
            status: 'deleted',
          };

          Api.books.update(book, params)
            .then( function (response) {

              book.deleted = true;
              book.listed = false;
              book.status = 'deleted';
              $scope.books.remove(book);

            });

          const chapterParams = {
            deleted: true,
            listed: false,
          };

          const deleteChapterPromiseChain = (remainingChapters) => {
            if (remainingChapters.length > 0) {
              const nextChapter = remainingChapters.shift();
              Api.chapters.update(nextChapter, chapterParams)
                .then(() => deleteChapterPromiseChain(remainingChapters));
            }
          };

          deleteChapterPromiseChain(book.chapters);
        }
      }
    };

    $scope.initAssociation = function(book) {

      $scope.associatingBook = book;
      $('#associationModal').modal('show');

      Api.themes.fetchAll().then( function (response) {
        if (response.data) {
          $scope.associationOptions = response.data;
          angular.forEach(response.data, function (value, key) {
            var theme = value;
            if (theme.name === 'Growth Mindset for Teachers') {
              // Cannot directly associate with Teacher theme
              $scope.associationOptions.splice(key, 1);
              // Only fetch specific topics for Teacher theme
              Api.themes.fetchChildren(theme).then( function (response) {
                $scope.associationOptions = $scope.associationOptions.concat(response.data);
              });
            }
          });
        }
      });

    };

    $scope.associateContent = function(content) {

      // Use book from $scope.associatingBook
      // Use Api call to associate (just setting one thing)

      Api.books.associateContent($scope.associatingBook, content)
        .then(function (response) {

          if (!response.error) {
            $scope.associatingBook.associated_content = content.uid;
          }

          // Close modal
          $('#associationModal').modal('hide');

        });

    };

    // Page page methods

    $scope.fetchPages = function(status) {

      $scope.pages = [];
      $scope.loading = true;
      $scope.pagePage = 0;
      $scope.shouldPaginate = false;

      var params = {
        status,
        order: '-display_order'
      };

      // timeout for cleaner loading UI
      $timeout(function() {

        Api.pages.find(params)
          .then(function (response) {

            $scope.pages = response.data;
            $scope.loading = false;

            // Determine if pagination needed
            if ($scope.pages && $scope.pages.length >= 20) {
              $scope.shouldPaginate = true;
            }

          });

      }, 250);

    };

    $scope.loadMorePages = function() {

      $scope.pagePage += 1;
      $scope.loading = true;
      $scope.shouldPaginate = false;

      var options = {order: '-created'};
      options.page = $scope.pagePage;

      if ($scope.status === 'pending') {
        options.pending = true;
        options.listed = false;
      } else if ($scope.status === 'promoted') {
        options.promoted = true;
        options.pending = false;
        options.listed = true;
      } else if ($scope.status === 'approved') {
        options.pending = false;
        options.listed = true;
      } else if ($scope.status === 'rejected') {
        options.pending = false;
        options.listed = false;
      }

      Api.pages.find(options)
        .then(function (response) {

          if (response.data && response.data.length > 0) {
            $scope.pages = $scope.pages.concat(response.data);
            // Determine if pagination needed
            if (response.data.length >= 20) {
              $scope.shouldPaginate = true;
            }
          }
          $scope.loading = false;

        });

    };

    $scope.editPage = function(page) {

      $window.location = 'pages/edit/' + page.short_uid;

    };

    $scope.promotePage = function(page) {

      if (page) {
        var promoted = !page.promoted;

        Api.pages.update(page,
          {
            listed: true,
            pending: false,
            promoted: promoted
          }).then( function (response) {

            page.pending = false;
            page.listed = true;
            page.promoted = promoted;

          });
      }

    };

    $scope.approvePage = function(page, approved) {

      if (page) {
        var params = {
          listed: approved,
          status: 'approved',
          pending: false
        };
        if (!approved) {
          params.promoted = false;
          params.status = 'rejected';
        }
        Api.pages.update(page, params)
          .then( function (response) {
            var updatedPage = response.data;
            page.pending = updatedPage.pending;
            page.listed = updatedPage.listed;
            page.promoted = updatedPage.promoted;
            page.status = updatedPage.status;

          });
      }
    };

    $scope.destroyPage = function(page) {

      if (page) {
        if (confirm('Are you sure you want to destroy this page?')) {
          var params = {
            deleted: true,
            listed: false,
            status: 'deleted',
          };
          Api.pages.update(page, params)
            .then( function (response) {

              page.deleted = true;
              page.statuss = 'deleted';
              page.listed = 'false';
              $scope.pages.remove(page);

            });
        }
      }
    };

    $scope.initAssociation = function(page) {

      $scope.associatingPage = page;
      $('#associationModal').modal('show');

      Api.themes.fetchAll().then( function (response) {
        if (response.data) {
          $scope.associationOptions = response.data;
          angular.forEach(response.data, function (value, key) {
            var theme = value;
            if (theme.name === 'Growth Mindset for Teachers') {
              // Cannot directly associate with Teacher theme
              $scope.associationOptions.splice(key, 1);
              // Only fetch specific topics for Teacher theme
              Api.themes.fetchChildren(theme).then( function (response) {
                $scope.associationOptions = $scope.associationOptions.concat(response.data);
              });
            }
          });
        }
      });

    };

    $scope.associateContent = function(content) {

      // Use page from $scope.associatingPage
      // Use Api call to associate (just setting one thing)

      Api.pages.associateContent($scope.associatingPage, content)
        .then(function (response) {

          if (!response.error) {
            $scope.associatingPage.associated_content = content.uid;
          }

          // Close modal
          $('#associationModal').modal('hide');

        });

    };

    // Feedback page methods

    $scope.fetchFeedback = function() {

      $scope.loading = true;
      $scope.feedbackPage = 0;
      $scope.shouldPaginate = false;

      var options = {order: '-created'};
      options.page = $scope.feedbackPage;

      Api.feedback.fetch(options)
        .then(function (response) {

          if (response.data && response.data.length > 0) {
            $scope.feedback = response.data;
            // Determine if pagination needed
            if (response.data.length === 20) {
              $scope.shouldPaginate = true;
            }
          }
          $scope.loading = false;
        });

    };

    $scope.loadMoreFeedback = function() {

      $scope.loading = true;
      $scope.feedbackPage += 1;
      $scope.shouldPaginate = false;

      var options = {order: '-created'};
      options.page = $scope.feedbackPage;

      Api.feedback.fetch(options)
        .then(function (response) {

          if (response.data && response.data.length > 0) {
            $scope.feedback = $scope.feedback.concat(response.data);
            // Determine if pagination needed
            if (response.data.length === 20) {
              $scope.shouldPaginate = true;
            }
          }
          $scope.loading = false;
        });

    };

    // Repopulates data (localhost only)
    $scope.repopulate = function () {

      if (confirm('This will delete and repopulate all data, is that ok?')) {

        // $ajax({url: '/api/delete_everything'})
        //   .then(function () {

            // $ajax({url: '/api/populate'})
            //   .then(function () {
            //     $window.location.reload();
            //   });

          // });

      }

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

    // Formats tag arrays into data from API
    var setTagsFromArray = function (tags, array) {
      if (array && array.length > 0) {
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

    $scope.setDisplayOrder = function(entity, order) {
      const { uid } = entity;
      let entityType = uid.slice(0, uid.indexOf('_')).toLowerCase();
      entityType = `${entityType}s`;
      if (entityType && entity) {
        if (order < 1 || order > 99) {
          entity.display_order = order;
          entity.error = 'Target order value must be between 1 and 99.';
          return false;
        }
        entity.error = null;

        Api[entityType].update(entity, {
          listed: true,
          pending: false,
          display_order: order,
        }).then(() => {
          entity.pending = false;
          entity.listed = true;
          entity.display_order = order;
        });
      }

    };

    // Initialization code

    // Set page based on hash in url

    if ($window.location.hash.length > 0) {
      $scope.setPage($window.location.hash.substr(1));
    }

  }]);

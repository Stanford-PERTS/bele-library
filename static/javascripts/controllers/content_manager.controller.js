// Angular controller for handling page search page

angular.module('mskApp')
  .controller('ContentManagerCtrl', ['$q', '$scope', '$window', 'Api', 'User', 'Share', 'Engagement', function ($q, $scope, $window, Api, User, Share, Engagement) {

    'use strict';

    $scope.resetChapterModalVariables = function() {
        $scope.chapterModalType = 'create';
        $scope.chapterModalModel = {
            uid: {
                value: '',
                displayError: false,
                errorMessage: '',
                touched: false,
                dirty: false,
                isFocused: false,
            },
            title: {
                value: '',
                displayError: false,
                errorMessage: '',
                touched: false,
                dirty: false,
                isFocused: false,
            },
            description: {
                value: '',
                displayError: false,
                errorMessage: '',
                touched: false,
                dirty: false,
                isFocused: false,
            },
        };
    };

    $scope.resetVariables = function() {
        $scope.loading = false;
        $scope.updating = false;
        $scope.updated = false;
        $scope.title = '';
        $scope.description = '';
        $scope.a1 = '';
        $scope.a2 = '';
        $scope.error = null;
        $scope.user = User.currentUser(); // get user from User service
        $scope.disableAssociationPrompt = true; // TODO: add checkmark UI to disable prompts if it gets annoying
        $scope.expanded = {};
        $scope.selectedPage = {'thisIs': 'aTest'};
        $scope.selectedChapter = {};
        $scope.resetChapterModalVariables();
    };

    $scope.resetVariables();

    $scope.init = function(initExpandedChapter) {
        $scope.expanded = { [initExpandedChapter]: true };
    };

    // Watch for selected page from directive
    $scope.updateSelectedPage = function(page) {
        // console.log(page);
        $scope.selectedPage = page;
    };

    $scope.$on('user:updated', function(event, data) {
        $scope.user = User.currentUser();
        $scope.loading = true;
        return $q.all([$scope.getSortable(), $scope.getPages($scope.user)])
            .then(([sortableResponse, pagesResponse]) => {
                // console.log(sortableResponse);
                let chapters = [];
                if(!sortableResponse.error && sortableResponse.data && sortableResponse.data.length > 0) {
                    chapters = sortableResponse.data[0].columns;
                    // All chapter drawers expanded by default.
                    angular.forEach(chapters, function (ch) {
                        $scope.expanded[ch.uid] = true;
                    });
                }
                $scope.models = {
                    chapters: {
                        items: chapters,
                    }
                };
                $scope.original = $scope.models;
                $scope.loading = false;
                // $scope.$apply();
            }).catch(error => {
                console.dir(error);
                $scope.error = `Error loading authored content: <${error.message ? error.message : error}>`;
                $scope.loading = false;
                // $scope.$apply();
            });
    });

    $scope.updateSelectedPage = function(page, chapter) {
        // console.log('updateSelectedPage', page);
        $scope.selectedPage = page;
    };

    $scope.initEditBookModal = function() {
      $('#editBookModal').modal('show');
    };

    $scope.openConfirmDeleteModal = function () {
      $scope.entityPendingDelete = $scope.book;
      $('#confirmDeleteModal').modal('show');
    };

    // Fetch sortable content in a custom api call for this content mgmt UI
    $scope.getSortable = () => Api.books.fetchSortable($scope.book.uid);

    $scope.getPages = (user) => Api.users.fetchPages(user);

    $scope.toggledisableAssociationPrompt = () => {
        $scope.disableAssociationPrompt = !$scope.disableAssociationPrompt;
    };

    $scope.handleDndCopied = (e, item, container) => {
        // console.log("handleDndCopied, deleting...");
        return $scope.delete(container, item);
    };

    $scope.reorderPages = (chapter, srcIndex, targetIndex) => {
        // console.log("reorderPages", chapter, page, targetIndex);
        var page = chapter.columns.splice(srcIndex, 1)[0];
        chapter.columns.splice(targetIndex, 0, page);
        const pageIds = [];
        for (let i = 0; i < chapter.columns.length; i++) {
            pageIds.push(chapter.columns[i].uid);
        }
        return Api.chapters.reorderPages(chapter.uid, pageIds)
            .then(response => {
                // console.log('content_manager, Api.chapter.reorderPages:', response);
            });
    };

    $scope.handleChapterReorderChild = (e, item, container, source, index) => {
        // console.log("handleChapterReorderChild");
        // console.log("source.splice(index, 1)", index, 1);
        // console.log("source: ", JSON.stringify(source));
        source.splice(index, 1);
        const chapters = source.map(chapter => chapter.uid);
        Api.books.reorderChapters($scope.book.uid, chapters)
            .then(response => {
                // console.log('content_manager, Api.book.reorderChapters:', response);
            });
    };

    $scope.handlePageInsert = (chapter, moveOrCopy, index) => {
        // console.log('handlePageInsert', chapter, moveOrCopy, index);
        $scope.insertedChapter = chapter;
        $scope.insertedChapterIndex = index;
    };

    $scope.associate = (item1, item2, options) => {
        options = options || {};
        // console.log("associate()", item1, item2, options);
        var index = options.index;
        var moveOrCopy = options.moveOrCopy;

        const { uid:uid1, name:name1, type:type1 } = item1;
        const { uid:uid2, name:name2, type:type2 } = item2;
        const message =
            'You are about to associate ' + type1 + ' "' + name1 + '" ' +
            'with "' + type2 + '" ' + name2 + '".\n\n' +
            'You are also deleting your previous association. Are you sure?';
        const response = $scope.disableAssociationPrompt ? true : window.confirm(message);
        if (response === true) {
            // console.log('Associating:', uid1, uid2, index);
            return Api.content.associate(
                uid1,
                uid2,
                {index: index, moveOrCopy: moveOrCopy}
            ).then(function (response) {
                // console.log(response);
                // TODO: Add error handling and additional response processing
            });
        } else {
            return false;
        }
    };

    function removeChapter(chapter) {
        // console.log("splicing out chapter");
        var indexToDelete = $scope.models.chapters.items.indexOf(chapter);
        $scope.models.chapters.items.splice(indexToDelete, 1);
    }

    $scope.handleDeleteChapter = function (chapter) {
        // console.log("delete chapter", chapter);
        var message =
            'Are you sure you want to delete chapter "' + chapter.name + '"?' +
            '\n\nContained pages will NOT be deleted.';
        // console.log("chapters:", $scope.models.chapters);
        if (confirm(message)) {
            // console.log("calling DELETE");
            Api.chapters.remove(chapter.uid).then(function (response) {
                if (response.error === false) {
                    removeChapter(chapter);
                }
            });
        }
    };

    $scope.handleClickEditPage = (page, chapter = '') => {
        const { uid } = page;
        $window.location.href = '/pages/edit/' + uid + '?chapter_id=' + chapter;
    };

    $scope.handleClickDeletePage = (chapter, page) => {
        const index = chapter.columns.findIndex(chapterPage => chapterPage.uid === page.uid);
        var deleteConfirmed = $scope.delete(chapter, page, true);
        if (deleteConfirmed !== false) {
            chapter.columns.splice(index, 1);
        }
    };

    $scope.handleClickAddExistingPage = (chapter) => {
        // console.log('handleClickAddExistingPage', chapter);
        $scope.selectedChapter = chapter;
        $('#addExistingPageModal').modal('show');
    };

    $scope.delete = (item1, item2, doConfirmFirst = false) => {
        const { uid:uid1, name:name1, type:type1 } = item1;
        const { uid:uid2, name:name2, type:type2 } = item2;
        const message =
            'You are about to delete ' + type2 + ' "' + name2 + '" ' +
            'from ' + type1 + ' "' + name1 + '".\n\n' +
            'Are you sure?';
        const response = doConfirmFirst ? window.confirm(message) : true;
        if (response === true) {
            // console.log(`Deleting: ${uid1} <-> ${uid2}`);
            return Api.content.deleteChild(uid1, uid2)
                .then(response => {
                    // console.log(response);
                    // TODO: Add error handling and additional response processing
                });
        } else {
            return false;
        }
    };

    $scope.toggleDrawerExpand = (chapter_uid) => {
        // console.log($scope, chapter_uid);
        let val = $scope.expanded[chapter_uid];
        if (val === undefined) {
            val = false;
        }
        val = !$scope.expanded[chapter_uid];
        $scope.expanded[chapter_uid] = val;
    };

    $scope.checkValidation = (onlyCheckTouched = false) => {
        const fieldsWithValidation = ['title', 'description'];
        fieldsWithValidation.forEach(fieldName => {
            $scope.chapterModalModel[fieldName].displayError = false;
            $scope.chapterModalModel[fieldName].errorMessage = '';
        });
        const titleMinLength = 5;
        const descriptionMinLength = 10;
        const descriptionMaxLength = 250;
        let valid = true;
        if (!(onlyCheckTouched && !$scope.chapterModalModel.title.dirty)) {
            if ($scope.chapterModalModel.title.value.length < titleMinLength) {
                $scope.chapterModalModel.title.displayError = true;
                $scope.chapterModalModel.title.errorMessage = `Chapter title must be at least ${titleMinLength} characters.`;
                valid = false;
            }
        }
        if (!(onlyCheckTouched && !$scope.chapterModalModel.description.dirty)) {
            if ($scope.chapterModalModel.description.value.length > descriptionMaxLength) {
                $scope.chapterModalModel.description.displayError = true;
                $scope.chapterModalModel.description.errorMessage = `Chapter description cannot be more than ${descriptionMaxLength} characters.`;
                valid = false;
            } else if ($scope.chapterModalModel.description.value.length < descriptionMinLength) {
                $scope.chapterModalModel.description.displayError = true;
                $scope.chapterModalModel.description.errorMessage = `Chapter description must be at least ${descriptionMinLength} characters.`;
                valid = false;
            }
        }
        return valid;
    };

    $scope.addChapter = function (isValid) {

        $scope.submitted = true;

        if ($scope.checkValidation()) {

            $scope.errorMessage = '';

            var params = {};
            params.title = $scope.chapterModalModel.title.value;
            params.short_description = $scope.chapterModalModel.description.value;

            const bookId = $scope.book.uid;

            $scope.updating = true;
            let modalTypeError = false;
            let apiFuncName;

            let editChapterPromise;
            if ($scope.chapterModalType === 'edit') {
                editChapterPromise = Api.chapters.update($scope.chapterModalModel.uid.value, params);
            } else if ($scope.chapterModalType === 'create') {
                editChapterPromise = Api.chapters.create(params);
            } else {
                modalTypeError = true;
            }
            if (!modalTypeError) {
                editChapterPromise
                  .then(function (response) {
                    let promise = $q.when();
                    if (response.error) {
                        $scope.updating = false;
                        $scope.errorMessage = 'Error with data. Try again.';
                    } else {
                        if ($scope.chapterModalType === 'create') {
                            const parentId = bookId;
                            const childId = response.data.uid;
                            promise = Api.content.associate(parentId, childId);
                        } else if ($scope.chapterModalType === 'edit') {

                        } else {
                            $scope.updating = false;
                            $scope.errorMessage = 'Error with chapterModalType. Try again.';
                        }
                    }
                    return promise.then(() => {
                        $scope.resetChapterModalVariables();
                        $window.location.reload();
                    });
                  });
            }

            } else {
                $scope.errorMessage = 'Missing or invalid parameters.';
            }

    };

    $scope.addExistingPage = function() {
        // console.log('adding existing page');
        // console.log($scope.selectedChapter, $scope.matchedPage);
        const chapter = {
            uid: $scope.selectedChapter.uid,
            type: 'chapter',
            name: $scope.selectedChapter.title,
        };
        const page = {
            uid: $scope.matchedPage.uid,
            type: 'page',
            name: $scope.matchedPage.title,
        };
        $scope.associate(chapter, page)
            .then(() => {
                $('#addExistingPageModal').modal('hide');
                $window.location.href = $window.location.href.replace(/\?.*$/, '') + '?expand=' + $scope.selectedChapter.uid.replace(/^Chapter_/, '');
            });
    };

    $scope.handleClickAddChapterModal = function(editOrCreate, chapter) {
        if (editOrCreate === undefined) {
            editOrCreate = 'edit';
        }
        $scope.resetChapterModalVariables();
        // console.log(editOrCreate, chapter, $scope);
        $scope.chapterModalType = editOrCreate;
        if (['edit', 'create'].includes(editOrCreate)) {
            if (editOrCreate === 'edit') {
                // console.log($scope);
                $scope.chapterModalModel.uid.value = chapter.uid;
                $scope.chapterModalModel.title.value = chapter.name;
                $scope.chapterModalModel.description.value = chapter.short_description;
            }
            $('#addChapterModal').modal('show');
        }
    };

    $scope.handleDragOverChapter = function(chapter) {
        // console.log('handleDragOverChapter', chapter, $scope.dragoverChapter);
        $scope.dragoverChapter = chapter.uid;
    };

    $scope.onDrop = function(srcChapter, srcIndex, targetChapter, targetIndex) {
        var srcList = srcChapter.columns;
        var targetList = targetChapter.columns;
        $scope.insertedPage = srcList[srcIndex];
        // console.log("onDrop()", srcChapter, srcIndex, targetChapter, targetIndex);

        if (srcChapter.uid === targetChapter.uid) {
            // console.log("reodering within chapter");
            $scope.reorderPages(srcChapter, srcIndex, targetIndex);
        } else {
            // console.log("cross-chapter move: assc with new chapter, delete from old");
            $scope.associate(
                targetChapter,
                $scope.insertedPage,
                {index: targetIndex, moveOrCopy: 'move'}
            ).then(function () {
                // console.log("Post associate");
                $scope.handleDndCopied(undefined, $scope.insertedPage, srcChapter);

                // console.log("srcList.splice(srcIndex, 1)", srcIndex, 1);
                // console.log("srcList: ", JSON.stringify(srcList));
                srcList.splice(srcIndex, 1);

                // console.log("targetList.splice(" + targetIndex + ", 0, page");
                // console.log("targetList: ", JSON.stringify(targetList));
                // console.log("page: ", JSON.stringify($scope.insertedPage));
                targetList.splice(targetIndex, 0, $scope.insertedPage);
            });
        }
    };

    $scope.handleFocus = function(fieldName) {
        // We don't want to validate until the field has been touched, so flag it.
        $scope.chapterModalModel[fieldName].touched = true;
        $scope.chapterModalModel[fieldName].isFocused = true;
    };

    $scope.handleBlur = function(fieldName) {
        // If there isn't already an error displayed, validate on blur...
        // so might as well just always validate on blur.
        // However, we don't want to validate if you click on a field and haven't
        // changed anything.
        $scope.chapterModalModel[fieldName].isFocused = false;
        if ($scope.chapterModalModel[fieldName].dirty === true) {
            $scope.checkValidation(true);
        }
    };

    $scope.handleChange = function(fieldName) {
        // Mark the field as dirty
        $scope.chapterModalModel[fieldName].dirty = true;
        // If there is already an error displayed, we
        // want instant feedback to tell the user they've
        // passed validation.
        if ($scope.chapterModalModel[fieldName].displayError) {
            $scope.checkValidation(true);
        }
    };

    $scope.matchExistingPageURL = function() {
        let valid = true;
        if ($scope.addExistingPageURL && $scope.addExistingPageURL.length > 0) {
            const regex = /pages\/(.*)\/?|books\/.*\/(.*)\/?/;
            const matched = $scope.addExistingPageURL.match(regex);
            matched.shift();
            let pageId = '';
            matched.forEach((match) => {
              if (match) {
                pageId = `Page_${match.replace(/^Page_/, '')}`;
              }
            });
            if (pageId) {
              Api.pages.findById(pageId)
                .then((result) => {
                  if (result.data.uid === pageId) {
                    $scope.matchedPage = result.data;
                  }
                });
            } else {
                valid = false;
            }
        } else {
            valid = false;
        }

        if (!valid) {
            $scope.matchedPage = null;
        }
    };

  }]);


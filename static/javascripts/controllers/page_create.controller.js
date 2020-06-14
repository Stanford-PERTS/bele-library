// Angular controller for page uploading (create) page

angular.module("mskApp").controller("PageCreateCtrl", [
  "$scope",
  "$q",
  "$window",
  "Api",
  "User",
  "hostingDomain",
  function($scope, $q, $window, Api, User, hostingDomain) {
    "use strict";

    // Helper object that maps scope vars to data properties
    $scope.additionalInfoMap = {
      pageName: {
        defaultValue: "",
        dataProp: "title"
      },
      pageSummary: {
        defaultValue: "",
        dataProp: "short_description"
      },
      pageBody: {
        defaultValue: "",
        dataProp: "body"
      },
      pageTime: {
        defaultValue: "",
        dataProp: "time_required"
      },
      pageMaterials: {
        defaultValue: "",
        dataProp: "required_materials"
      },
      pageEvidence: {
        defaultValue: "",
        dataProp: "evidence_of_effectiveness"
      },
      pagePreconditions: {
        defaultValue: "",
        dataProp: "preconditions_for_success"
      },
      pageEquity: {
        defaultValue: "",
        dataProp: "advances_equity"
      },
      pageLicense: {
        defaultValue: "",
        dataProp: "use_license"
      },
      pageMeasures: {
        defaultValue: "",
        dataProp: "associated_measures"
      },
      pageAdditionalTags: {
        defaultValue: "",
        dataProp: "additional_tags"
      },
      pageAcknowledgements: {
        defaultValue: "",
        dataProp: "acknowledgements"
      },
      pageCitations: {
        defaultValue: "",
        dataProp: "preferred_citation"
      },
      minGrade: {
        defaultValue: 0,
        dataProp: "min_grade"
      },
      maxGrade: {
        defaultValue: 13,
        dataProp: "max_grade"
      },
      yearTime: {
        defaultValue: "",
        dataProp: "time_of_year"
      },
      classPeriod: {
        defaultValue: "",
        dataProp: "class_period"
      },
      pageIconPath: {
        default: undefined,
        dataProp: "iconPath"
      },
      relatedPages: {
        defaultValue: [],
        dataProp: "related_pages"
      }
      // TODO: handle these externally (upload service)
      // pageIcon: {
      //   defaultValue: '',
      //   dataProp: '',
      // },
      // pageResources: {
      //   defaultValue: [],
      //   dataProp: '',
      // },
    };

    /*
     * Helper function that either sets the scope from data, or returns a data object using
     * scope values.
     */
    $scope.setValues = (target, useDefaultValues, fieldDataMap, data) => {
      useDefaultValues = useDefaultValues || false;
      let result = {};
      // Initialize additional info vars with default values
      Object.keys(fieldDataMap).forEach(scopeProperty => {
        const { defaultValue, dataProp } = fieldDataMap[scopeProperty];
        let targetValue = defaultValue;
        if (target === "scope") {
          if (!useDefaultValues) {
            targetValue = data[dataProp];
          }
          $scope.models[scopeProperty] = {
            value: targetValue,
            displayError: false,
            errorMessage: "",
            touched: false,
            dirty: false,
            isFocused: false
          };
        } else if (target === "data") {
          if (!useDefaultValues) {
            targetValue = $scope.models[scopeProperty].value;
          }

          result[dataProp] = targetValue;
        }
      });

      if (target === "scope") {
        return true;
      } else if (target === "data") {
        return result;
      }
      return false;
    };

    // Initialize all variables used by view.

    $scope.resetVariables = function() {
      $scope.models = {};
      $scope.files = [];
      $scope.freshFiles = [];
      $scope.oldFiles = []; // For editing...
      $scope.relatedPages = [];

      $scope.step = 1; // Change to 2 or 3 for testing
      $scope.resourceType = "";
      $scope.validated = false;
      $scope.pageUrl = "/page";
      $scope.created = false; // Used for catching file upload error after creation
      $scope.shareUrl = "https://" + hostingDomain + "/pages";
      $scope.shareText = encodeURIComponent(
        "I just uploaded a new #mindset page - "
      );

      $scope.setValues("scope", true, $scope.additionalInfoMap);

      $scope.tags = [
        {
          name: "Framework",
          active: false
        },
        {
          name: "External Service",
          active: false
        },
        {
          name: "Student Activity",
          active: false
        },
        {
          name: "Adult Activity",
          active: false
        },
        {
          name: "Diagnostic",
          active: false
        },
        {
          name: "Structural Change",
          active: false
        }
      ];

      // Initial values for grade level slider
      $scope.gradeSlider = [$scope.minGrade, $scope.maxGrade];

      $scope.slider = {
        options: {
          range: true,
          stop: function(event, ui) {
            $scope.minGrade = $scope.gradeSlider[0];
            $scope.maxGrade = $scope.gradeSlider[1];
          }
        }
      };

      // Used to associate grade level integers with names
      $scope.gradeLevels = [
        "Kindergarten",
        "1st",
        "2nd",
        "3rd",
        "4th",
        "5th",
        "6th",
        "7th",
        "8th",
        "9th",
        "10th",
        "11th",
        "12th",
        "Postsecondary"
      ];

      $scope.schoolSubjects = [
        {
          name: "Math",
          active: false
        },
        {
          name: "English / Lit.",
          active: false
        },
        {
          name: "Science",
          active: false
        },
        {
          name: "Social Studies",
          active: false
        },
        {
          name: "Other",
          active: false
        }
      ];

      $scope.yearTimes = ["Anytime", "Beginning", "Middle", "End"];
      $scope.classPeriods = ["Anytime", "Beginning", "End"];

      $scope.yearTime = "Anytime";
      $scope.classPeriod = "Anytime";

      $scope.classDrop = false;
      $scope.yearDrop = false;

      $scope.tinymceOptions = {
        plugins: "link image code media lists",
        toolbar:
          "formatselect | undo redo | bold italic | alignleft aligncenter alignright | numlist bullist | code | media",
        relative_urls: false,
        remove_script_host: false,
        convert_urls: true,
        init_instance_callback: function(editor) {
          if (editor.id === "ui-tinymce-1") {
            editor.on("focus", function(e) {
              $scope.handleFocus("pageBody");
            });
            editor.on("blur", function(e) {
              $scope.handleBlur("pageBody", !editor.isNotDirty);
            });
            editor.on("Change", function(e) {
              $scope.handleChange("pageBody");
            });
          }
        },
        images_upload_handler: function(blobInfo, success, failure) {
          const file = new File([blobInfo.blob()], blobInfo.filename());
          return Api.pages
            .uploadFile(undefined, file)
            .then(response => {
              const { files } = response.data.json_properties;
              const newFile = files[files.length - 1];
              success(newFile.link);
            })
            .catch(error => failure(error));
        },
        setup: function(editor) {
          overridePaste(editor);
        }
      };

      /*
       * This fixes the bug where TinyMCE paste events don't trigger onChange/validation.
       * TODO: extend this to handle more than plain text.
       * See https://stackoverflow.com/a/27323689 for more info.
       */

      const overridePaste = editor => {
        editor.on("paste", function(e) {
          // Prevent default paste behavior
          e.preventDefault();
          // Check for clipboard data in various places for cross-browser compatibility.
          var content = (
            (e.originalEvent || e).clipboardData || window.clipboardData
          ).getData("Text");
          editor.execCommand("mceInsertContent", false, content);
        });
      };
    };

    // Determines if a valid Youtube link has been shared and
    // extracts ID for page upload
    $scope.getYoutubeId = function() {
      var reg = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
      var match = $scope.youtubeSource.match(reg);

      if (match && match[2].length === 11) {
        $scope.youtubeValid = true;
        $scope.youtubeInvalid = false;
        $scope.youtubeId = match[2];
      } else if ($scope.youtubeSource.length > 0) {
        $scope.youtubeValid = false;
        $scope.youtubeInvalid = true;
        $scope.youtubeId = "";
      } else {
        $scope.youtubeValid = false;
        $scope.youtubeInvalid = false;
        $scope.youtubeId = "";
      }
    };

    // Determines if a valid iFrame src has been shared and
    // extracts src for page upload
    $scope.getIframeSrc = function() {
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
        $scope.iframeSource = "";
      } else {
        $scope.iframeSrcValid = false;
        $scope.iframeSrcInvalid = false;
        $scope.iframeSource = "";
      }
    };

    // Removes any videos, Youtube by default
    $scope.removeVideo = function() {
      $scope.youtubeSource = "";
      $scope.getYoutubeId();
    };

    // Removes any iFrame sources
    $scope.removeIframe = function() {
      $scope.iframeSource = "";
      $scope.embedCode = "";
      $scope.getIframeSrc();
    };

    $scope.setEditPage = function(page) {
      $scope.setValues("scope", false, $scope.additionalInfoMap, page);

      $scope.pageType = page.type;

      $scope.yearTime = page.time_of_year;
      $scope.classPeriod = page.class_period;

      if (page.youtube_id) {
        $scope.youtubeSource = "https://youtu.be/" + page.youtube_id;
        $scope.getYoutubeId();
      }

      if (page.iframe_src) {
        $scope.embedCode = '<iframe src="' + page.iframe_src + '"></iframe>';
        $scope.getIframeSrc();
      }

      if (page.has_files) {
        $scope.oldFiles = page.json_properties.files;
      }

      if (page.max_grade) {
        $scope.gradeSlider = [page.min_grade, page.max_grade];
      }

      $q.all(
        page.related_pages.map(relatedPage =>
          Api.pages.findById(relatedPage).then(response => response.data)
        )
      ).then(results => {
        $scope.relatedPages = results;
      });

      setTagsFromArray($scope.tags, page.tags);

      $scope.editPage = true;
      $scope.editingPage = page;
      $scope.checkValidation();
    };

    // ************************************
    // Code to run on init...
    // ************************************

    $scope.resetVariables();

    // Regular expression to recognize edit URL
    var editReg = /^.*(\/pages\/edit\/)(.{8}).*/;
    var editing = false;

    // Check for url with /edit/<page_id>
    // and pull <page_id> to update form
    if (
      $window.location.href.match(editReg) &&
      $window.location.href.match(editReg)[2]
    ) {
      $scope.pageId = $window.location.href.match(editReg)[2];
      editing = true;
    }

    $scope.init = function(page = "", chapterId = null, bookId = null) {
      if (page !== "") {
        $scope.setEditPage(page);
      }

      if (chapterId && bookId) {
        $scope.chapterId = chapterId;
        $scope.bookId = bookId;
      }
      console.log("Chapter ID", $scope.chapterId);
      console.log("Book ID", $scope.bookId);
    };

    mixpanel.track("Start Upload", {
      Editing: editing
    });

    // Setup quill editor
    // TODO

    // var editor = new Quill('#editor', {
    //   theme: 'snow'
    // });
    // editor.addModule('toolbar', { container: '#toolbar' });

    // Dropdown tag methods

    $scope.setPageIconPath = function() {
      $scope.models.pageIconPath.value = URL.createObjectURL($scope.pageIcon);
    };

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
      $scope.resourceType = "files";

      if ($scope.freshFiles && $scope.freshFiles.length > 0) {
        forEach($scope.freshFiles, function(file) {
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
          if (confirm("Are you sure you want to delete this file?")) {
            Api.pages.removeFile($scope.pageId, file).then(
              function(response) {
                $scope.oldFiles.remove(file);
              },
              function(error) {
                // ERROR!
              }
            );
          }
        }
      }
    };

    // Check step is validated and user can continue to next step
    $scope.checkValidation = function(onlyCheckTouched = false) {
      console.log("checkValidation", $scope);
      const fieldsWithValidation = ["pageName", "pageSummary", "pageBody"];
      fieldsWithValidation.forEach(fieldName => {
        $scope.models[fieldName].displayError = false;
        $scope.models[fieldName].errorMessage = "";
      });

      $scope.error = "";
      $scope.validated = true;
      let validated = true;

      if ($scope.step === 1) {
        if (!(onlyCheckTouched && !$scope.models.pageName.dirty)) {
          if ($scope.models.pageName.value.length < 5) {
            $scope.validated = false;
            $scope.error = "Page name is too short";
            $scope.models.pageName.displayError = true;
            $scope.models.pageName.errorMessage =
              "Page title must be at least 5 characters";
            validated = false;
          }
        }
        if (!(onlyCheckTouched && !$scope.models.pageSummary.dirty)) {
          if ($scope.models.pageSummary.value.length < 10) {
            $scope.validated = false;
            $scope.error = "Page summary is too short";
            $scope.models.pageSummary.displayError = true;
            $scope.models.pageSummary.errorMessage =
              "Page summary must be at least 10 characters";
            validated = false;
          } else if ($scope.models.pageSummary.value.length > 250) {
            $scope.validated = false;
            $scope.error = "Page summary is too long";
            $scope.models.pageSummary.displayError = true;
            $scope.models.pageSummary.errorMessage =
              "Page summary cannot be more than 250 characters";
            validated = false;
          }
        }
        console.log(
          onlyCheckTouched,
          $scope.models.pageBody,
          $scope.models.pageBody.value.length
        );
        if (!(onlyCheckTouched && !$scope.models.pageBody.dirty)) {
          if ($scope.models.pageBody.value.length < 17) {
            $scope.error = "Page text is too short";
            $scope.validated = false;
            $scope.models.pageBody.displayError = true;
            $scope.models.pageBody.errorMessage =
              "Page body must be at least 10 characters";
            validated = false;
          }
        }
        if (validated) {
          $scope.validated = true;
        }
        console.log($scope.models);
      }

      if (!User.currentUser()) {
        $scope.validated = false;
      }

      return $scope.validated;
    };

    // Moves user to the next step of the upload process
    $scope.nextStep = function() {
      if ($scope.checkValidation()) {
        if ($scope.editPage) {
          const data = $scope.setValues(
            "data",
            false,
            $scope.additionalInfoMap
          );
          data.tags = putTagsInArray($scope.tags);

          Api.pages.update($scope.editingPage, data).then(function(response) {
            $scope.page = response.data;

            // Check for any files and upload
            if ($scope.files && $scope.files.length > 0) {
              $scope
                .uploadFieldImages()
                .then(() => uploadFile($scope.files, 0))
                .then(() => ($scope.files = []))
                .catch(error => {
                  $scope.error = "Error uploading file, try another.";
                  $scope.creating = false;
                });
            } else {
              $scope.uploadFieldImages();
            }
          });
        }

        $scope.step += 1;
        scrollToTop();

        mixpanel.track("Upload Tagging");
      }
    };

    // Moves user to the previous step of the upload process
    $scope.previousStep = function() {
      $scope.step += -1;
      $scope.checkValidation();
    };

    $scope.addResourceType = function(type) {
      $scope.resourceType = type;
      $scope.error = "";
    };

    $scope.createPage = function() {
      // Function to finish process and upload the page
      // Formats data entries for POST request

      if ($scope.checkValidation() && !$scope.creating) {
        // Indicate upload and disable button
        $scope.creating = true;

        mixpanel.track("Finish Upload", {
          Type: $scope.pageType,
          Editing: $scope.editPage
        });

        const data = $scope.setValues("data", false, $scope.additionalInfoMap);
        data.tags = putTagsInArray($scope.tags);

        if (!$scope.editPage && !$scope.created) {
          Api.pages.create(data).then(function(response) {
            $scope.page = response.data;
            $scope.created = true;
            $scope.editingPage = response.data;

            $scope.finishedCallback();
          });
        } else {
          Api.pages.update($scope.editingPage, data).then(function(response) {
            $scope.page = response.data;

            $scope.finishedCallback();
          });
        }
      }
    };

    $scope.uploadFieldImages = function() {
      // Check for any files and upload
      const filesDict = {
        icon: $scope.pageIcon
      };
      if (!$scope.pageIcon) {
        delete filesDict.icon;
      }
      return uploadFileFromDict(filesDict, 0).then(
        function(response) {
          console.log("Successfully uploaded page icon");
        },
        function(error) {
          $scope.error = "Error uploading page icon, try another.";
          $scope.creating = false;
        }
      );
    };

    $scope.finishedCallback = function() {
      const promises = [];

      if ($scope.chapterId && $scope.bookId) {
        promises.push(Api.content.associate($scope.chapterId, $scope.page.uid));
      }

      // Check for any files and upload
      if ($scope.files && $scope.files.length > 0) {
        promises.push(
          $scope
            .uploadFieldImages()
            .then(() => uploadFile($scope.files, 0))
            .then(() => ($scope.files = []))
            .catch(error => {
              $scope.error = "Error uploading file, try another.";
              $scope.creating = false;
            })
        );
      } else {
        promises.push($scope.uploadFieldImages());
      }

      $q.all(promises).then(() => {
        if ($scope.bookId) {
          $window.location.href = `/books/manage/${$scope.bookId.replace(
            /^Book_/,
            ""
          )}?expand=${$scope.chapterId.replace(/^Chapter_/, "")}`;
        } else {
          $scope.showFinished();
        }
      });
    };

    $scope.showFinished = function() {
      $scope.step = 4;
      $scope.pageUrl = "/pages/" + $scope.page.short_uid;
      $scope.shareUrl =
        "https://" + hostingDomain + "/pages/" + $scope.page.short_uid;
      $scope.$apply();
      scrollToTop();
    };

    // Reload page (currently just a page refresh)
    $scope.resetPage = function() {
      $window.location.href = "/pages/upload";
    };

    // Reload page (currently just a page refresh)
    $scope.viewPage = function() {
      $window.location.href = $scope.pageUrl;
    };

    // Helper functions....

    // Function to loop through files and upload one at time
    // Async uploading causes errors in json_properties on page
    var uploadFile = function(files, index) {
      var def = $q.defer();
      var file = files[index];
      if (file) {
        Api.pages.uploadFile($scope.page, file).then(
          function(response) {
            $scope.oldFiles = response.data.json_properties.files;
            def.resolve(uploadFile(files, index + 1));
          },
          function(error) {
            // Error occurred, break with rejection
            def.reject(error);
          }
        );
      } else {
        // No more files, resolve!
        def.resolve();
      }
      return def.promise;
    };

    // Function to loop through files dict and upload one at time
    // Async uploading causes errors in json_properties on page
    // var uploadFile = function(filesMap, index) {
    var uploadFileFromDict = function(filesDict, index) {
      var def = $q.defer();
      const files = Object.entries(filesDict);
      const file = files[index];
      const fields = { entity_field: file && file[0] };
      if (file) {
        Api.pages.uploadFile($scope.page, file[1], fields).then(
          function(response) {
            uploadFile(files, index + 1).then(function(response) {
              // File added, run again.
              def.resolve(response);
            });
          },
          function(error) {
            // Error occurred, break with rejection
            def.reject(error);
          }
        );
      } else {
        // No more files, resolve!
        def.resolve();
      }
      return def.promise;
    };

    // Formats tag arrays into data for API
    var putTagsInArray = function(tags) {
      var array = [];
      for (var i = 0; i < tags.length; i++) {
        var tag = tags[i];
        if (tag.active === true) {
          array.push(tag.name);
        }
      }
      return JSON.stringify(array);
    };

    // Formats tag arrays into data for API
    var setTagsFromArray = function(tags, array) {
      if (array) {
        for (var i = 0; i < tags.length; i++) {
          var tag = tags[i];
          for (var j = 0; j < array.length; j++) {
            if (tag.name === array[j]) {
              tag.active = true;
            }
          }
        }
      }
      return JSON.stringify(array);
    };

    // function to scroll to top of .full-container div
    var scrollToTop = function() {
      $("main").animate({ scrollTop: 0 });
      $(".upload-container").animate({ scrollTop: 0 });
    };

    $scope.handleFocus = function(fieldName) {
      // We don't want to validate until the field has been touched, so flag it.
      $scope.models[fieldName].touched = true;
      $scope.models[fieldName].isFocused = true;
    };

    $scope.handleBlur = function(fieldName, tinyIsDirty = false) {
      console.log("handleBlur", fieldName, tinyIsDirty);
      // If there isn't already an error displayed, validate on blur...
      // so might as well just always validate on blur.
      // However, we don't want to validate if you click on a field and haven't
      // changed anything.
      $scope.models[fieldName].isFocused = false;
      if ($scope.models[fieldName].dirty === true || tinyIsDirty) {
        $scope.checkValidation(true);
      }
    };

    $scope.handleChange = function(fieldName) {
      // Mark the field as dirty
      $scope.models[fieldName].dirty = true;
      // If there is already an error displayed, we
      // want instant feedback to tell the user they've
      // passed validation.
      if ($scope.models[fieldName].displayError) {
        $scope.checkValidation(true);
      }
    };

    $scope.addRelatedPage = function() {
      if ($scope.newRelatedPage) {
        const regex = /pages\/(.*)\/?|books\/.*\/(.*)\/?/;
        const matched = $scope.newRelatedPage.match(regex);
        $scope.newRelatedPage = "";
        matched.shift();
        let pageId = "";
        matched.forEach(match => {
          if (match) {
            pageId = `Page_${match.replace(/^Page_/, "")}`;
          }
        });
        if (
          pageId &&
          !$scope.models.relatedPages.value.find(a => a === pageId) &&
          $scope.models.relatedPages.value.length <= 10
        ) {
          Api.pages.findById(pageId).then(result => {
            if (result.data.uid === pageId) {
              $scope.models.relatedPages.value.push(pageId);
              $scope.relatedPages.push(result.data);
            }
          });
        }
      }
    };

    $scope.removeRelatedPage = function(pageId) {
      $scope.models.relatedPages.value = $scope.models.relatedPages.value.filter(
        a => a !== pageId
      );
      $scope.relatedPages = $scope.relatedPages.filter(a => a.uid !== pageId);
    };
  }
]);

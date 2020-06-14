// Angular service for working with Mindset Kit API

/* global util */

angular.module('mskApp')
  .service('Api', ['$q', '$http', 'Upload', function Api($q, $http, Upload) {

    'use strict';

    var base = '/api/';
    var self = this;
    var updatable = ['color', 'estimated_duration', 'lesson_count', 'listed', 'name', 'promoted', 'display_order', 'subjects', 'summary', 'tags', 'target_audience', 'type', 'youtube_id', 'wistia_id', 'locale', 'iframe_src'];
    var searchable = ['q', 'kind', 'tags', 'min_grade', 'max_grade', 'subjects', 'page', 'content_type', 'search_icon'];

    // Wrapper for $http with request, returns promise

    this.http = function(req) {

      var def = $q.defer();

      $http(req).success(function(response) {
        def.resolve(response);
      })
      .error(function(response) {
        def.reject(response);
      });

      return def.promise;

    };

    this.getGoogleLoginLink = function (redirect) {
      var parsedRedirect = util.parseUrl(redirect);
      parsedRedirect.search = util.buildQueryString({google_login: 'true'});
      return this.http({
        method: 'GET',
        url: base + 'get_google_login_link',
        params: {redirect: parsedRedirect.href}
      });
    };

    this.resetPasswordWithToken = function (token, newPassword) {
      // Possible responses are:
      // * 'changed'
      // * 'invalid_token'
      // * 'bad_password'
      return this.http({
        url: base + 'reset_password',
        method: 'POST',
        data: {token: token, new_password: newPassword}
      });

    };

    this.sendPasswordReset = function (email) {

      var req = {
        method: 'GET',
        url: base + 'forgot_password',
        params: {'email': email}
      };
      return self.http(req);

    };

    this.sendReflectionEmail = function (params) {

      var req = {
        url: base + 'send_reflection_email',
        method: 'POST',
        data: params
      };
      return self.http(req);

    };

    // Auth API requests

    this.auth = {};

    this.auth.login = function(data) {

      var req = {
        url: base + 'login',
        method: 'POST',
        data: data
      };
      return self.http(req);

    };

    this.auth.register = function(data) {

      var req = {
        url: base + 'register',
        method: 'POST',
        data: data
      };
      return self.http(req);

    };

    // User API requests

    this.users = {};

    this.users.search = function (params) {


      var searchParams = {};

      for (var param in params) {
        if (searchable.indexOf(param) > -1) {
          searchParams[param] = params[param];
        }
      }

      console.log('search with params', searchParams);
      var req = {
        method: 'GET',
        url: base + 'search/users',
        params: searchParams
      };
      return self.http(req);

    };

    this.users.get = function(params) {

      var req = {
        method: 'GET',
        url: base + 'users',
        params: params,
      };
      return self.http(req);

    };

    this.users.findById = function(id) {

      var req = {
        method: 'GET',
        url: base + 'users/' + id
      };
      return self.http(req);

    };

    this.users.update = function(user, params) {

      var req = {
        method: 'PUT',
        url: base + 'users/' + user.uid,
        data: params
      };
      return self.http(req);

    };

    this.users.fetchPractices = function(user, page) {

      var req = {
        method: 'GET',
        url: base + 'users/' + user.uid + '/practices',
        params: {'page': page}
      };
      return self.http(req);

    };

    this.users.fetchPages = function(user, page) {

      var req = {
        method: 'GET',
        url: base + 'users/' + user.uid + '/pages',
        params: {'page': page}
      };
      return self.http(req);

    };

    this.users.fetchResources = function(user, page) {

      var req = {
        method: 'GET',
        url: base + 'users/' + user.uid + '/resources',
        params: {'page': page}
      };
      return self.http(req);

    };

    this.users.fetchBooks = function(user, page = 0) {

      var req = {
        method: 'GET',
        url: base + 'users/' + user.uid + '/books',
        params: {'page': page}
      };
      return self.http(req);

    };

    this.users.fetchAuthored = function(user, page = 0) {

      var req = {
        method: 'GET',
        url: base + 'users/' + user.uid + '/get_authored',
        params: {'page': page}
      };
      return self.http(req);

    };

    this.users.fetchVotes = function(user, page) {

      var req = {
        method: 'GET',
        url: base + 'users/' + user.uid + '/votes',
        params: {'page': page}
      };
      return self.http(req);

    };

    this.users.uploadImage = function(imageFile) {

      var def = $q.defer();

      // Get upload url from the server
      self.users.getUploadImageUrl().then( function (response) {
        if (!response.error) {
          var uploadUrl = response.data;

          Upload.upload({
              url: uploadUrl,
              headers: {'Content-Type': imageFile.type},
              file: imageFile
            }).progress( function (evt) {
              var progressPercentage = parseInt(100.0 * evt.loaded / evt.total,
                                                10);
              console.log('progress: ' + progressPercentage + '% ' + evt.config.file.name);
            }).success( function (data, status, headers, config) {
              console.log('upload success', data, status, headers, config);
              def.resolve(data);
            }).error( function (error) {
              def.reject(error);
            });

        } else {
          def.reject('An error occurred');
        }

      });

      return def.promise;

    };

    this.users.getUploadImageUrl = function() {

      var req = {
        method: 'GET',
        url: base + 'users/upload_image_url'
      };
      return self.http(req);

    };

    this.getUploadUrl = function(modelType) {
      modelType = modelType.toLowerCase();
      const whitelist = ['practice', 'page', 'book'];
      if (!whitelist.contains(modelType)) {
        throw 'Invalid modelType provided to getUploadUrl';
      }
      modelType += 's';
      var req = {
        method: 'GET',
        url: base + modelType + '/upload_url'
      };
      return self.http(req);

    };

    // Pages API requests

    this.pages = {};

    this.pages.find = function(params) {

      var req = {
        method: 'GET',
        url: base + 'pages',
        params: params
      };
      return self.http(req);

    };

    this.pages.findById = function(id) {

      var req = {
        method: 'GET',
        url: base + 'pages/' + id
      };
      return self.http(req);

    };

    this.pages.fetchPopular = function() {

      var req = {
        method: 'GET',
        url: base + 'pages/popular'
      };
      return self.http(req);

    };

    this.pages.create = function(params) {
      delete params.iconPath;

      var req = {
        method: 'POST',
        url: base + 'pages',
        data: params
      };
      return self.http(req);

    };

    this.pages.update = function(page, params) {

      var req = {
        method: 'PUT',
        url: base + 'pages/' + page.uid,
        data: params
      };
      return self.http(req);

    };

    this.pages.delete = function(page) {

      var req = {
        method: 'DELETE',
        url: base + 'pages/' + page.uid
      };
      return self.http(req);

    };

        // A file object has properties:
    //   lastModified: js timestamp
    //   lastModifiedDate: Date object
    //   name: string, e.g. "IMG_2237.JPG"
    //   size: int
    //   type: mime type string, e.g. "image/jpeg"
    // TODO: modularize the upload function across entity types, keep DRY
    this.pages.uploadFile = function(page, file, fields) {
      page = page || {};
      fields = fields || {};
      fields.entity_id = page.uid;

      var def = $q.defer();

      // Get upload url from the server
      self.getUploadUrl('page').then( function (response) {
        if (!response.error) {
          var uploadUrl = response.data;
          var headers = {
            'Content-Type': file.type,
            'Content-Disposition': 'attachment; filename=' + file.name + ';'
          };
          console.log("file:", file);
          console.log("headers:", headers);

          Upload.upload({
              url: uploadUrl,
              headers: headers,
              file: file,
              fields: fields
            }).progress( function (evt) {
              var progressPercentage = parseInt(100.0 * evt.loaded / evt.total,
                                                10);
              console.log('progress: ' + progressPercentage + '% ' + evt.config.file.name);
            }).success( function (data, status, headers, config) {
              console.log('upload success', data, status, headers, config);
              def.resolve(data);
            }).error( function (error) {
              def.reject(error);
            });

        } else {
          def.reject('An error occurred');
        }

      });

      return def.promise;

    };

    this.pages.removeFile = function(pageId, file) {
      var req = {
        method: 'GET',
        url: base + 'pages/' + pageId + '/remove_file',
        params: {
          'file': encodeURIComponent(file.gs_object_name)
        }
      };
      return self.http(req);

    };

    this.pages.inviteUsers = function(pageId, users) {
      console.log('inviteUsers', pageId, users);

      var req = {
        method: 'POST',
        url: base + 'pages/' + pageId + '/invite_authors',
        data: {
          'users': users,
        }
      };
      return self.http(req);

    };

    this.pages.removeAuthor = function (pageId, authorId) {
      console.log('books.removeAuthor');

      var req = {
        method: 'POST',
        url: base + 'pages/' + pageId + '/remove_author',
        data: {
          user_id: authorId,
        },
      };
      return self.http(req);
    };

    this.pages.fetchAll = function(page) {
      return self.content.fetchAll('pages', page);
    };

    this.pages.remove = function (pageId) {
      var req = {
        method: 'DELETE',
        url: base + 'pages/' + pageId,
      };
      return self.http(req);
    };

    // Books API requests

    this.books = {};

    this.books.find = function(params) {

      var req = {
        method: 'GET',
        url: base + 'books',
        params: params
      };
      return self.http(req);

    };

    this.books.findById = function(id) {

      var req = {
        method: 'GET',
        url: base + 'books/' + id
      };
      return self.http(req);

    };

    this.books.create = function(params) {

      var req = {
        method: 'POST',
        url: base + 'books',
        data: params
      };
      return self.http(req);

    };

    this.books.update = function(book, params) {

      var req = {
        method: 'PUT',
        url: base + 'books/' + book.uid,
        data: params
      };
      return self.http(req);

    };

    // A file object has properties:
    //   lastModified: js timestamp
    //   lastModifiedDate: Date object
    //   name: string, e.g. "IMG_2237.JPG"
    //   size: int
    //   type: mime type string, e.g. "image/jpeg"
    // TODO: modularize the upload function across entity types, keep DRY
    this.books.uploadFile = function(book, file, fields) {
      book = book || {};
      fields = fields || {};

      if (book.hasOwnProperty('uid')) {
        fields.entity_id = book.uid;
      }

      var def = $q.defer();

      // Get upload url from the server
      self.getUploadUrl('book').then( function (response) {
        if (!response.error) {
          var uploadUrl = response.data;
          var headers = {
            'Content-Type': file.type,
            'Content-Disposition': 'attachment; filename=' + file.name + ';'
          };
          console.log("file:", file);
          console.log("headers:", headers);

          Upload.upload({
              url: uploadUrl,
              headers: headers,
              file: file,
              fields: fields
            }).progress( function (evt) {
              var progressPercentage = parseInt(100.0 * evt.loaded / evt.total,
                                                10);
              console.log('progress: ' + progressPercentage + '% ' + evt.config.file.name);
            }).success( function (data, status, headers, config) {
              console.log('upload success', data, status, headers, config);
              def.resolve(data);
            }).error( function (error) {
              def.reject(error);
            });

        } else {
          def.reject('An error occurred');
        }

      });

      return def.promise;

    };

    this.books.removeFile = function(bookId, file) {

      var req = {
        method: 'GET',
        url: base + 'books/' + bookId + '/remove_file',
        params: {
          'file': encodeURIComponent(file.gs_object_name)
        }
      };
      return self.http(req);

    };

    this.books.removeChild = function(book, child) {
      return self.content.removeChild('books', book, child);
    };

    this.books.reorderChild = function(book, child, moveUp) {
      return self.content.reorderChild('books', book, child, moveUp);
    };

    this.books.addChild = function(book, child) {
      return self.content.addChild('books', book, child);
    };

    this.books.fetchAll = function(page) {
      return self.content.fetchAll('books', page);
    };

    this.books.inviteUsers = function(bookId, users) {
      console.log('inviteUsers', bookId, users);

      var req = {
        method: 'POST',
        url: base + 'books/' + bookId + '/invite_authors',
        data: {
          'users': users
        }
      };
      return self.http(req);

    };

    this.books.removeAuthor = function (bookId, authorId) {
      console.log('books.removeAuthor');

      var req = {
        method: 'POST',
        url: base + 'books/' + bookId + '/remove_author',
        data: {
          user_id: authorId,
        },
      };
      return self.http(req);
    };

    this.books.fetchSortable = function(bookId) {
      var req = {
        method: 'GET',
        url: base + 'books/' + bookId + '/get_sortable'
      };
      return self.http(req);
    };

    this.books.reorderChapters = function(bookId, chapters) {

      var req = {
        method: 'PUT',
        url: base + 'books/' + bookId + '/reorder_chapters',
        data: {
          chapters,
        },
      };
      return self.http(req);

    };

    this.books.remove = function (bookId) {
      var req = {
        method: 'DELETE',
        url: base + 'books/' + bookId,
      };
      return self.http(req);
    };

    // Chapter API requests

    this.chapters = {};

    this.chapters.create = function(params) {
      var req = {
        method: 'POST',
        url: base + 'chapters',
        data: params
      };
      return self.http(req);

    };

    this.chapters.update = function(chapterId, params) {

      var req = {
        method: 'PUT',
        url: base + 'chapters/' + chapterId,
        data: params
      };
      return self.http(req);

    };

    this.chapters.reorderPages = function(chapterId, pages) {

      var req = {
        method: 'PUT',
        url: base + 'chapters/' + chapterId + '/reorder_pages',
        data: {
          pages,
        },
      };
      return self.http(req);

    };

    this.chapters.fetchAll = function(page) {
      return self.content.fetchAll('chapters', page);
    };

    this.chapters.remove = function (chapterId) {
      var req = {
        method: 'DELETE',
        url: base + 'chapters/' + chapterId,
      };
      return self.http(req);
    };

    // Practice API requests

    this.practices = {};

    this.practices.find = function(params) {

      var req = {
        method: 'GET',
        url: base + 'practices',
        params: params
      };
      return self.http(req);

    };

    this.practices.findById = function(id) {

      var req = {
        method: 'GET',
        url: base + 'practices/' + id
      };
      return self.http(req);

    };

    this.practices.fetchPopular = function() {

      var req = {
        method: 'GET',
        url: base + 'practices/popular'
      };
      return self.http(req);

    };

    this.practices.create = function(params) {

      var req = {
        method: 'POST',
        url: base + 'practices',
        data: params
      };
      return self.http(req);

    };

    this.practices.update = function(practice, params) {

      var req = {
        method: 'PUT',
        url: base + 'practices/' + practice.uid,
        data: params
      };
      return self.http(req);

    };

    this.practices.delete = function(practice) {

      var req = {
        method: 'DELETE',
        url: base + 'practices/' + practice.uid
      };
      return self.http(req);

    };

    // A file object has properties:
    //   lastModified: js timestamp
    //   lastModifiedDate: Date object
    //   name: string, e.g. "IMG_2237.JPG"
    //   size: int
    //   type: mime type string, e.g. "image/jpeg"
    this.practices.uploadFile = function(practice, file, fields) {
      fields = fields || {};
      fields.entity_id = practice.uid;

      var def = $q.defer();

      // Get upload url from the server
      self.getUploadUrl('practice').then( function (response) {
        if (!response.error) {
          var uploadUrl = response.data;
          var headers = {
            'Content-Type': file.type,
            'Content-Disposition': 'attachment; filename=' + file.name + ';'
          };
          console.log("file:", file);
          console.log("headers:", headers);

          Upload.upload({
              url: uploadUrl,
              headers: headers,
              file: file,
              fields: fields
            }).progress( function (evt) {
              var progressPercentage = parseInt(100.0 * evt.loaded / evt.total,
                                                10);
              console.log('progress: ' + progressPercentage + '% ' + evt.config.file.name);
            }).success( function (data, status, headers, config) {
              console.log('upload success', data, status, headers, config);
              def.resolve(data);
            }).error( function (error) {
              def.reject(error);
            });

        } else {
          def.reject('An error occurred');
        }

      });

      return def.promise;

    };

    this.practices.removeFile = function(practiceId, file) {

      var req = {
        method: 'GET',
        url: base + 'practices/' + practiceId + '/remove_file',
        params: {
          'file': encodeURIComponent(file.gs_object_name)
        }
      };
      return self.http(req);

    };

    this.practices.associateContent = function(practice, content) {

      var params = {
        associated_content: content.uid
      };
      return self.practices.update(practice, params);

    };

    // Content model API requests

    this.content = {};

    this.content.search = function (params) {

      var searchParams = {};

      for (var param in params) {
        if (searchable.indexOf(param) > -1) {
          searchParams[param] = params[param];
        }
      }

      var req = {
        method: 'GET',
        url: base + 'search',
        params: searchParams
      };
      return self.http(req);

    };

    this.content.fetchAll = function(model, page) {

      var req = {
        method: 'GET',
        url: base + model,
        params: {'page': page}
      };
      return self.http(req);

    };

    this.content.create = function(model, params) {

      var req = {
        method: 'POST',
        url: base + model,
        data: params
      };
      return self.http(req);

    };

    this.content.update = function(model, content, params) {

      var updateFields = {};

      for (var param in params) {
        if (updatable.indexOf(param) > -1) {
          updateFields[param] = params[param];
        }
      }

      var req = {
        method: 'PUT',
        url: base + model + '/' + content.uid,
        data: updateFields
      };
      return self.http(req);

    };

    this.content.delete = function(model, content) {

      var req = {
        method: 'DELETE',
        url: base + model + '/' + content.uid
      };
      return self.http(req);

    };

    this.content.removeChild = function(model, parent, child) {

      var req = {
        method: 'GET',
        url: base + model + '/' + parent.uid + '/remove-child/' + child.uid
      };
      return self.http(req);

    };

    this.content.deleteChild = function(parentId, childId) {

      var req = {
        method: 'POST',
        url: base + 'content/delete-child',
        data: {
          'parent_id': parentId,
          'child_id': childId,
        }
      };
      return self.http(req);

    };

    this.content.reorderChild = function(model, parent, child, moveUp) {

      var req = {
        method: 'GET',
        url: base + model + '/' + parent.uid + '/reorder-child/' + child.uid,
        params: {'move_up': moveUp}
      };
      return self.http(req);

    };

    this.content.addChild = function(model, parent, child) {

      var req = {
        method: 'GET',
        url: base + model + '/' + parent.uid + '/add-child/' + child.uid
      };
      return self.http(req);

    };

    this.content.associate = function(parentId, childId, options) {
      options = options || {};
      var index = options.index;
      var moveOrCopy = options.moveOrCopy || 'copy';

      var req = {
        method: 'PUT',
        url: base + 'content/associate',
        data: {
          'parent_id': parentId,
          'child_id': childId,
          'index': index,
          'move_or_copy': moveOrCopy,
        }
      };
      return self.http(req);
    };

    // Theme API requests

    this.themes = {};

    this.themes.fetchAll = function(page) {
      return self.content.fetchAll('themes', page);
    };

    this.themes.create = function(params) {
      return self.content.create('themes', params);
    };

    this.themes.update = function(theme, params) {
      return self.content.update('themes', theme, params);
    };

    this.themes.delete = function(theme) {
      return self.content.delete('themes', theme);
    };

    this.themes.fetchChildren = function(theme) {
      var req = {
        method: 'GET',
        url: base + 'themes/' + theme.uid + '/topics'
      };
      return self.http(req);
    };

    this.themes.fetchLessons = function(theme) {
      var req = {
        method: 'GET',
        url: base + 'themes/' + theme.uid + '/lessons'
      };
      return self.http(req);
    };

    this.themes.removeChild = function(theme, child) {
      return self.content.removeChild('themes', theme, child);
    };

    this.themes.reorderChild = function(theme, child, moveUp) {
      return self.content.reorderChild('themes', theme, child, moveUp);
    };

    this.themes.addChild = function(theme, child) {
      return self.content.addChild('themes', theme, child);
    };

    // Topic API requests

    this.topics = {};

    this.topics.fetchAll = function(page) {
      return self.content.fetchAll('topics', page);
    };

    this.topics.create = function(params) {
      return self.content.create('topics', params);
    };

    this.topics.update = function(topic, params) {
      return self.content.update('topics', topic, params);
    };

    this.topics.delete = function(topic) {
      return self.content.delete('topics', topic);
    };

    this.topics.fetchChildren = function(topic) {

      var req = {
        method: 'GET',
        url: base + 'topics/' + topic.uid + '/lessons'
      };
      return self.http(req);

    };

    this.topics.removeChild = function(topic, lesson) {
      return self.content.removeChild('topics', topic, lesson);
    };

    this.topics.reorderChild = function(topic, lesson, moveUp) {
      return self.content.reorderChild('topics', topic, lesson, moveUp);
    };

    this.topics.addChild = function(topic, lesson) {
      return self.content.addChild('topics', topic, lesson);
    };

    // Lesson API requests

    this.lessons = {};

    this.lessons.fetchAll = function(page) {
      return self.content.fetchAll('lessons', page);
    };

    this.lessons.create = function(params) {
      return self.content.create('lessons', params);
    };

    this.lessons.update = function(lesson, params) {
      return self.content.update('lessons', lesson, params);
    };

    this.lessons.delete = function(lesson) {
      return self.content.delete('lessons', lesson);
    };

    // Returns themes with lesson (with specific paths)
    this.lessons.getThemes = function(lesson) {
      var req = {
        method: 'GET',
        url: base + 'lessons/' + lesson.uid + '/themes'
      };
      return self.http(req);
    };

    // Comment API requests

    this.comments = {};

    this.comments.fetch = function(params) {

      var req = {
        method: 'GET',
        url: base + 'comments',
        params: params
      };
      return self.http(req);

    };

    this.comments.create = function(params) {

      var req = {
        method: 'POST',
        url: base + 'comments',
        data: params
      };
      return self.http(req);

    };

    this.comments.delete = function(commentId) {

      var req = {
        method: 'DELETE',
        url: base + 'comments/' + commentId
      };
      return self.http(req);

    };

    // Vote API requests

    this.votes = {};

    this.votes.fetch = function(subject, type) {

      var req = {
        method: 'GET',
        url: base + 'votes'
      };
      //TODO: DRY
      const whitelist = ['lesson', 'practice', 'book', 'page'];
      if (whitelist.includes(type)) {
        const idPropertyName = `${type}_id`;
        req.params = { [idPropertyName]: subject };
      }
      return self.http(req);

    };

    this.votes.create = function(subject, type) {

      var req = {
        method: 'POST',
        url: base + 'votes'
      };
      //TODO: DRY
      const whitelist = ['lesson', 'practice', 'book', 'page'];
      if (whitelist.includes(type)) {
        const idPropertyName = `${type}_id`;
        req.data = { [idPropertyName]: subject };
      }
      return self.http(req);

    };

    this.votes.delete = function(voteId) {

      var req = {
        method: 'DELETE',
        url: base + 'votes/' + voteId
      };
      return self.http(req);

    };

    // Feedback API requests

    this.feedback = {};

    this.feedback.fetch = function(params) {

      var req = {
        method: 'GET',
        url: base + 'feedback',
        params: params
      };
      return self.http(req);

    };

    this.feedback.create = function(params) {

      var req = {
        method: 'POST',
        url: base + 'feedback',
        data: params
      };
      return self.http(req);

    };

    // Email API requests

    this.email = {};

    this.email.create = function(params) {

      var req = {
        method: 'POST',
        url: base + 'email',
        data: params
      };
      return self.http(req);

    };

  }]);
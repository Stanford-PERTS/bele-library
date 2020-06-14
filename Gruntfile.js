/*jshint globalstrict: true*/

'use strict';

// const terser = require('terser');

// const terserOptions = {
//   compress: {
//     passes: 3,
//   },
//   ecma: 8,
//   output: {
//     beautify: false,
//   },
//   toplevel: true,
// };

module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),

    // SETUP USEMINE PREP TO AUTO CREATE CONCAT AND UGLIFY SCRIPTS

    // Allow the use of non-minsafe AngularJS files. Automatically makes it
    // minsafe compatible so Uglify does not destroy the ng references
    ngAnnotate: {
      dist: {
        files: [{
          expand: true,
          cwd: '.tmp/concat',
          src: '*/*/**.js',
          dest: '.tmp/concat'
        }]
      }
    },

    // Checks javascript files for formatting issues
    jshint: {
      files: [
        'Gruntfile.js',
        'static/javascripts/*.js',
        '!static/javascripts/*.min.js',
        '!static/javascripts/redactor.js',
        '!static/javascripts/jquery.tinymce.js',
        '!static/javascripts/tinymce.js',
        'static/javascripts/controllers/*.js',
        'static/javascripts/directives/*.js',
        'static/javascripts/services/*.js'
        ],
      options: {
        reporter: require('jshint-stylish'),
        curly: true,
        eqeqeq: true,
        eqnull: true,
        browser: true,
        strict: true,
        undef: true,
        loopfunc: true,
        esversion: 6,

        globals: {
          $: true,
          FB: true,
          jQuery: true,
          angular: true,
          require: true,
          console: true,
          module: true,
          util: true,
          forEach: true,
          confirm: true,
          mixpanel: true,
          CryptoJS: true,
          document: true,
        }
      }
    },

    // Empties folders to start fresh
    clean: {
      dist: {
        files: [{
          dot: true,
          src: [
            '.tmp',
            'static/templates/dist/*',
            'static/javascripts/*.vendor.min.js',
            'static/javascripts/*.mindsetkit.min.js',
            'static/stylesheets/*.mindsetkit.css'
          ]
        }]
      }
    },

    copy: {
      dist: {
        files: [
          { expand: true, dot: true, cwd: 'templates', dest: 'templates/dist', src: ['head.html'] },
          { expand: true, flatten: true, src: ['bower_components/components-font-awesome/fonts/*'], dest: 'static/fonts'},
          { expand: true, cwd: 'bower_components/tinymce', src: ['**'], dest: 'static/javascripts'},
        ],
      },
    },

    wiredep: {
      task: {
        // Point to the files that should be updated when
        // you run `grunt wiredep`
        src: [
          'templates/head.html'
        ],
        ignorePath: '..',
        exclude: ['/json3/', '/es5-shim/']
      }
    },

    // Reads HTML for usemin blocks to enable smart builds that automatically
    // concat, minify and revision files. Creates configurations in memory so
    // additional tasks can operate on them
    useminPrepare: {
      html: 'templates/head.html',
      options: {
        root: '.',
        dest: '.'
        // assetsDirs: ['static']
      }
    },

    // Renames files for browser caching purposes
    rev: {
      dist: {
        files: {
          src: [
            'static/javascripts/mindsetkit.min.js',
            'static/javascripts/vendor.min.js',
            'static/stylesheets/mindsetkit.css'
          ]
        }
      }
    },

    // Performs rewrites based on rev and the useminPrepare configuration
    // TODO: https://github.com/yeoman/grunt-usemin UGH EVERYTHING IS DEPRECATED/OUTDATED
    usemin: {
      html: 'templates/dist/*.html',
      options: {
        assetsDirs: ['.']
      }
    },

    // Handles scss -> css file conversions
    compass: {
      dist: {                   // Target
        options: {              // Target options
          sassDir: 'sass',
          cssDir: 'static/stylesheets',
          environment: 'production',
          force: true
        }
      },
      watch: {
        options: {
          sassDir: 'sass',
          cssDir: 'static/stylesheets',
          watch: true
        }
      }
    },

    // Run tasks locally while building
    watch: {
      files: ['<%= jshint.files %>'],
      tasks: ['jshint'],
      options: {
        livereload: true
      }
    },

    // Used to run compass:watch and watch concurrently
    concurrent: {
      watch: {
        tasks: ['watch', 'compass:watch'],
        options: {
          logConcurrentOutput: true
        }
      }
    }
  });

  grunt.loadNpmTasks('grunt-contrib-uglify-es');
  grunt.loadNpmTasks('grunt-contrib-jshint');
  grunt.loadNpmTasks('grunt-contrib-cssmin');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-contrib-compass');
  grunt.loadNpmTasks('grunt-contrib-clean');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-concurrent');
  grunt.loadNpmTasks('grunt-usemin');
  grunt.loadNpmTasks('grunt-ng-annotate');
  grunt.loadNpmTasks('grunt-wiredep');
  grunt.loadNpmTasks('grunt-rev');

  // Serve task (run during local development)
  grunt.registerTask('serve', [
    'wiredep',
    'concurrent:watch'
  ]);

  // Runs the serve task by default
  grunt.registerTask('default', function () {
    grunt.task.run('serve');
  });

  // Build task
  grunt.registerTask('build', [
    'clean:dist', // removes .tmp files and generated head file
    'jshint', // runs jshint, to force correct javascript syntax
    'wiredep', // injects bower modules in head.html
    'copy:dist', // generates a copy of head.html in /templates/dist
    'compass:dist', // generates production versions of css files
    'useminPrepare', // generates concat, cssmin, and uglify tasks
    'concat:generated', // concats js files based on useminPerpare
    'cssmin:generated', // concats / minifies js files based on useminPerpare
    'ngAnnotate:dist', // makes the angular files min-safe
    'uglify:generated', // uglifies js files based on useminPrepare
    'rev', // revisions static assets through a file content hash
    'usemin' // replaces js and css references in /templates/dist/head.html
  ]);

  grunt.option( 'force', true );

};

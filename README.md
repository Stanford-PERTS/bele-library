bele-library
==========

Currently a duplicate of the PERTS Mindset Kit. Destined to be the BELE Library, a web app for the creation and curation of educational resources managed by the BELE Network.

## Starting the app locally

### Dependencies

* Python 2.7.15 (not the native MacOS installation). Recommend homebrew (`brew install python@2`) and `pyenv`.
* The [Google Cloud SDK](https://cloud.google.com/sdk/) a.k.a. `gcloud`.
* Java, required by the datastore emulator.
* NodeJS and npm

### Commands

After first cloning, or after changing node dependencies:

```
$ npm install
```

Then you need two processes running to launch the MSK locally; a process that watches for changes to SASS files and compiles them to CSS, and another that runs a webserver. Open two tabs in a Terminal window, and run each of these commands in their own tab.

```
$ npm start
```

and, in the other tab

```
$ npm run server
```

Then open this URL in your browser: `localhost:3001`

## Production builds

**The follow is not set up, but @chris-perts is taking responsibility for:**

Codeship (a continuous integration service) watches the bele-library repository on github and builds, tests, and deploys code to bele-library.appspot.com. Simply committing and syncing to the `master` branch will trigger one of these builds, and your changes will appear on bele-library.appspot.com a few minutes later.

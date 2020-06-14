/* IMPORTANT: run this file through https://www.minifier.org/ to get rid of whitespace and comments */

// DEV
// const VENDOR_ROLE = '5ae000bad741b700049e5af1';
// const ADMIN_ROLE = '5ae000bad741b700049e5ae9';
// const COORDINATOR_ROLE = '5ae000bad741b700049e5aff';
// const USER_ROLE = '5ae000bad741b700049e5b03';
// const ANALYTICS_TO_EMAIL = '';
// const ANALYTICS_FROM_EMAIL = '';

// STAGING
// const VENDOR_ROLE = '5ae7c60c88c2620004c3dff6';
// const ADMIN_ROLE = '5ae7c60c88c2620004c3dfec';
// const COORDINATOR_ROLE = '5ae7c60c88c2620004c3e000';
// const USER_ROLE = '5ae7c60c88c2620004c3e00a';
// const ANALYTICS_TO_EMAIL = '';
// const ANALYTICS_FROM_EMAIL = '';
// const UNSUPPORTED_LOCATION_OBJECT_ID = '5b0260ea98b3ad0014e7a87e';
// const APN_TOPIC = 'com.thejcbrand.vowla-stg';

// PROD
const VENDOR_ROLE = '5af8e0c0c72010000426c25c';
const ADMIN_ROLE = '5af8e0c0c72010000426c250';
const COORDINATOR_ROLE = '5af8e0c0c72010000426c266';
const USER_ROLE = '5af8e0c0c72010000426c26e';
const ANALYTICS_TO_EMAIL = '';
const ANALYTICS_FROM_EMAIL = '';
const UNSUPPORTED_LOCATION_OBJECT_ID = '5b0f91241086a90014c8647a';
const APN_TOPIC = 'com.thejcbrand.vowla';

const CONVERSATION_SCHEMA = '5ad7062df7dae80014007c45';
const USER_VENDOR_SCHEMA = '5ace9be3d7038600146f5321';
const NOTIFICATION_SCHEMA = '5ae353335f1ef6001489a130';
const USER_CLIENT_SCHEMA = '5adfa5ec0c02e7001475e410';
const USER_COORDINATOR_SCHEMA = '5ae0ba01066d490014b34dfd';
const UNMATCHED_CLIENTS_SCHEMA = '5ae8da415d11b90014f19be6';
const MASTER_TIMELINE_TASKS_SCHEMA = '5add09f8ba2ac300143410b1';
const TIMELINE_TASK_RESPONSE_SCHEMA = '5aed009c6626380014fe7f59';
const MAX_MATCH_DISTANCE_METERS = 96560.6; //60 miles
const MAX_NUM_CLIENTS_PER_SEASON = 12;
const COORDINATOR_CLIENT_MAX_WINDOW = 4; // Max client window length, in weeks
const ENABLE_LOGGING = true;
const TIMELINE_NUDGE_OFFSET_DAYS = 7;
const MATCH_DELAY = 1 * 60 * 1000;
const MAX_DAYS_FROM_WEDDING = 210;
const SEASONS = [
  { name: 'Spring', months: [3, 4, 5], mid: 'April 15' }, 
  { name: 'Summer', months: [6, 7, 8], mid: 'July 16' }, 
  { name: 'Fall', months: [9, 10, 11], mid: 'October 16' }, 
  { name: 'Winter', months: [12, 1, 2], mid: 'January 14' }
];
const MINIMUM_DAYS_TO_WEDDING = 180;
if (!ENABLE_LOGGING) {
  console = {};
  console.log = () => {};
};

// APN provider options
const providerOptions = {
  token: {
    key: '-----BEGIN PRIVATE KEY-----\\nMIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQgYLNzKpcW/5dCi+VZ B41vhG7MAlEVAqrq4Lko5l+4YmWgCgYIKoZIzj0DAQehRANCAAQpXdgv0Rt8LhLo Uxsw502WsjY8R/R9R1oqAsphGUpeeovTYv7dOr/aIcavxmKkUfWDo0L6qIiskJ4j RTAmeG+n\\n-----END PRIVATE KEY-----',
    keyId: 'TTGTYJL7FG',
    teamId: 'JPQTA8NVTY'
  },
  production: true,
};

const devProviderOptions = Object.assign({}, providerOptions);
devProviderOptions.production = false;

/*
 * Sends push notification and creates an associated notification object in the CMS
 */ 
const sendPush = (alert, payload, category, token, userId) => {
  const apnProvider = new modules.apn.Provider(providerOptions);
  const devApnProvider = new modules.apn.Provider(devProviderOptions);
  const topic = APN_TOPIC;
  const notificationData = {
    has_been_read: false,
    alert_title: alert.title,
    alert_body: alert.body,
    notification_category: category,
    user_id: userId,
    conversation_id: payload.conversation_id,
    vendor_id: payload.vendor_id,
    task_id: payload.task_id,
    shopping_item_id: payload.shopping_item_id,
    client_id: payload.client_id,
    coordinator_id: payload.coordinator_id,
    phase: payload.phase,
    coordinator_profile_image: payload.coordinator_profile_image,
    topic,
  };
  console.log('Creating notification object:', notificationData, userId, typeof(userId));
  // Create notification object in CMS for every push
  sdk.objects.create(NOTIFICATION_SCHEMA, notificationData).then(result => {
    if (!token) return false;
    const notification_id = result._id;
    const note = new modules.apn.Notification();
    note.alert = alert;
    note.payload = Object.assign(payload, { notification_id: notification_id });
    note.topic = topic;
    note.category = category;
    console.log('sending note', token);
    devApnProvider.send(note, token).then(result => {
      console.log('push notification sent:');
      console.dir(result);
      console.dir(result && result.failed && result.failed[0] && result.failed[0].response);
    });
    apnProvider.send(note, token).then(result => {
      console.log('push notification sent:');
      console.dir(result);
      console.dir(result && result.failed && result.failed[0] && result.failed[0].response);
    });
  });
};

const getMasterTimelineTasks = () =>
  sdk.objects.list(MASTER_TIMELINE_TASKS_SCHEMA)
    .then(response => response[0]);

/*
 * Returns an adjusted timeline of each phase and its end date
 */
const createTimelinePhaseMap = (createdDate, weddingDate) => {
  const now = new Date;
  const maxDaysFromWeddingMs = MAX_DAYS_FROM_WEDDING * 24 * 60 * 60 * 1000; 
  // Standard: 2/7 months for phases 1-3, 1/7 months for phase 4
  const allowedVariance = TIMELINE_NUDGE_OFFSET_DAYS * 24 * 60 * 60 * 1000; // 3 days in ms
  const phaseDurationRatios = [2, 2, 2, 1];
  const delta = Math.abs(weddingDate-createdDate) >= maxDaysFromWeddingMs ? maxDaysFromWeddingMs : Math.abs(weddingDate-createdDate);
  const sum = phaseDurationRatios.reduce((acc, curr) => acc + curr);
  const startDate = new Date(weddingDate - delta);
  console.log(`created: ${createdDate}, startDate: ${startDate}, weddingDate: ${weddingDate}, delta: ${delta}, sum: ${sum}`);
  const phaseDurations = phaseDurationRatios.map(ratio => delta * ratio/sum);
  console.log('phaseDurations', phaseDurationRatios, weddingDate, startDate, delta, sum, phaseDurations);
  let phaseEndDateMs = startDate.getTime();
  for (let i = 0; i < phaseDurations.length; i++) {
    phaseEndDateMs += phaseDurations[i];
    const phaseEndDate = new Date(phaseEndDateMs);
    console.log(phaseEndDate.toISOString());
    console.log(now, phaseEndDate, now <= phaseEndDate, phaseEndDate - now < allowedVariance, phaseEndDate - now, allowedVariance);
    if ((now <= phaseEndDate) && ((phaseEndDate - now) < allowedVariance)) {
      phaseEndDateString = phaseEndDate.toISOString();
      return {
        phase: i + 1,
        phaseEndDateMilliseconds: phaseEndDate,
        phaseEndDateString: phaseEndDateString,
      };
    }
  };
  return false;
};

const getIncompleteTasksForPhase = (timelineTasks, phase, userId) => {
  const key = `phase_${phase}_list`;
  const phaseListItems = timelineTasks[key];
  console.log('getIncompleteTasksForPhase', key, phaseListItems);
  let promises = [];
  phaseListItems.forEach(phaseListItem => {
    promises.push(sdk.objects.list(TIMELINE_TASK_RESPONSE_SCHEMA, { user_id: userId, task_id: phaseListItem }).then(response => {
      console.log('response: ', response);
      if (response.length === 0) return phaseListItem;
      if (response[0] && !response[0].data.completed) { 
        return response[0];
      } else {
        return false;
      };
    }));
  });
  return Promise.all(promises);
};

/*
 * Gets all clients that haven't had their wedding yet
 */
const getActiveClients = () => 
  sdk.objects.list(USER_CLIENT_SCHEMA)
    .then(clients => {
      const date = new Date;
      const now = date.toISOString();
      const result = clients.filter(client => client.data.wedding_date > now);
      console.log('getActiveClients:', result);
      return result;
    });

const addToUnmatchedQueue = (userId) => {
  sdk.objects.list(UNMATCHED_CLIENTS_SCHEMA).then(results => {
    console.log('Unmatched client query:', results);
    if (!results) return;
    const objectId = results[0]._id;
    const clients = results[0].data.clients;
    if (clients && !clients.includes(userId)) {
      const data = { '$push': { clients: userId } };
      sdk.objects.updateFields(objectId, data).then(response => {
        console.log('Update unmatched clients:', response);
      });
    };
  });
};

const updateUnmatchedQueue = (userId) => {
  sdk.objects.list(UNMATCHED_CLIENTS_SCHEMA).then(results => {
    console.log('Unmatched client query:', results);
    const objectId = results[0]._id;
    const clients = results[0].data.clients;
    const idx = clients.indexOf(userId);
    if (clients && idx !== -1) {
      clients.splice(idx, 1);
      const data = { 'clients': clients };
      sdk.objects.updateFields(objectId, data).then(response => {
        console.log('Update unmatched clients:', response);
      });
    }
  });
};

const updateUserCoordinatorData = (userCoordinatorObjectId, userId, assignedCoordinator, clientName) => 
  sdk.objects.updateFields(userCoordinatorObjectId, { '$push': { client_ids: userId } }).then(response => {
    console.log('Update UserCoordinator with new client', response.data);
    const userToken = assignedCoordinator.data.device_token;
    const clientFirstName = clientName.split(' ')[0];
    const coordinatorId = assignedCoordinator.data.user_id;
    const alert = {
      title: 'You have a new client',
      body: `Meet your new client: ${clientFirstName}!`,
    };
    const payload = {
      user_id: coordinatorId,
      client_id: userId,
      coordinator_id: coordinatorId,
    };
    const category = 'coordinatorGotMatchedWithClient';
    sendPush(alert, payload, category, userToken, coordinatorId);
  });

const updateUserClientData = (userId, coordinatorAssignedId, coordinatorName, coordinatorProfileImage) =>
  sdk.objects.list(USER_CLIENT_SCHEMA, { user_id: userId }).then(userClientObjects => {
    console.log('Querying UserClients by user_id:', userClientObjects);
    const userObject = userClientObjects[0];
    const userClientObjectId = userClientObjects[0]._id;
    const coordinatorFirstName = coordinatorName.split(' ')[0];
    sdk.objects.updateFields(userClientObjectId, { coordinator_assigned_id: coordinatorAssignedId }).then(response => {
      console.log('UserClient update:', response.data);
      const userToken = response.data.device_token;
      const alert = {
        title: 'Meet your coordinator!',
        body: `Say hi to ${coordinatorFirstName}, who will help you plan your special day.`,
      };
      const payload = {
        user_id: userId,
        client_id: userId,
        coordinator_id: coordinatorAssignedId,
        coordinator_profile_image: coordinatorProfileImage,
      };
      const category = 'clientGotMatchedWithCoordinator';
      sendPush(alert, payload, category, userToken, userId);
    });
  });

const createConversation = (coordinatorAssignedId, userId, coordinatorName, clientName) => {
  const conversationData = {
    user_id: userId,
    coordinator_id: coordinatorAssignedId,
    messages: [],
    active: !0,
    coordinator_name: coordinatorName,
    user_name: clientName,
  };
  // Create new conversation between client and coordinator
  return sdk.objects.list(CONVERSATION_SCHEMA, { coordinator_id: coordinatorAssignedId, user_id: userId }).then(results => {
    if (!results || results.length === 0) {
      console.log(`Creating new CMS conversation object: ${conversationData}`);
      sdk.objects.create(CONVERSATION_SCHEMA, conversationData); 
    }
  });
};

const updateMatch = (userId) => {
  return sdk.objects.list(USER_CLIENT_SCHEMA, { user_id: userId }).then(results => {
    const newClient = results[0];
    const location = newClient.data.location_lat_long ? { location_lat_long: newClient.data.location_lat_long } : { location_lat_long: [37.789296, -122.404024] };
    console.log(`Http hook called: updateMatch. user_id: ${userId}, location: ${location}`);
    const locationFilter = {
      location_lat_long: {
        center: location.location_lat_long,
        max: MAX_MATCH_DISTANCE_METERS,
      }
    };
    // Get valid coordinators by location
    return sdk.objects.list(USER_COORDINATOR_SCHEMA, locationFilter).then(results => {
      console.log('Location filter: ', locationFilter);
      let coordinators = results;
      console.log('Query results, coordinators: ', coordinators);
      const activeClientRequests = [];
      coordinators.forEach(coordinator => {
        activeClientRequests.push(getCoordinatorValidClients(coordinator, newClient));
      });
      Promise.all(activeClientRequests).then(activeClientCounts => {
        if (coordinators.length === 0) {
          return addToUnmatchedQueue(userId);
        };
        const sortedResults = activeClientCounts.filter(clientCount => clientCount.numClients <= MAX_NUM_CLIENTS_PER_SEASON)
          .sort((a, b) => a.numClients > b.numClients);
        const coordinatorAssignedId = sortedResults[0].coordinator_id;
        const userCoordinatorObjectId = sortedResults[0].userCoordinatorObjectId;
        const assignedCoordinator = coordinators.find(coordinator => coordinator._id === userCoordinatorObjectId);
        const coordinatorName = `${assignedCoordinator.data.main_user_first_name} ${assignedCoordinator.data.main_user_last_name}`;
        const coordinatorProfileImage = assignedCoordinator.data.profile_image;
        console.log('active client count results', activeClientCounts, sortedResults);
        console.log('coordinator selected:', coordinatorAssignedId, assignedCoordinator);
        let matchedUsers = assignedCoordinator.data.client_ids;
        console.log('Matched client ids:', matchedUsers);
        if (matchedUsers.includes(userId)) {
          console.log('Client is already matched with this coordinator. Operation aborted.');
          return false;
        };
        console.log(`Querying UserCoordinators by location: ${location}, results: ${coordinators}, coordinatorAssignedId: ${coordinatorAssignedId}`);
        return sdk.objects.list(USER_CLIENT_SCHEMA, { user_id: userId }).then(userClients => {
          const clientName = `${userClients[0].data.main_user_first_name} ${userClients[0].data.main_user_last_name}`;
          const promises = [
            updateUserClientData(userId, coordinatorAssignedId, coordinatorName, coordinatorProfileImage),
            updateUserCoordinatorData(userCoordinatorObjectId, userId, assignedCoordinator, clientName),
            createConversation(coordinatorAssignedId, userId, coordinatorName, clientName),
            updateUnmatchedQueue(userId)
          ];
          Promise.all(promises);
        });
      });
    });
  });
};

/*
 * Given a coordinator and new client, validates the new client against
 * the coordinator's client list
 */
const getCoordinatorValidClients = (coordinator, newClient) => {
  let date = new Date;
  const now = date.toISOString();
  const userCoordinatorObjectId = coordinator._id;
  const coordinator_id = coordinator.data.user_id;
  const clientIds = coordinator.data.client_ids;
  console.log(`client ids for ${coordinator._id}, ${clientIds}`);
  const filter = { user_id: { $in: clientIds }};
  return sdk.objects.list(USER_CLIENT_SCHEMA, filter)
    .then(clients => {
      const numClients = validateClientWithSeason(clients, newClient);
      console.log(clients, numClients);
      return { userCoordinatorObjectId, coordinator_id, numClients };
    });
};

const addDays = (date, days) => {
    const d = new Date(date);
    d.setDate(d.getDate() + days);
    return d;
};

/*
 * Gets coordinator's clients per season and tests client
 * to see if new addition would invalidate the max # per season.
 * If valid, returns the new number of clients in that coordinator's season.
 */
const validateClientWithSeason = (originalClients, newClient) => {
  const clients = originalClients.concat(newClient);
  const newClientSeason = getSeasonFromClient(newClient);
  const seasonCounts = mapClientsToSeasonCount(clients);
  console.dir(seasonCounts, newClientSeason);
  const numClientsInSeason = seasonCounts[newClientSeason];
  if (numClientsInSeason > MAX_NUM_CLIENTS_PER_SEASON) {
    return false;
  };
  return numClientsInSeason;
};

const getSeason = (seasonName) =>
  SEASONS.find(season => season.name === seasonName);

/*
 * Gets season from a date
 */
const getSeasonFromDate = (date) => {
  const month = date.getMonth() + 1;
  const year = date.getFullYear();
  let result;
  return `${year}_${SEASONS.find(season => season.months.includes(month)).name}`;
};

const getNextDateFromSeasonName = (seasonName) => {
  const now = new Date();
  const earliestDate = addDays(now, MINIMUM_DAYS_TO_WEDDING);
  const season = getSeason(seasonName);
  let year = earliestDate.getFullYear();
  let seasonMidDate = new Date(`${season.mid} ${year}`);
  if (seasonMidDate < earliestDate) {
    year = year + 1;
    seasonMidDate = new Date(`${season.mid} ${year}`);
  };
  return seasonMidDate;
};

/*
 * Gets season from client with season only
 */
const getNextSeasonFromSeasonName = (seasonName) => {
  const now = new Date();
  const earliestDate = addDays(now, MINIMUM_DAYS_TO_WEDDING);
  let year = earliestDate.getFullYear();
  const season = getSeason(seasonName);
  let seasonStartDate = new Date(`${season.months[0]}/1/${year}`);
  if (seasonStartDate < earliestDate) {
    year = year + 1;
  };
  return `${year}_${season.name}`;
};

const mapClientsToSeasonCount = (clients) => {
  let seasonCount = {};
  clients.forEach(client => {
    const season = getSeasonFromClient(client);
    seasonCount = addToCollection(seasonCount, season);
  });
  return seasonCount;
};

const getSeasonFromClient = (client) => {
  const weddingDate = new Date(client.data.wedding_date);
  const seasonName = client.data.wedding_season;
  const seasonOnly = !weddingDate && seasonName;
  let season;
  if (!weddingDate && !seasonName) return false;
  if (seasonOnly) {
    season = getNextSeasonFromSeasonName(seasonName);
  } else {
    season = getSeasonFromDate(weddingDate);
  };
  return season;
};

const getDateFromClient = (client) => {
  console.log('getDateFromClient');
  const weddingDate = client.data.wedding_date;
  const seasonName = client.data.wedding_season;
  const seasonOnly = !weddingDate && seasonName;
  let date;
  if (seasonOnly) {
    console.log('season only');
    date = getNextDateFromSeasonName(seasonName);
  } else {
    date = new Date(weddingDate);
  };
  console.log('result', date);
  return date;
};

/*
 * Pure function that produces a map of item instance counts in a collection
 */ 
const addToCollection = (collection, item) => {
  let coll = Object.assign({}, collection);
  if (!coll.hasOwnProperty(item)) {
    coll[item] = 1;
  } else {
    coll[item] += coll[item];
  };
  return coll;
};

/*
 * Ensures required dataObjects exist for the user and creates them if not.
 */
const ensureUserData = (userId) =>
  sdk.endUsers.get(userId).then(endUser => {
    const log = (schema, data) => console.log(`Creating Data Object of type ${schema}. Payload: ${JSON.stringify(data)}`);
    const role = endUser.roles[0];
    const roleString = role.hasOwnProperty('id') ? String(role.id) : String(role);
    console.log('EnsureUserData, end user:', endUser, 'role', role, 'roleString', roleString);
    switch(roleString) {
      case USER_ROLE:
        const userClientData = {
          user_id: userId,
          main_user_email: endUser.email,
          shopping_items: [],
          favorited_vendors: [],
          recommended_vendors: []
        };
        const userClientFilter = { user_id: userId };
        return createDataObject(USER_CLIENT_SCHEMA, userClientData, userClientFilter, log);
        break;
      case COORDINATOR_ROLE:
        const data = {
          user_id: userId,
          main_user_email: endUser.email,
          client_ids: [],
        };
        const filter = { user_id: userId };
        return createDataObject(USER_COORDINATOR_SCHEMA, data, filter, log);
        break;
    }
  });

const ensureVendorData = (userId) =>
  sdk.users.get(userId).then(user => {
    const log = (schema, data) => console.log(`Creating Data Object of type ${schema}. Payload: ${JSON.stringify(data)}`);
    const role = user.roles[0].id;
    console.log(`User ${user}, role: ${role}, vendor_role: ${VENDOR_ROLE}`);
    const data = {
      user_id: userId,
      email: user.email,
    };
    const filter = { user_id: userId };
    if (role === VENDOR_ROLE) {
      return createDataObject(USER_VENDOR_SCHEMA, data, filter, log);
    };
  });
/*
 * Creates dataObjects from a list of schemas and values to initialize with
 */
const createDataObjectsFromList = (schemas, data, filter, log) => {
  if (!log) { log = console.log };
  return schemas.map(schema => createDataObject(schema, data, filter, log));
};
/*
 * Create a dataObject from a schemas and values to initialize with
 */
const createDataObject = (schema, data, filter, log) =>
  sdk.objects.list(schema, filter).then(results => {
    console.log(results);
    if (!results || results.length === 0) {
      log(schema, data);
      sdk.objects.create(schema, data);
    };
    return results;
  });

// Gets all active clients and sends timeline task nudges
const sendTimelineTaskNudges = () =>
  Promise.all([getActiveClients(), getMasterTimelineTasks()])
    .then(([activeClients, timelineTasks]) => {
      console.log('active clients: ', activeClients, 'timeline tasks', timelineTasks);
      const timelineTasksList = timelineTasks.data;
      activeClients.forEach(activeClient => {
        if (!activeClient.data.coordinator_assigned_id) {
          return false;
        };
        // for each active client
        const createdDate = new Date(activeClient.createdAt);
        // const weddingDate = new Date(activeClient.data.wedding_date);
        const weddingDate = getDateFromClient(activeClient);
        console.log(`client: ${activeClient.data.main_user_email}`, createdDate, weddingDate);
        const upcomingPhase = createTimelinePhaseMap(createdDate, weddingDate);
        if (upcomingPhase) {
          console.log('upcoming phase: ', upcomingPhase);
          getIncompleteTasksForPhase(timelineTasksList, upcomingPhase.phase, activeClient.data.user_id).then(response => {
            console.log(`client: ${activeClient.data.main_user_first_name}`, 'incomplete tasks for phase:', response);
            const incompleteTasks = response.filter(task => !!task);
            if (incompleteTasks.length > 0) {
              sendNudge(incompleteTasks, activeClient, upcomingPhase);
            }
          });   
        } else {
          console.log('no upcoming phases for client');
        }
      })
    })
    .catch(err => {
      throw console.error(err);
    });

const sendNudge = (tasks, client, phase) => {
  console.log('sending nudge for tasks: ', tasks, client, phase);
  // send client nudge
  const alert = {
    title: 'Get that task done!',
    body: `Don't fall behind schedule! Take care of that overdue task and move on to the next phase!`,
  };
  const payload = {
    phase: phase.phase,
  };
  const category = 'coupleNudgeCurrentPhaseTasks';
  sendPush(alert, payload, category, client.data.device_token, client.data.user_id);
  // send coordinator nudge
  if (client.data.coordinator_assigned_id) {
    sdk.objects.list(USER_COORDINATOR_SCHEMA, { user_id: client.data.coordinator_assigned_id }).then(response => {
      const coordinator = response[0];
      console.log('sending push to coordinator');
      const alert = {
        title: 'Task overdue',
        body: `${client.data.main_user_first_name} is falling behind schedule, now is a good time to check in with them.`,
      };
      const payload = {
        phase: phase.phase,
      };
      const category = 'coordinatorGotNudgedAboutClientCurrentPhaseTasks';
      sendPush(alert, payload, category, coordinator.data.device_token, client.data.coordinator_assigned_id);
    });
  }
};

const getDeviceTokenFromId = (userId, isCoordinator) => {
  const schema = isCoordinator ? USER_COORDINATOR_SCHEMA : USER_CLIENT_SCHEMA;
  return sdk.objects.list(schema, { user_id: userId }).then(results => {
    console.log('getDeviceTokenFromId', results);
    if (results[0].data.device_token) {
      return results[0].data.device_token;
    };
  });
};

const pushCoupleRecommendedVendor = (clientId, coordinatorName, vendorId, coordinatorProfileImage) =>
  getDeviceTokenFromId(clientId).then(deviceToken => {
    const alert = {
      title: 'New Recommendation!',
      body: `${coordinatorName} recommended a new vendor.`,
    };
    const payload = {
      vendor_id: vendorId,
      coordinator_profile_image: coordinatorProfileImage
    };
    const category = 'clientGotRecommendedVendorByCoordinator';
    sendPush(alert, payload, category, deviceToken, clientId);
  });

const pushCoordinatorBookedVendor = (coordinatorId, clientId, clientName, taskId, phase) =>
  getDeviceTokenFromId(coordinatorId, true).then(deviceToken => {
    const alert = {
      title: 'Vendor Booked!',
      body: `${clientName} has booked a vendor`,
    };
    const payload = {
      client_id: clientId,
      task_id: taskId,
      phase: phase,
    };
    const category = 'coordinatorNotifiedBookedVendorByClient';
    sendPush(alert, payload, category, deviceToken, coordinatorId);
  });

const pushCoordinatorAddedShoppingItem = (clientId, shoppingItemId, coordinatorProfileImage) =>
  getDeviceTokenFromId(clientId).then(deviceToken => {
    const alert = {
      title: 'Item added to shopping list',
      body: 'Your planner has added a new item to your shopping list',
    };
    const payload = {
      shopping_item_id: shoppingItemId,
      coordinator_profile_image: coordinatorProfileImage
    };
    const category = 'clientGotShoppingItemAddedByCoordinator';
    sendPush(alert, payload, category, deviceToken, clientId);
  });

const sendVendorCommunicationEmail = (vendorName, clientFullName, clientEmail, clientPhoneNumber, communicationType) => {
  console.log('sending vendor comm email', vendorName, clientFullName, clientEmail, clientPhoneNumber, communicationType);
  const contactInfo = communicationType === 'email' ? `Email: ${clientEmail}` : `Phone Number: ${clientPhoneNumber}`;
  sdk.email({
      from: ANALYTICS_FROM_EMAIL,
      to: ANALYTICS_TO_EMAIL,
      subject: 'New vendor communiation requested',
      text: `User: ${clientFullName}\n\n${contactInfo}\n\nVendor: ${vendorName}\n\nMethod: ${communicationType}`,
  });
};

const sendUnsupportedLocationClient = (email, locationString, locationLatLong, locationGooglePlaceId) =>
  sdk.objects.updateFields(UNSUPPORTED_LOCATION_OBJECT_ID, { $push: { users: { 
    email: email, 
    location_string: locationString,
    location_lat_long: locationLatLong,
    location_google_place_id: locationGooglePlaceId,
  }}});
    

sdk.hooks.onInterval('00 30 11 * * *', () => {
  console.dir('every day of the week at 11:30 AM');
  sendTimelineTaskNudges();
});

sdk.hooks.onUpdate(USER_CLIENT_SCHEMA, response => {
  console.log('user client', response);
  const clientId = response.data.user_id;
  if (response.data.coordinator_assigned_id !== response.oldData.coordinator_assigned_id) {
    console.log('clients coordinator unmatched', response.oldData.coordinator_assigned_id);
    sdk.objects.list(USER_COORDINATOR_SCHEMA, { user_id: response.oldData.coordinator_assigned_id }).then(response => {
      const userCoordinatorObjectId = response[0]._id;
      // Remove client from coordinator's clients list and set
      const clientIds = response[0].data.client_ids;
      const idx = clientIds.indexOf(clientId);
      clientIds.splice(idx, 1);
      console.log('unmatching client from coordinator clients list', response, clientIds);
      const data = { client_ids: clientIds };
      sdk.objects.updateFields(userCoordinatorObjectId, data);
    });
  }
});

sdk.hooks.onUpdate(USER_COORDINATOR_SCHEMA, response => {
  console.log('user coordinator', response);
  if (response.data.client_ids.length < response.oldData.client_ids.length) {
    const lastClient = response.oldData.client_ids[response.oldData.client_ids.length - 1];
    console.log('coordinators client list, client unmatched', lastClient);
    sdk.objects.list(USER_CLIENT_SCHEMA, { user_id: lastClient }).then(response => {
      console.log('unmatching coordinator from client object', response);
      const userClientObjectId = response[0]._id;
      // Set client's assigned coordinator to emptry string or null
      const data = { coordinator_assigned_id: '' };
      sdk.objects.updateFields(userClientObjectId, data);
    });
  };
  // Array equality check for arrays without objects ONLY
  if (JSON.stringify(response.data.location_lat_long) !== JSON.stringify(response.oldData.location_lat_long)) {
    console.log('coordinator location changed');
    sdk.objects.list(UNMATCHED_CLIENTS_SCHEMA).then(results => {
      const clients = results[0].data.clients;
      console.log('coordinator on create', clients, results);
      clients.forEach(client => {
        console.log(`Checking if new match for client: ${client}`);
        updateMatch(client);
      });
    });
  }
});

sdk.hooks.onUpdate(CONVERSATION_SCHEMA, response => {
  // Send push to chat recipient on conversation update
  console.log('Hook: Conversation Object onUpdate:', response);
  const conversation_id = response.id;
  const { messages, user_id, coordinator_id, coordinator_name, user_name } = response.data;
  const recipient_id = messages[messages.length - 1].recipient_id;
  const recipientIsClient = recipient_id === user_id;
  console.log(`Recipient_id ${recipient_id}, user_id ${user_id}, recipient is client: ${recipientIsClient}`);
  const filter = { user_id: recipient_id };
  sdk.objects.list((recipientIsClient ? USER_CLIENT_SCHEMA : USER_COORDINATOR_SCHEMA), filter).then(results => {
    console.log(`Querying ${recipientIsClient ? 'UserClient' : 'UserCoordinator'} for recipient: ${results}`);
    const token = results[0].data.device_token;
    const name = results[0].data.main_user_first_name;
    const message = messages[messages.length - 1].message_text;
    const alert = {
      title: '',
      body: `${recipientIsClient ? coordinator_name : user_name} says: ${message}`,
    };
    const payload = {
      recipient_id: recipient_id,
      client_id: user_id,
      coordinator_id: coordinator_id,
      conversation_id: conversation_id,
      coordinator_profile_image: recipientIsClient ? null : results[0].data.coordinator_profile_image,
    };
    const category = recipientIsClient ? 'clientReceivedNewChatMessageFromCoordinator' : 'coordinatorReceivedNewChatMessageFromClient';
    sendPush(alert, payload, category, token, recipient_id);
  });
});

sdk.hooks.onCreateUser((user) => {
  // ensure vendor
  const role = String(user.roles[0].id);
  console.log('Hook: onCreateUser', role);
  switch(role) {
    case VENDOR_ROLE:
      const data = {
        user_id: user.id,
        email: user.email,
        name: 'New Vendor'
      };
      const filter = { user_id: user.id };
      createDataObject(USER_VENDOR_SCHEMA, data, filter);
      break;
  }
});

sdk.hooks.onDeleteUser((user) => {
  const role = String(user.roles[0].id);
  const userId = String(user.id);
  console.log('Hook: onDeleteUser', role);
  let schemaId;
  switch(role) {
    case VENDOR_ROLE:
      schemaId = USER_VENDOR_SCHEMA;
      break;
  };
  sdk.objects.list(schemaId, { user_id: userId }).then(results => {
    console.log('***', role, results);
    const objId = results[0]._id;
    sdk.objects.deleteOne(objId).then(response => console.log(response));
  });
});

sdk.hooks.onDeleteEndUser((user) => {
  const role = String(user.roles[0].id);
  const userId = String(user.id);
  console.log('Hook: onDeleteEndUser', userId, role);
  switch(role) {
    case COORDINATOR_ROLE:
      schemaId = USER_COORDINATOR_SCHEMA;
      break;
    case USER_ROLE:
      schemaId = USER_CLIENT_SCHEMA;
      break;
  };
  sdk.objects.list(schemaId, { user_id: userId }).then(results => {
    console.log('***', role, results);
    const objId = results[0]._id;
    sdk.objects.deleteOne(objId).then(response => console.log(response));
  });
});

sdk.hooks.onHttpCall('test', () => { sendTimelineTaskNudges() });
sdk.hooks.onHttpCall('ensureUserData', ({
  user_id
}) => ensureUserData(user_id));
sdk.hooks.onHttpCall('ensureVendorData', ({
  user_id
}) => ensureVendorData(user_id));
sdk.hooks.onHttpCall('updateMatch', ({
  user_id
}) => setTimeout(() => updateMatch(user_id), MATCH_DELAY));
sdk.hooks.onHttpCall('sendVendorCommunicationEmail', ({ 
  vendor_name,
  client_full_name,
  client_email,
  client_phone_number,
  communication_type 
}) => sendVendorCommunicationEmail(vendor_name, client_full_name, client_email, client_phone_number, communication_type));
sdk.hooks.onHttpCall('clientGotRecommendedVendorByCoordinator', ({
  client_id,
  coordinator_first_name,
  vendor_id,
  coordinator_profile_image,
}) => pushCoupleRecommendedVendor(client_id, coordinator_first_name, vendor_id, coordinator_profile_image));
sdk.hooks.onHttpCall('coordinatorNotifiedBookedVendorByClient', ({
  coordinator_id,
  client_id,
  client_first_name,
  task_id,
  phase
}) => pushCoordinatorBookedVendor(coordinator_id, client_id, client_first_name, task_id, phase));
sdk.hooks.onHttpCall('clientGotShoppingItemAddedByCoordinator', ({
  client_id,
  shopping_item_id,
  coordinator_profile_image,
}) => pushCoordinatorAddedShoppingItem(client_id, shopping_item_id, coordinator_profile_image));
sdk.hooks.onHttpCall('sendUnsupportedLocationClient', { allowAnonymous: true }, ({
  email,
  location_string,
  location_lat_long,
  location_google_place_id,
}) => sendUnsupportedLocationClient(email, location_string, location_lat_long, location_google_place_id));

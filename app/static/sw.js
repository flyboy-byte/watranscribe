const CACHE_NAME = 'watranscribe-v11';
const IDB_NAME   = 'watranscribe-shared-files';
const IDB_STORE  = 'files';

const PRECACHE = [
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/apple-touch-icon.png',
  '/static/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle Web Share Target POST
  if (request.method === 'POST' && url.pathname === '/static/share') {
    event.respondWith(handleShareTarget(request));
    return;
  }

  // Cache-first for static assets
  if (request.method === 'GET' && url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request))
    );
  }
});

// Accept clearAll messages from the page so Clear All can wipe the queue
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'clearAll') {
    clearAllSharedFiles();
  }
});

async function handleShareTarget(request) {
  try {
    const formData = await request.formData();
    const files = formData.getAll('audio');
    if (files.length > 0) {
      await writeSharedFiles(files);
      return Response.redirect('/?wa_shared=1', 303);
    }
  } catch (e) {
    console.error('[SW] Share target error:', e);
  }
  return Response.redirect('/', 303);
}

function openIDB() {
  return new Promise((resolve, reject) => {
    // Version 2: switched to keyPath:'name' for dedup-by-filename
    const req = indexedDB.open(IDB_NAME, 2);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (db.objectStoreNames.contains(IDB_STORE)) {
        db.deleteObjectStore(IDB_STORE);
      }
      db.createObjectStore(IDB_STORE, { keyPath: 'name' });
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror   = (e) => reject(e.target.error);
  });
}

// Accumulate files across shares — put() overwrites by name so no dupes
async function writeSharedFiles(files) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(IDB_STORE, 'readwrite');
    const store = tx.objectStore(IDB_STORE);
    for (const file of files) {
      store.put({ blob: file, name: file.name, type: file.type });
    }
    tx.oncomplete = () => resolve();
    tx.onerror    = () => reject(tx.error);
  });
}

async function clearAllSharedFiles() {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, 'readwrite');
    tx.objectStore(IDB_STORE).clear();
    tx.oncomplete = () => resolve();
    tx.onerror    = () => reject(tx.error);
  });
}

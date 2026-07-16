// WhatsApp share-target flow: the service worker (static/sw.js) intercepts
// the Web Share Target POST, stashes the shared audio file(s) in IndexedDB,
// and redirects to "/?wa_shared=1". On load here, if that query param is
// present, read the file(s) back out of IndexedDB, populate the visible
// file <input>, and auto-submit the upload form — mirroring the original
// app.py's injected "populate file input" JS, now a normal static file
// loaded by the template instead of being string-concatenated into
// st.markdown.
(function () {
  const IDB_NAME = "watranscribe-shared-files";
  const IDB_STORE = "files";

  function openIDB() {
    return new Promise(function (resolve, reject) {
      const req = indexedDB.open(IDB_NAME, 2);
      req.onupgradeneeded = function (e) {
        const db = e.target.result;
        if (db.objectStoreNames.contains(IDB_STORE)) db.deleteObjectStore(IDB_STORE);
        db.createObjectStore(IDB_STORE, { keyPath: "name" });
      };
      req.onsuccess = function (e) {
        resolve(e.target.result);
      };
      req.onerror = function (e) {
        reject(e.target.error);
      };
    });
  }

  function readAndClearSharedFiles(db) {
    return new Promise(function (resolve) {
      const tx = db.transaction(IDB_STORE, "readwrite");
      const store = tx.objectStore(IDB_STORE);
      const all = store.getAll();
      all.onsuccess = function () {
        store.clear();
        resolve(all.result || []);
      };
      all.onerror = function () {
        resolve([]);
      };
    });
  }

  function injectAndSubmit(fileObjects) {
    const input = document.getElementById("wa-file-input");
    const form = document.getElementById("wa-upload-form");
    if (!input || !form) return;

    const dt = new DataTransfer();
    fileObjects.forEach(function (f) {
      dt.items.add(f);
    });
    const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "files");
    if (desc && desc.set) {
      desc.set.call(input, dt.files);
    } else {
      input.files = dt.files;
    }

    const url = new URL(window.location.href);
    url.searchParams.delete("wa_shared");
    window.history.replaceState({}, "", url.toString());

    form.submit();
  }

  const params = new URLSearchParams(window.location.search);
  if (!params.has("wa_shared")) return;

  openIDB()
    .then(function (db) {
      return readAndClearSharedFiles(db);
    })
    .then(function (items) {
      if (!items.length) return;
      const fileObjects = items.map(function (item) {
        const blob = item.blob;
        if (blob instanceof File) return blob;
        return new File([blob], item.name || "audio.opus", { type: item.type || "audio/ogg" });
      });
      injectAndSubmit(fileObjects);
    })
    .catch(function (err) {
      console.error("[PWA] Share read error:", err);
    });
})();

const DB_NAME = "bytez-read-history";
const ARTICLES_STORE = "articles";
const FLAGS_STORE = "flags";
const DB_VERSION = 2;

const INSTALL_BANNER_KEY = "tnforme:install-banner-dismissed";
const ALL_READ_EGG_PREFIX = "all-read-egg:";

type ReadRecord = {
  id: string;
  slug: string;
  readAt: number;
};

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(ARTICLES_STORE)) {
        db.createObjectStore(ARTICLES_STORE, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(FLAGS_STORE)) {
        db.createObjectStore(FLAGS_STORE, { keyPath: "key" });
      }
    };
  });
}

export async function markStoryRead(id: string, slug: string): Promise<void> {
  if (typeof window === "undefined") return;
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ARTICLES_STORE, "readwrite");
    tx.oncomplete = () => {
      db.close();
      window.dispatchEvent(new CustomEvent("tnforme:story-read"));
      resolve();
    };
    tx.onerror = () => reject(tx.error);
    tx.objectStore(ARTICLES_STORE).put({
      id,
      slug,
      readAt: Date.now(),
    } satisfies ReadRecord);
  });
}

export async function isStoryRead(id: string): Promise<boolean> {
  if (typeof window === "undefined") return false;
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ARTICLES_STORE, "readonly");
    tx.onerror = () => reject(tx.error);
    const request = tx.objectStore(ARTICLES_STORE).get(id);
    request.onsuccess = () => {
      db.close();
      resolve(request.result !== undefined);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function getReadStoryIds(): Promise<string[]> {
  if (typeof window === "undefined") return [];
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ARTICLES_STORE, "readonly");
    tx.onerror = () => reject(tx.error);
    const request = tx.objectStore(ARTICLES_STORE).getAllKeys();
    request.onsuccess = () => {
      db.close();
      resolve((request.result as string[]) ?? []);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function wasAllReadEggShown(setKey: string): Promise<boolean> {
  if (typeof window === "undefined") return true;
  const db = await openDb();
  const flagKey = `${ALL_READ_EGG_PREFIX}${setKey}`;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(FLAGS_STORE, "readonly");
    tx.onerror = () => reject(tx.error);
    const request = tx.objectStore(FLAGS_STORE).get(flagKey);
    request.onsuccess = () => {
      db.close();
      resolve(request.result !== undefined);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function markAllReadEggShown(setKey: string): Promise<void> {
  if (typeof window === "undefined") return;
  const db = await openDb();
  const flagKey = `${ALL_READ_EGG_PREFIX}${setKey}`;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(FLAGS_STORE, "readwrite");
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => reject(tx.error);
    tx.objectStore(FLAGS_STORE).put({ key: flagKey, shownAt: Date.now() });
  });
}

export const INSTALL_BANNER_DISMISS_KEY = INSTALL_BANNER_KEY;

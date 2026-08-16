const DB_NAME = "bytez-read-history";
const STORE_NAME = "articles";
const DB_VERSION = 1;

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
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };
  });
}

export async function markStoryRead(id: string, slug: string): Promise<void> {
  if (typeof window === "undefined") return;
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => reject(tx.error);
    tx.objectStore(STORE_NAME).put({
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
    const tx = db.transaction(STORE_NAME, "readonly");
    tx.onerror = () => reject(tx.error);
    const request = tx.objectStore(STORE_NAME).get(id);
    request.onsuccess = () => {
      db.close();
      resolve(request.result !== undefined);
    };
    request.onerror = () => reject(request.error);
  });
}

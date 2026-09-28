// sw.js — Claude Code 마스터 클래스 PWA Service Worker
const CACHE_NAME = 'claude-code-pwa-v1';
const PRECACHE_ASSETS = [
  '/',
  '/favicon.svg',
  '/apple-touch-icon.png',
  '/og.png',
  '/manifest.webmanifest'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(PRECACHE_ASSETS).catch(err => {
        // 일부 정적 에셋 실패 시에도 서비스워커 설치는 완료
        console.warn('[SW] Precache partial error:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  // GET 요청 및 동일 오리진만 처리
  if (req.method !== 'GET' || !req.url.startsWith(self.location.origin)) {
    return;
  }

  // HTML 내비게이션 요청은 Network-First, 실패 시 캐시된 index.html 서빙
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then(res => {
          if (res && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(cache => cache.put('/', clone));
          }
          return res;
        })
        .catch(() => {
          return caches.match('/', { ignoreSearch: true })
            .then(cached => cached || caches.match('/index.html', { ignoreSearch: true }));
        })
    );
    return;
  }

  // 기타 정적 파일(이미지, 매니페스트 등): Cache-First 또는 Stale-While-Revalidate
  event.respondWith(
    caches.match(req, { ignoreSearch: true }).then(cached => {
      if (cached) {
        // 백그라운드 갱신
        fetch(req).then(res => {
          if (res && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
          }
        }).catch(() => {});
        return cached;
      }
      return fetch(req).then(res => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
        }
        return res;
      });
    })
  );
});

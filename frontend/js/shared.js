/**
 * DIMA CUP — Shared Components & Data Layer
 * ==========================================
 * Los datos viven en MongoDB Atlas, servidos a través de un backend
 * en FastAPI (carpeta /backend-fastapi, desplegado por separado en
 * Render/Railway/Fly, ya que Netlify no ejecuta Python).
 *
 * Todas las páginas leen de DC.teams, DC.matches, etc. (igual que antes),
 * pero esos datos llegan por fetch() en vez de localStorage.
 *
 * IMPORTANTE: como los datos llegan por red, cada página debe esperar
 * `await DC.ready` antes de usar DC.teams/players/matches/news/sponsors.
 * (Ya está hecho en todas las páginas del sitio — si agregas una página
 * nueva, recuerda hacer lo mismo.)
 */

/* ─────────────────────────────────────────
   CONFIGURACIÓN DE LA API
   ───────────────────────────────────────── */
/* Antes esto era '/api' porque Netlify redirigía a sus funciones en el
   mismo dominio. Ahora el backend FastAPI vive en otro servicio/dominio
   (ej. https://dimacup-api.onrender.com), así que hay que apuntar ahí.
   Cambia SOLO esta línea cuando despliegues el backend: */
const API_BASE = 'https://futbol-res5.onrender.com/api';

/* Si algún día vuelves a servir frontend y backend desde el mismo
   dominio (ej. FastAPI sirviendo también los HTML), puedes regresar a: */
// const API_BASE = '/api';

const Api = {
  async get(resource) {
    const res = await fetch(`${API_BASE}/${resource}`);
    if (!res.ok) throw new Error('Error al consultar ' + resource);
    return res.json();
  },
  async post(resource, body) {
    const res = await fetch(`${API_BASE}/${resource}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || ('Error al guardar en ' + resource));
    return data;
  },
  async del(resource, id) {
    const res = await fetch(`${API_BASE}/${resource}?id=${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Error al eliminar en ' + resource);
    return res.json();
  },
};

/* Caché en memoria — se llena al cargar la página y se actualiza tras cada cambio */
const _cache = { teams: [], players: [], matches: [], news: [], sponsors: [] };

async function _loadAll() {
  const [teams, players, matches, news, sponsors] = await Promise.all([
    Api.get('teams'),
    Api.get('players'),
    Api.get('matches'),
    Api.get('news'),
    Api.get('sponsors'),
  ]);
  _cache.teams = teams; _cache.players = players; _cache.matches = matches;
  _cache.news = news;   _cache.sponsors = sponsors;
}

/* ─────────────────────────────────────────
   DC — fachada de datos (mismo API que antes,
   pero ahora respaldada por MySQL vía PHP)
   ───────────────────────────────────────── */
const DC = {
  /* Promesa que se resuelve cuando los datos iniciales ya están en caché.
     Toda página debe hacer `await DC.ready` antes de leer DC.teams, etc. */
  ready: _loadAll().catch(err => {
    console.error('No se pudo conectar con la base de datos:', err);
    showToastSafe('⚠️ No se pudo conectar con el servidor/base de datos. Revisa la variable MONGODB_URI en Netlify.');
  }),

  get teams()    { return _cache.teams;    },
  get players()  { return _cache.players;  },
  get matches()  { return _cache.matches;  },
  get news()     { return _cache.news;     },
  get sponsors() { return _cache.sponsors; },

  /* Devuelve HTML: <img> si el equipo/jugador tiene imagen subida, si no el emoji como texto.
     size = tamaño en px (cuadrado), o 'fill' para que la imagen ocupe el 100% de su contenedor
     (úsalo cuando el contenedor padre ya tiene un ancho/alto fijo por CSS, ej. .team-shield, .player-avatar). */
  crest(team, size = 48) {
    if (team && team.img) {
      const dim = size === 'fill' ? 'width:100%;height:100%;' : `width:${size}px;height:${size}px;`;
      return `<img src="${team.img}" alt="${team.name || ''}" style="${dim}object-fit:cover;border-radius:inherit;display:block;">`;
    }
    return team ? (team.emoji || '⚽') : '⚽';
  },
  avatar(player, size = 48) {
    if (player && player.img) {
      const dim = size === 'fill' ? 'width:100%;height:100%;' : `width:${size}px;height:${size}px;`;
      return `<img src="${player.img}" alt="${player.name || ''}" style="${dim}object-fit:cover;border-radius:inherit;display:block;">`;
    }
    return player ? (player.emoji || '⚽') : '⚽';
  },

  getTeam:        (id)  => _cache.teams.find(t => t.id == id),
  getPlayer:      (id)  => _cache.players.find(p => p.id == id),
  getMatch:       (id)  => _cache.matches.find(m => m.id == id),
  getTeamPlayers: (tid) => _cache.players.filter(p => p.team == tid),
  getTeamMatches: (tid) => _cache.matches.filter(m => m.local == tid || m.visit == tid),

  /* ── Equipos ── */
  async saveTeam(team) {
    const saved = await Api.post('teams', team);
    const i = _cache.teams.findIndex(t => t.id == saved.id);
    if (i >= 0) _cache.teams[i] = saved; else _cache.teams.push(saved);
    return saved;
  },
  async deleteTeam(id) {
    await Api.del('teams', id);
    _cache.teams = _cache.teams.filter(t => t.id != id);
  },

  /* ── Jugadores ── */
  async savePlayer(player) {
    const saved = await Api.post('players', player);
    const i = _cache.players.findIndex(p => p.id == saved.id);
    if (i >= 0) _cache.players[i] = saved; else _cache.players.push(saved);
    return saved;
  },
  async deletePlayer(id) {
    await Api.del('players', id);
    _cache.players = _cache.players.filter(p => p.id != id);
  },

  /* ── Partidos ──
     El cálculo de la tabla de posiciones ahora lo hace el servidor
     (netlify/functions/matches.js) cada vez que se guarda/elimina un partido,
     así que aquí simplemente recargamos equipos + partidos desde la API. */
  async saveMatch(match) {
    const saved = await Api.post('matches', match);
    const [teams, matches] = await Promise.all([Api.get('teams'), Api.get('matches')]);
    _cache.teams = teams; _cache.matches = matches;
    return saved;
  },
  async deleteMatch(id) {
    await Api.del('matches', id);
    const [teams, matches] = await Promise.all([Api.get('teams'), Api.get('matches')]);
    _cache.teams = teams; _cache.matches = matches;
  },

  /* Fases del torneo, en orden. 'Grupos' alimenta la tabla de posiciones;
     el resto son la eliminatoria directa (estilo Mundial). */
  FASES: ['Grupos', 'Octavos de Final', 'Cuartos de Final', 'Semifinal', 'Tercer Lugar', 'Final'],
  FASES_ELIMINACION: ['Octavos de Final', 'Cuartos de Final', 'Semifinal', 'Tercer Lugar', 'Final'],

  /* Letras de grupo presentes actualmente entre los equipos, ordenadas (A, B, C...) */
  get groups() {
    const set = new Set(_cache.teams.map(t => t.grupo || 'A'));
    return [...set].sort();
  },
  getGroupTeams: (g) => _cache.teams.filter(t => (t.grupo || 'A') === g),

  /* ── Noticias ── */
  async saveNews(item) {
    const saved = await Api.post('news', item);
    const i = _cache.news.findIndex(n => n.id == saved.id);
    if (i >= 0) _cache.news[i] = saved; else _cache.news.unshift(saved);
    return saved;
  },
  async deleteNews(id) {
    await Api.del('news', id);
    _cache.news = _cache.news.filter(n => n.id != id);
  },

  /* ── Patrocinadores ── */
  async saveSponsor(item) {
    const saved = await Api.post('sponsors', item);
    const i = _cache.sponsors.findIndex(s => s.id == saved.id);
    if (i >= 0) _cache.sponsors[i] = saved; else _cache.sponsors.push(saved);
    return saved;
  },
  async deleteSponsor(id) {
    await Api.del('sponsors', id);
    _cache.sponsors = _cache.sponsors.filter(s => s.id != id);
  },

  /* Recarga todo desde la base de datos (botón "Recargar datos" del admin) */
  async reset() {
    await _loadAll();
  },
};

/* showToast aún no existe cuando DC.ready se crea (se define más abajo en
   este mismo archivo), así que usamos un envoltorio seguro para no romper
   la carga si algo falla antes de tiempo. */
function showToastSafe(msg) {
  if (typeof showToast === 'function') showToast(msg, 6000);
  else console.warn(msg);
}


/* ─────────────────────────────────────────
   ROUTER
   ───────────────────────────────────────── */
const Router = {
  base: '',
  go(path)  { window.location.href = this.base + path + '.html'; },
  href(path){ return path === '/' ? this.base + '/index.html' : this.base + path + '.html'; },
  current() {
    const p = window.location.pathname;
    if (p.endsWith('index.html') || p === '/' || p === '') return '/';
    const clean = p.replace(/\.html$/, '').split('/').pop();
    return '/' + clean;
  },
};

/* ─────────────────────────────────────────
   COMPONENTS
   ───────────────────────────────────────── */

function injectLoader() {
  const el = document.createElement('div');
  el.id = 'loader';
  el.innerHTML = `<div class="loader-inner"><div class="loader-logo">TORNEO CUP</div><div class="loader-bar"></div></div>`;
  document.body.prepend(el);
  setTimeout(() => el.classList.add('hidden'), 800);
}

function injectNavbar() {
  const cur = Router.current();
  const links = [
    ['/index',       'Inicio'],
    ['/equipos',     'Equipos'],
    ['/jugadores',   'Jugadores'],
    ['/calendario',  'Calendario'],
    ['/resultados',  'Resultados'],
    ['/posiciones',  'Posiciones'],
    ['/estadisticas','Estadísticas'],
    ['/galeria',     'Galería'],
    ['/patrocinadores','Patrocinadores'],
  ];

  const liLinks = links.map(([path, label]) => {
    const href = path === '/index' ? 'index.html' : path.slice(1) + '.html';
    const isActive = cur === '/' ? path === '/index' : cur.startsWith(path);
    return `<li><a href="${href}" class="${isActive ? 'active' : ''}">${label}</a></li>`;
  }).join('');

  const mobileLinksFull = [...links, ['/reglamento','Reglamento'],['/contacto','Contacto'],['/admin','Admin']]
    .map(([path, label]) => {
      const href = path === '/index' ? 'index.html' : path.slice(1) + '.html';
      const isActive = cur === '/' ? path === '/index' : cur.startsWith(path);
      return `<a href="${href}" class="${isActive ? 'active' : ''}">${label}</a>`;
    }).join('');

  const navbar = document.createElement('nav');
  navbar.className = 'navbar'; navbar.id = 'navbar';
  navbar.innerHTML = `
    <div class="nav-inner">
      <a href="index.html" class="nav-logo">
        <div><div class="nav-logo-text">Torneo CUP</div><div class="nav-logo-sub">Torneo Oficial 2025</div></div>
      </a>
      <ul class="nav-links">${liLinks}</ul>
      <div class="nav-actions">
        <a href="contacto.html" class="btn-inscribir">Inscribir equipo</a>
        <button class="hamburger" id="hamburgerBtn" aria-label="Menú">
          <span></span><span></span><span></span>
        </button>
      </div>
    </div>`;

  const mobileMenu = document.createElement('div');
  mobileMenu.className = 'mobile-menu'; mobileMenu.id = 'mobileMenu';
  mobileMenu.innerHTML = mobileLinksFull;

  document.body.prepend(mobileMenu);
  document.body.prepend(navbar);

  window.addEventListener('scroll', () => navbar.classList.toggle('scrolled', window.scrollY > 20));
  document.getElementById('hamburgerBtn').addEventListener('click', () => mobileMenu.classList.toggle('open'));
  mobileMenu.addEventListener('click', e => { if (e.target.tagName === 'A') mobileMenu.classList.remove('open'); });
}

function injectFooter() {
  const footer = document.createElement('footer');
  footer.className = 'footer';
  footer.innerHTML = `
    <div class="container">
      <div class="footer-grid">
        <div class="footer-brand">
          <div class="logo-text">Torneo Cup</div>
          <p>El torneo de fútbol más importante del estado de Durango. Donde nacen los campeones.</p>
          <div class="footer-social">
            <a href="#" title="Facebook">📘</a><a href="#" title="Instagram">📸</a>
            <a href="#" title="Twitter/X">🐦</a><a href="#" title="YouTube">▶️</a><a href="#" title="WhatsApp">💬</a>
          </div>
        </div>
        <div class="footer-col"><h4>Torneo</h4><ul>
          <li><a href="equipos.html">Equipos</a></li><li><a href="jugadores.html">Jugadores</a></li>
          <li><a href="calendario.html">Calendario</a></li><li><a href="resultados.html">Resultados</a></li>
          <li><a href="posiciones.html">Posiciones</a></li><li><a href="eliminacion.html">Eliminación</a></li><li><a href="estadisticas.html">Estadísticas</a></li>
        </ul></div>
        <div class="footer-col"><h4>Contenido</h4><ul>
          <li><a href="noticias.html">Noticias</a></li><li><a href="galeria.html">Galería</a></li>
          <li><a href="patrocinadores.html">Patrocinadores</a></li><li><a href="reglamento.html">Reglamento</a></li>
        </ul></div>
        <div class="footer-col"><h4>Información</h4><ul>
          <li><a href="contacto.html">Inscribir equipo</a></li><li><a href="contacto.html">Contacto</a></li>
          <li><a href="admin.html">Panel Admin</a></li>
        </ul></div>
      </div>
      <div class="footer-bottom">
        <p>© 2026 Torneo CUP · Durango, México · Todos los derechos reservados</p>
        <p style="color:var(--gray-dark);font-size:0.7rem;">Diseñado con ⚽ en Durango</p>
      </div>
    </div>`;
  document.body.appendChild(footer);
}

function injectScrollTop() {
  const btn = document.createElement('button');
  btn.className = 'scroll-top'; btn.innerHTML = '↑'; btn.title = 'Volver arriba';
  document.body.appendChild(btn);
  window.addEventListener('scroll', () => btn.classList.toggle('visible', window.scrollY > 400));
  btn.addEventListener('click', () => window.scrollTo({ top:0, behavior:'smooth' }));
}

function showToast(msg, duration = 3000) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast'; toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

function startCountdown(targetDate, containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;
  function update() {
    const diff = new Date(targetDate) - new Date();
    if (diff <= 0) { container.innerHTML = `<span style="color:var(--gold);font-family:var(--font-display);font-size:2rem">¡EN VIVO!</span>`; return; }
    const d = Math.floor(diff / 86400000);
    const h = Math.floor((diff % 86400000) / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    container.innerHTML = `<div class="countdown-grid">${[['DÍAS',d],['HRS',h],['MIN',m],['SEG',s]].map(([l,n])=>`
      <div class="countdown-item">
        <div class="countdown-box">${String(n).padStart(2,'0')}</div>
        <div class="countdown-label">${l}</div>
      </div>`).join('')}</div>`;
  }
  update(); setInterval(update, 1000);
}

function animateCounters(selector = '[data-count]') {
  const els = document.querySelectorAll(selector);
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = parseInt(el.dataset.count);
      const duration = 1500; const start = Date.now();
      const tick = () => {
        const progress = Math.min((Date.now() - start) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(ease * target);
        if (progress < 1) requestAnimationFrame(tick);
      };
      tick(); observer.unobserve(el);
    });
  });
  els.forEach(el => observer.observe(el));
}

function initScrollReveal() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.1 });
  document.querySelectorAll('.fade-up').forEach(el => observer.observe(el));
}

function initShared() {
  injectLoader();
  injectNavbar();
  injectFooter();
  injectScrollTop();
  setTimeout(initScrollReveal, 100);
}

document.addEventListener('DOMContentLoaded', initShared);

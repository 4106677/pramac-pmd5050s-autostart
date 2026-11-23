// Control page of the generator unit (generator.yaml, web_server js_include). Languages: UA (default) / RU / EN.
// Talks to the stock ESPHome web API: SSE /events for states, POST /<domain>/<object_id>/<action>.
// Entities are found by their firmware NAME (sent once per connection): if a name changes in
// generator.yaml, change it in NAMES too.

const NAMES = {
  'Запуск вручную': 'manual', 'Внешний сигнал запуска': 'remote', 'Двигатель работает': 'engine',
  'Нагрузка подключена': 'load', 'Ошибка запуска': 'failed', 'Прогрев перед нагрузкой, с': 'warm',
  'Охлаждение перед остановкой, с': 'cool', 'Обороты двигателя': 'rpm', 'Моточасы': 'hours',
  'Уровень Wi-Fi': 'rssi', 'Плата работает': 'uptime', 'Состояние': 'status', 'IP-адрес': 'ip',
  'Сеть Wi-Fi': 'ssid', 'Версия прошивки': 'fw',
};

const T = {
  ru: {
    title: 'Генератор Pramac', online: 'На связи', offline: 'Нет связи', connecting: 'Подключение…',
    start: 'Запустить', again: 'Запустить снова', stop: 'Заглушить',
    cStart: 'Нажмите ещё раз, чтобы запустить', cStop: 'Нажмите ещё раз, чтобы заглушить',
    remoteNote: 'Работает по внешнему сигналу. Остановится, когда сигнал пропадёт.',
    ext: 'Внешний сигнал', yes: 'Есть', no: 'Нет', engine: 'Двигатель', engOn: 'Работает', engOff: 'Стоит',
    load: 'Нагрузка', loadOn: 'Подключена', loadOff: 'Отключена', hours: 'Моточасы', h: 'ч', min: 'мин', d: 'дн',
    settings: 'Настройки', warm: 'Прогрев', warmSub: 'перед подключением нагрузки', cool: 'Охлаждение',
    coolSub: 'перед остановкой', s: 'с', net: 'Сеть и плата', wifi: 'Wi-Fi', signal: 'Сигнал', ip: 'IP-адрес',
    uptime: 'Блок работает', fw: 'Прошивка', change: 'Сменить сеть Wi-Fi',
    failT: 'Не удалось завести за 3 попытки',
    failX: 'Проверьте топливо, аккумулятор и топливный кран. Затем нажмите «Запустить снова».',
    offT: 'Нет связи с блоком', offX: 'Проверьте, что телефон в той же сети Wi-Fi',
    st: {
      stopped: ['Остановлен', 'Ждёт сигнала запуска'], requested: ['Запрос на запуск', 'Готовится к запуску'],
      starting: ['Запуск', 'Включено зажигание'], cranking: ['Запуск', 'Стартер, попытка {n} из 3'],
      warmup: ['Прогрев', 'Нагрузка подключится после прогрева'],
      run_remote: ['Работает', 'По внешнему сигналу · нагрузка подключена'],
      run_manual: ['Работает', 'Запущен с телефона · нагрузка подключена'],
      running: ['Работает', 'Нагрузка не подключена'], running_free: ['Работает', 'Без запроса на запуск'],
      cooldown: ['Охлаждение', 'Нагрузка отключена, двигатель скоро остановится'],
      failed: ['Не завёлся', '3 попытки без результата'],
    },
  },
  uk: {
    title: 'Генератор Pramac', online: 'На зв’язку', offline: 'Немає зв’язку', connecting: 'Підключення…',
    start: 'Запустити', again: 'Запустити знову', stop: 'Заглушити',
    cStart: 'Натисніть ще раз, щоб запустити', cStop: 'Натисніть ще раз, щоб заглушити',
    remoteNote: 'Працює за зовнішнім сигналом. Зупиниться, коли сигнал зникне.',
    ext: 'Зовнішній сигнал', yes: 'Є', no: 'Немає', engine: 'Двигун', engOn: 'Працює', engOff: 'Стоїть',
    load: 'Навантаження', loadOn: 'Підключене', loadOff: 'Відключене', hours: 'Мотогодини', h: 'год', min: 'хв', d: 'дн',
    settings: 'Налаштування', warm: 'Прогрів', warmSub: 'перед підключенням навантаження', cool: 'Охолодження',
    coolSub: 'перед зупинкою', s: 'с', net: 'Мережа і плата', wifi: 'Wi-Fi', signal: 'Сигнал', ip: 'IP-адреса',
    uptime: 'Блок працює', fw: 'Прошивка', change: 'Змінити мережу Wi-Fi',
    failT: 'Не вдалося завести за 3 спроби',
    failX: 'Перевірте пальне, акумулятор і паливний кран. Потім натисніть «Запустити знову».',
    offT: 'Немає зв’язку з блоком', offX: 'Перевірте, що телефон у тій самій мережі Wi-Fi',
    st: {
      stopped: ['Зупинений', 'Чекає сигналу запуску'], requested: ['Запит на запуск', 'Готується до запуску'],
      starting: ['Запуск', 'Увімкнено запалювання'], cranking: ['Запуск', 'Стартер, спроба {n} з 3'],
      warmup: ['Прогрів', 'Навантаження підключиться після прогріву'],
      run_remote: ['Працює', 'За зовнішнім сигналом · навантаження підключене'],
      run_manual: ['Працює', 'Запущений з телефона · навантаження підключене'],
      running: ['Працює', 'Навантаження не підключене'], running_free: ['Працює', 'Без запиту на запуск'],
      cooldown: ['Охолодження', 'Навантаження відключене, двигун скоро зупиниться'],
      failed: ['Не завівся', '3 спроби без результату'],
    },
  },
  en: {
    title: 'Pramac Generator', online: 'Connected', offline: 'Offline', connecting: 'Connecting…',
    start: 'Start', again: 'Try again', stop: 'Stop',
    cStart: 'Tap again to start', cStop: 'Tap again to stop',
    remoteNote: 'Running on the external signal. It stops when the signal goes away.',
    ext: 'External signal', yes: 'On', no: 'Off', engine: 'Engine', engOn: 'Running', engOff: 'Stopped',
    load: 'Load', loadOn: 'Connected', loadOff: 'Disconnected', hours: 'Engine hours', h: 'h', min: 'min', d: 'd',
    settings: 'Settings', warm: 'Warm-up', warmSub: 'before connecting the load', cool: 'Cool-down',
    coolSub: 'before stopping', s: 's', net: 'Network & board', wifi: 'Wi-Fi', signal: 'Signal', ip: 'IP address',
    uptime: 'Uptime', fw: 'Firmware', change: 'Change Wi-Fi network',
    failT: 'Failed to start after 3 attempts',
    failX: 'Check the fuel, the battery and the fuel valve, then tap “Try again”.',
    offT: 'No connection to the unit', offX: 'Make sure the phone is on the same Wi-Fi network',
    st: {
      stopped: ['Stopped', 'Waiting for a start signal'], requested: ['Start requested', 'Getting ready to start'],
      starting: ['Starting', 'Ignition on'], cranking: ['Starting', 'Starter, attempt {n} of 3'],
      warmup: ['Warming up', 'The load connects after warm-up'],
      run_remote: ['Running', 'External signal · load connected'],
      run_manual: ['Running', 'Started from the phone · load connected'],
      running: ['Running', 'Load not connected'], running_free: ['Running', 'No start request'],
      cooldown: ['Cooling down', 'Load disconnected, the engine stops soon'],
      failed: ['Did not start', '3 attempts failed'],
    },
  },
};
const LANGS = [['uk', 'UA'], ['ru', 'RU'], ['en', 'EN']];
const LOCALE = { ru: 'ru-RU', uk: 'uk-UA', en: 'en-US' };

// firmware status text (Russian, also shown in Home Assistant) -> [key, tone, pulsing]
const STATUS = {
  'Остановлен, ожидание': ['stopped', 'grey'], 'Запрос на запуск': ['requested', 'amber', 1],
  'Запуск': ['starting', 'amber', 1], 'Прогрев перед нагрузкой': ['warmup', 'amber', 1],
  'Работает по внешнему сигналу': ['run_remote', 'green'], 'Работает, запущен вручную': ['run_manual', 'green'],
  'Работает': ['running', 'green'], 'Работает без запроса': ['running_free', 'green'],
  'Охлаждение перед остановкой': ['cooldown', 'blue', 1], 'Не удалось завести': ['failed', 'red'],
};
const ACTIVE = ['requested', 'starting', 'cranking', 'warmup', 'run_remote', 'run_manual', 'running', 'running_free'];

const I = {
  plug: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 2v6M15 2v6M6 8h12v3a6 6 0 0 1-12 0V8zM12 17v5"/></svg>',
  engine: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M4 9h3V7h6v2h3l2 2h2v6h-2l-2 2H7l-3-3z"/><path d="M8 4h6M11 4v3"/></svg>',
  load: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  alert: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17v.5"/></svg>',
};
const TONES = { green: 'green', amber: 'amber', red: 'red', grey: 'grey', blue: 'blue' };

let lang = pickLang();
const S = {};          // key -> last JSON event of that entity
const byId = {};       // "sensor-xxx" -> key
let lastSeen = 0, everSeen = false, confirmTimer = null, pending = {}, sendTimer = {};
const open = { settings: false, net: false };

// українська за замовчуванням; інша мова — лише якщо її вибрали перемикачем
function pickLang() {
  try { const l = localStorage.getItem('gen-lang'); if (T[l]) return l; } catch (e) { /* private mode */ }
  return 'uk';
}
const t = (k) => T[lang][k];
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = (k) => (S[k] ? parseFloat(S[k].value) : NaN);
const on = (k) => !!(S[k] && S[k].value === true);
const fmt = (v, d) => v.toLocaleString(LOCALE[lang], { minimumFractionDigits: d, maximumFractionDigits: d });
const bars = (n) => '<span class="bars">' + [6, 9, 12, 14].map((h, i) => `<i style="height:${h}px" class="${i < n ? 'f' : ''}"></i>`).join('') + '</span>';
const rssiBars = (r) => (r > -55 ? 4 : r > -65 ? 3 : r > -75 ? 2 : 1);

/* ---------- RPM gauge ---------- */
const MAX = 4000, CX = 150, CY = 150, R = 118;
const ZONES = [[0, 1000, 'var(--grey)'], [1000, 2800, 'var(--amber)'], [2800, 3200, 'var(--green)'], [3200, 4000, 'var(--red)']];
const ang = (v) => Math.PI * (1 - Math.min(Math.max(v, 0), MAX) / MAX);
const pt = (v, r = R) => [CX + r * Math.cos(ang(v)), CY - r * Math.sin(ang(v))];
const arc = (a, b, r = R) => { const [x1, y1] = pt(a, r), [x2, y2] = pt(b, r); return `M${x1.toFixed(1)} ${y1.toFixed(1)} A${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`; };
function gaugeSVG() {
  let s = '<svg class="gauge" viewBox="0 0 300 172">';
  s += `<path d="${arc(0, MAX)}" stroke="var(--track)" stroke-width="18" fill="none" stroke-linecap="round"/>`;
  for (const [a, b, c] of ZONES) s += `<path d="${arc(a + 12, b - 12, R + 17)}" stroke="${c}" stroke-width="4" fill="none" stroke-linecap="round" opacity=".55"/>`;
  s += '<path id="g-arc" d="" stroke-width="18" fill="none" stroke-linecap="round"/>';
  for (const v of [0, 1000, 2000, 3000, 4000]) { const [x, y] = pt(v, R - 28); s += `<text class="tick" x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="middle">${v ? v / 1000 + 'k' : 0}</text>`; }
  s += `<circle id="g-knob" class="knob" r="6" fill="var(--card)" stroke="var(--ink)" stroke-width="3" cx="${CX - R}" cy="${CY}" opacity="0"/>`;
  s += '<text class="val" id="g-val" x="150" y="138" text-anchor="middle">–</text>';
  s += '<text class="unit" x="150" y="162" text-anchor="middle">RPM</text></svg>';
  return s;
}
function setGauge(v) {
  const ok = !isNaN(v), x = ok ? Math.max(0, v) : 0;
  const a = $('#g-arc');
  a.setAttribute('d', x > 30 ? arc(0, Math.min(x, MAX)) : '');
  a.setAttribute('stroke', (ZONES.find((z) => x < z[1]) || ZONES[3])[2]);
  const [kx, ky] = pt(x), k = $('#g-knob');
  k.setAttribute('cx', kx.toFixed(1)); k.setAttribute('cy', ky.toFixed(1)); k.setAttribute('opacity', x > 30 ? 1 : 0);
  $('#g-val').textContent = ok ? Math.round(x) : '–';
}

/* ---------- page ---------- */
function build() {
  document.documentElement.lang = lang === 'uk' ? 'uk' : lang;
  document.title = t('title');
  const tile = (id, icon, k) => `<div class="card tile" id="${id}"><div class="ic">${icon}</div><div style="min-width:0"><div class="k">${k}</div><div class="v"></div></div></div>`;
  const stepper = (k) => `<div class="row"><div class="k">${t(k)}<small>${t(k + 'Sub')}</small></div>
    <div class="step"><button data-k="${k}" data-d="-1" aria-label="-">−</button><output id="o-${k}">–</output><button data-k="${k}" data-d="1" aria-label="+">+</button></div></div>`;
  let root = $('#gen');
  if (!root) { root = document.createElement('div'); root.id = 'gen'; root.className = 'wrap'; document.body.appendChild(root); }
  root.innerHTML = `<div class="app" id="app">
    <div class="top"><b>${t('title')}</b><span class="pill" id="pill"><i></i><span></span></span></div>
    <div class="card hero" id="hero"><div class="st"><span class="dot"></span><h2 id="st-t"></h2></div><div class="sub" id="st-s"></div>${gaugeSVG()}</div>
    <div class="banner hidden" id="fail">${I.alert}<div><b>${t('failT')}</b><span>${t('failX')}</span></div></div>
    <button class="big" id="act"></button>
    <div class="note hidden" id="note"></div>
    <div class="grid">${tile('t-remote', I.plug, t('ext'))}${tile('t-engine', I.engine, t('engine'))}${tile('t-load', I.load, t('load'))}${tile('t-hours', I.clock, t('hours'))}</div>
    <details class="card" id="d-settings"${open.settings ? ' open' : ''}><summary>${t('settings')}</summary><div class="rows">${stepper('warm')}${stepper('cool')}</div></details>
    <details class="card" id="d-net"${open.net ? ' open' : ''}><summary>${t('net')}</summary><div class="rows">
      <div class="row"><div class="k">${t('wifi')}</div><div class="v" id="n-ssid">–</div></div>
      <div class="row"><div class="k">${t('signal')}</div><div class="v" id="n-rssi">–</div></div>
      <div class="row"><div class="k">${t('ip')}</div><div class="v" id="n-ip">–</div></div>
      <div class="row"><div class="k">${t('uptime')}</div><div class="v" id="n-up">–</div></div>
      <div class="row"><div class="k">${t('fw')}</div><div class="v" id="n-fw">–</div></div>
      <div class="row"><a href="/wifi">${t('change')} ›</a></div></div></details>
    <div class="foot"><span class="langs">${LANGS.map(([c, l]) => `<button data-l="${c}" class="${c === lang ? 'on' : ''}">${l}</button>`).join('')}</span></div>
  </div>`;
  $('#d-settings').ontoggle = (e) => { open.settings = e.target.open; };
  $('#d-net').ontoggle = (e) => { open.net = e.target.open; };
  root.querySelectorAll('.langs button').forEach((b) => (b.onclick = () => {
    lang = b.dataset.l; try { localStorage.setItem('gen-lang', lang); } catch (e) { /* ignore */ }
    build();
  }));
  root.querySelectorAll('.step button').forEach((b) => (b.onclick = () => step(b.dataset.k, +b.dataset.d)));
  $('#act').onclick = act;
  render();
}

function status() {
  const raw = S.status ? String(S.status.value) : '';
  const m = raw.match(/^Стартер, попытка (\d)/);
  if (m) return { key: 'cranking', tone: 'amber', pulse: 1, n: m[1] };
  const s = STATUS[raw];
  if (s) return { key: s[0], tone: s[1], pulse: s[2] };
  return { key: on('engine') ? 'running' : 'stopped', tone: on('engine') ? 'green' : 'grey' };
}

function render() {
  if (!$('#app')) return;
  const online = Date.now() - lastSeen < 10000;
  const st = status();
  $('#app').classList.toggle('offline', !online);
  const pill = $('#pill');
  pill.classList.toggle('off', !online);
  pill.lastChild.textContent = online ? t('online') : everSeen ? t('offline') : t('connecting');

  const hero = $('#hero'), tone = TONES[st.tone];
  hero.style.setProperty('--tone', `var(--${tone})`);
  hero.style.setProperty('--tone-bg', `var(--${tone}-bg)`);
  hero.classList.toggle('pulse', !!st.pulse && online);
  const [title, sub] = !online && everSeen ? [t('offT'), t('offX')] : !everSeen ? [t('connecting'), ''] : t('st')[st.key];
  $('#st-t').textContent = title;
  $('#st-s').textContent = sub.replace('{n}', st.n || '');
  setGauge(online ? num('rpm') : NaN);

  const failed = on('failed') || st.key === 'failed';
  $('#fail').classList.toggle('hidden', !failed || !online);

  const btn = $('#act'), note = $('#note');
  const active = ACTIVE.includes(st.key);
  const lockedByRemote = on('remote') && !failed;
  if (!btn.classList.contains('confirm')) {
    btn.dataset.mode = active ? 'stop' : 'start';
    btn.textContent = active || lockedByRemote ? t('stop') : failed ? t('again') : t('start');
    btn.classList.toggle('stop', active && !lockedByRemote);
  }
  btn.disabled = !online || lockedByRemote;
  note.textContent = t('remoteNote');
  note.classList.toggle('hidden', !(online && lockedByRemote));

  setTile('t-remote', on('remote'), on('remote') ? t('yes') : t('no'), 'blue');
  setTile('t-engine', on('engine'), on('engine') ? t('engOn') : t('engOff'), 'green');
  setTile('t-load', on('load'), on('load') ? t('loadOn') : t('loadOff'), 'amber');
  const hrs = num('hours');
  setTile('t-hours', false, isNaN(hrs) ? '–' : `${fmt(hrs, 1)} ${t('h')}`, 'grey');

  for (const k of ['warm', 'cool']) {
    const v = pending[k] !== undefined ? pending[k] : num(k);
    $('#o-' + k).textContent = isNaN(v) ? '–' : `${v} ${t('s')}`;
  }
  const rssi = num('rssi');
  $('#n-ssid').textContent = (S.ssid && S.ssid.value) || '–';
  $('#n-rssi').innerHTML = isNaN(rssi) ? '–' : `${bars(rssiBars(rssi))}${Math.round(rssi)} dBm`;
  $('#n-ip').textContent = (S.ip && S.ip.value) || '–';
  $('#n-up').textContent = uptime(num('uptime'));
  $('#n-fw').textContent = (S.fw && S.fw.value) || '–';
}

function setTile(id, isOn, text, tone) {
  const el = document.getElementById(id);
  el.classList.toggle('on', isOn);
  el.style.setProperty('--t', `var(--${tone})`);
  el.style.setProperty('--t-bg', `var(--${tone}-bg)`);
  el.querySelector('.v').textContent = text;
}

function uptime(m) {
  if (isNaN(m)) return '–';
  m = Math.floor(m);
  const d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), mm = m % 60;
  if (d) return `${d} ${t('d')} ${h} ${t('h')}`;
  if (h) return `${h} ${t('h')} ${mm} ${t('min')}`;
  return `${mm} ${t('min')}`;
}

function post(key, action) {
  const id = S[key] && S[key].id;
  if (!id) return Promise.resolve();
  const dash = id.indexOf('-');
  return fetch(`/${id.slice(0, dash)}/${id.slice(dash + 1)}/${action}`, { method: 'POST' }).catch(() => {});
}

function act() {
  const btn = $('#act'), stop = btn.dataset.mode === 'stop';
  if (!btn.classList.contains('confirm')) {
    btn.classList.add('confirm');
    btn.classList.remove('stop');
    btn.textContent = stop ? t('cStop') : t('cStart');
    clearTimeout(confirmTimer);
    confirmTimer = setTimeout(() => { btn.classList.remove('confirm'); render(); }, 3000);
    return;
  }
  clearTimeout(confirmTimer);
  btn.classList.remove('confirm');
  post('manual', stop ? 'turn_off' : 'turn_on');
  render();
}

function step(k, dir) {
  const e = S[k];
  if (!e) return;
  const stp = parseFloat(e.step) || 5, lo = parseFloat(e.min_value), hi = parseFloat(e.max_value);
  const cur = pending[k] !== undefined ? pending[k] : num(k);
  pending[k] = Math.min(hi, Math.max(lo, (isNaN(cur) ? lo : cur) + dir * stp));
  render();
  clearTimeout(sendTimer[k]);
  sendTimer[k] = setTimeout(() => {
    post(k, `set?value=${pending[k]}`).then(() => setTimeout(() => { delete pending[k]; render(); }, 1500));
  }, 600);
}

/* ---------- live data ---------- */
let raf = 0;
const later = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; render(); }); };
let es = null, esStarted = 0;
function connect() {
  if (es) es.close();
  esStarted = Date.now();
  es = new EventSource('/events');
  es.addEventListener('state', (ev) => {
    let d;
    try { d = JSON.parse(ev.data); } catch (e) { return; }
    let k = byId[d.id];
    if (!k && d.name && NAMES[d.name]) k = byId[d.id] = NAMES[d.name];
    if (!k) return;
    S[k] = Object.assign(S[k] || {}, d);
    lastSeen = Date.now(); everSeen = true;
    later();
  });
  es.addEventListener('ping', () => { lastSeen = Date.now(); });
  es.onerror = () => later();
}

// ESPHome's index page has no viewport tag: without it phones render the page at desktop width.
if (!document.querySelector('meta[name=viewport]')) {
  const vp = document.createElement('meta');
  vp.name = 'viewport';
  vp.content = 'width=device-width,initial-scale=1';
  document.head.appendChild(vp);
}
build();
connect();
setInterval(() => {
  // a phone that slept or changed networks can keep a dead stream open: reconnect after 12 s of silence
  if (Date.now() - Math.max(lastSeen, esStarted) > 12000) connect();
  render();
}, 2000);

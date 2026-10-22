import { createGMPlugin } from './vendor/gm-plugin-web-sdk.esm.js';
import { SoundPlayer } from './sounds.js';
import {
  ACTIVE, EXERCISES, STORAGE_KEY, STYLES, addDays, applySession, dateKey, decodeGlassesMessage,
  emptyData, encodeCals, encodeSetup, encodeStats, normalize, summary,
} from './stats.js';

const PHONE_TO_GLASSES = 0x4647;
const GLASSES_TO_PHONE = 0x4648;

const gm = createGMPlugin();
const $ = (id) => document.getElementById(id);
const statusEl = $('status');
let data = emptyData();
let ready = false;
let view = 0;            // exercise shown on this screen (follows the glasses)
let saveChain = Promise.resolve();
const sounds = new SoundPlayer({ onStatus: (state) => setSoundStatus(state) });

function setSoundStatus(state) {
  const el = $('sound-status');
  const text = {
    locked: 'Sound is off until you tap — use the button at the top.',
    ready: 'Sound is on. Keep this page open during workouts.',
    playing: 'Sound is on. Keep this page open during workouts.',
    error: 'This phone won\u2019t play sound here. Check the phone isn\u2019t muted or on silent, and that Workout Tracker is allowed audio playback in the MemoMind app.',
    off: 'Sounds are off.',
  }[state];
  if (text) el.textContent = text;
  el.className = `sub${state === 'locked' || state === 'error' ? ' warn' : ''}`;
  // the big "tap to turn on sound" banner shows until audio is really unlocked
  $('sound-banner').hidden = !(data.sound && (state === 'locked' || (state !== 'off' && !sounds.unlocked)));
}

// The App suspends hidden plugin pages, which stops sound and syncing. Ask
// the phone to keep the screen on while this page is open (where supported).
let wakeLock = null;
async function keepAwake() {
  try {
    if (!document.hidden && navigator.wakeLock && !wakeLock) {
      wakeLock = await navigator.wakeLock.request('screen');
      wakeLock.addEventListener?.('release', () => { wakeLock = null; });
    }
  } catch {
    wakeLock = null;   // not supported or not allowed: nothing else to do
  }
}

function setStatus(text, state = '') {
  statusEl.querySelector('span').textContent = text;
  statusEl.className = `status ${state}`.trim();
}

function prettyDate(key, withYear = false) {
  if (!key) return '';
  const [y, m, d] = key.split('-').map(Number);
  const opts = { month: 'short', day: 'numeric' };
  if (withYear) opts.year = 'numeric';
  return new Date(y, m - 1, d).toLocaleDateString(undefined, opts);
}

function renderStyles() {
  const box = $('styles');
  if (!box.childElementCount) {
    for (const style of STYLES) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'style';
      button.dataset.style = String(style.id);
      const img = document.createElement('img');
      img.src = style.img;
      img.alt = '';
      const name = document.createElement('strong');
      name.textContent = style.name;
      const blurb = document.createElement('small');
      blurb.textContent = style.blurb;
      button.append(img, name, blurb);
      button.addEventListener('click', () => {
        sounds.preview(style.id);
        if (data.style === style.id) return;
        data.style = style.id;
        void save();
        renderStyles();
        void sendStats();
      });
      box.append(button);
    }
  }
  for (const button of box.children) {
    const selected = Number(button.dataset.style) === data.style;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  }
}

function renderSound() {
  const toggle = $('sound');
  toggle.setAttribute('aria-checked', String(data.sound));
  toggle.querySelector('span').textContent = data.sound ? 'On' : 'Off';
  sounds.enabled = data.sound;
  $('test-sound').hidden = !data.sound;
  if (!data.sound) setSoundStatus('off');
  else setSoundStatus(sounds.unlocked ? 'ready' : 'locked');
}


const SETUP_TEXT = {
  0: 'one slow, full sit-up (lie down first)',
  3: 'three jumping jacks',
  5: 'touch your toes, then reach for the sky',
};

function calText(exId, cal) {
  if (!cal) return ['Not set up', `First time, your glasses ask for ${SETUP_TEXT[exId]}.`];
  const when = cal.date ? ` · measured ${prettyDate(cal.date)}` : '';
  switch (exId) {
    case 0:
      return [`${cal.a}° range`, `A rep counts at ${Math.round(cal.a * 0.6)}°${when}`];
    case 5:
      return [`${cal.a}° down · ${cal.b}° up`, `Counts a toe touch + sky reach${when}`];
    default:
      return ['Set up', `${cal.c} bump${cal.c === 1 ? '' : 's'} per jack${when}`];
  }
}

function renderTabs() {
  const box = $('tabs');
  if (!box.childElementCount) {
    for (const id of ACTIVE) {
      const e = EXERCISES[id];
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'tab';
      b.dataset.ex = String(e.id);
      b.textContent = e.short;
      b.addEventListener('click', () => { view = e.id; render(); });
      box.append(b);
    }
  }
  for (const b of box.children) {
    const id = Number(b.dataset.ex);
    b.classList.toggle('selected', id === view);
    b.classList.toggle('live', id === data.current);
    b.setAttribute('aria-pressed', String(id === view));
  }
}

function render() {
  renderTabs();
  renderStyles();
  renderSound();
  const today = dateKey();
  const s = summary(data, view, today);
  const name = EXERCISES[view].name;
  const days = data.ex[view].days;

  $('today-label').textContent = `${name} today`;
  $('today').textContent = s.today;
  $('today-note').textContent = s.todayAll > s.today
    ? `${s.todayAll} reps across all workouts today`
    : s.todayAll > 0 ? 'Nice work — keep it going'
      : (s.streak > 0 ? 'Do any workout today to keep your streak!' : 'No reps yet today');
  $('today-note').className = `sub${s.todayAll === 0 && s.streak > 0 ? ' warn' : ''}`;

  $('streak').textContent = s.streak;
  $('streak-note').textContent = `${s.streak === 1 ? 'day' : 'days'} in a row · any workout`;

  $('best').textContent = s.best.reps > 0 ? s.best.reps : '—';
  $('best-date').textContent = s.best.reps > 0 ? `on ${prettyDate(s.best.date, true)}` : 'one session';

  const [calMain, calNote] = calText(view, s.cal);
  $('range-label').textContent = `${name} setup`;
  $('range').textContent = calMain;
  $('range-note').textContent = calNote;

  $('total').textContent = s.total;
  $('total-label').textContent = `All-time ${name.toLowerCase()}`;
  $('best-day').textContent = s.bestDay ? `${s.bestDay.reps} · ${prettyDate(s.bestDay.date)}` : '—';
  $('longest').textContent = `${s.longest} day${s.longest === 1 ? '' : 's'}`;
  $('active').textContent = `${s.grand} reps`;

  const chart = $('chart');
  chart.textContent = '';
  $('chart-label').textContent = `${name} · last 14 days`;
  const range = [];
  for (let i = 13; i >= 0; i -= 1) range.push(addDays(today, -i));
  const max = Math.max(1, ...range.map((d) => days[d] || 0));
  for (const d of range) {
    const reps = days[d] || 0;
    const bar = document.createElement('div');
    bar.className = `bar${reps > 0 ? ' has' : ''}${d === today ? ' today' : ''}`;
    bar.title = `${prettyDate(d)}: ${reps} reps`;
    const fill = document.createElement('i');
    fill.style.height = `${Math.round((reps / max) * 100)}%`;
    const label = document.createElement('span');
    label.textContent = Number(d.slice(8));
    bar.append(fill, label);
    chart.append(bar);
  }
}

function save() {
  const snapshot = JSON.parse(JSON.stringify(data));
  saveChain = saveChain
    .then(() => gm.storage.set(STORAGE_KEY, snapshot))
    .catch((error) => setStatus(`Save failed: ${error.message || error}`, 'bad'));
  return saveChain;
}

async function send(bytes) {
  if (!ready) return;
  try {
    await gm.plugin.sendMessage(PHONE_TO_GLASSES, bytes);
  } catch {
    // Glasses not connected or plugin not running yet; they say HELLO when
    // they start, and we answer then.
  }
}

const sendStats = () => send(encodeStats(data, data.current));
const sendCals = () => send(encodeCals(data));

gm.plugin.onMessage(({ channel, data: bytes }) => {
  if (channel !== GLASSES_TO_PHONE) return;
  const message = decodeGlassesMessage(bytes);
  if (!message) return;
  setStatus('Glasses connected', 'ok');
  switch (message.type) {
    case 'event':
      // A sound cue from the glasses; it names the style it was sent from.
      sounds.playEvent(message.style, message.event, message.value);
      return; // no reply needed
    case 'hello':
    case 'exercise':
      if (data.current !== message.ex) { data.current = message.ex; void save(); }
      view = message.ex;
      render();
      if (message.type === 'hello') void sendCals();
      break;
    case 'session':
      if (data.current !== message.ex) { data.current = message.ex; view = message.ex; }
      if (applySession(data, message.id, message.reps, message.ex)) { void save(); render(); }
      break;
    case 'cal':
      // Setup finished on the glasses: keep it so it only happens once.
      data.ex[message.ex].cal = { a: message.a, b: message.b, c: message.c, date: dateKey() };
      void save();
      render();
      $('recalibrate').disabled = false;
      $('recalibrate').textContent = 'Recalibrate';
      break;
    case 'style':
      if (data.style !== message.style) { data.style = message.style; void save(); renderStyles(); }
      break;
    default:
      return;
  }
  // Answer HELLO / EXERCISE, and acknowledge every SESSION so the glasses
  // stop resending.
  void sendStats();
});

$('sound').addEventListener('click', () => {
  data.sound = !data.sound;
  void save();
  renderSound();
  if (data.sound) { sounds.unlock(); sounds.preview(data.style); }
});

$('test-sound').addEventListener('click', async () => {
  sounds.unlock();
  await sounds.decodeAll();
  sounds.preview(data.style);
});

$('sound-banner').addEventListener('click', async () => {
  sounds.unlock();
  await sounds.decodeAll();
  sounds.preview(data.style);   // confirm with a sound
});

// Phones only allow sound after a tap: try on every tap until it works.
document.addEventListener('pointerdown', () => {
  if (data.sound && !sounds.unlocked) sounds.unlock();
  void keepAwake();
});

$('recalibrate').addEventListener('click', async () => {
  const button = $('recalibrate');
  try {
    if (!ready) throw new Error('not ready');
    await gm.plugin.sendMessage(PHONE_TO_GLASSES, encodeSetup(view));
    button.textContent = 'Follow your glasses…';
    button.disabled = true;
    setTimeout(() => { button.disabled = false; button.textContent = 'Recalibrate'; }, 60_000);
  } catch {
    button.textContent = 'Glasses not connected';
    setTimeout(() => { button.textContent = 'Recalibrate'; }, 3000);
  }
});

$('reset').addEventListener('click', () => {
  const button = $('reset');
  if (button.dataset.armed !== '1') {
    button.dataset.armed = '1';
    button.textContent = 'Tap again to erase all history';
    setTimeout(() => { button.dataset.armed = ''; button.textContent = 'Reset all history'; }, 4000);
    return;
  }
  button.dataset.armed = '';
  button.textContent = 'Reset all history';
  // Keep settings and setups; erase reps, high scores and streak.
  const fresh = emptyData();
  for (const e of EXERCISES) fresh.ex[e.id].cal = data.ex[e.id].cal;
  Object.assign(fresh, { style: data.style, sound: data.sound, current: data.current });
  data = fresh;
  void save();
  render();
  void sendStats();
});

async function start() {
  render();
  try {
    await gm.ready();
    ready = true;
    const stored = await gm.storage.get(STORAGE_KEY);
    data = normalize(stored && stored.value);
    view = data.current;
    render();
    try {
      const info = await gm.device.getInfo();
      setStatus(info.connected ? 'Glasses connected' : 'Glasses not connected', info.connected ? 'ok' : 'bad');
    } catch {
      setStatus('Ready');
    }
    try {
      await gm.device.subscribeEvents(['connection']);
      gm.device.onConnection((event) => {
        setStatus(event.connected ? 'Glasses connected' : 'Glasses not connected', event.connected ? 'ok' : 'bad');
        if (event.connected) { void sendCals(); void sendStats(); }
      });
    } catch {
      // Optional permission denied: messages still work.
    }
    await sendCals();
    await sendStats();
    void keepAwake();
  } catch (error) {
    setStatus(error.message || String(error), 'bad');
  }
}

// Refresh "today" and the streak when the date rolls over or the app returns.
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) { render(); void keepAwake(); }
});
setInterval(render, 60_000);
window.addEventListener('pagehide', () => { sounds.stopAll(); gm.close(); });

void start();

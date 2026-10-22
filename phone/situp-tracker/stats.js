// Data logic for Workout Tracker (no Bridge calls, easy to test).
// Protocol "fox89.workout-sync" 2.0 — see situp_counter.c on the glasses.

export const STORAGE_KEY = 'situp-data';   // kept so existing history carries over
export const PROTO = 2;

// Ids match the glasses. Push-ups, squats and hip twists were retired (a head
// sensor can't measure them reliably); their ids stay so old data lines up.
export const EXERCISES = [
  { id: 0, name: 'Sit-ups', short: 'Sit-ups', active: true },
  { id: 1, name: 'Push-ups', short: 'Push-ups', active: false },
  { id: 2, name: 'Squats', short: 'Squats', active: false },
  { id: 3, name: 'Jumping jacks', short: 'Jacks', active: true },
  { id: 4, name: 'Hip twists', short: 'Twists', active: false },
  { id: 5, name: 'Toe & sky touches', short: 'Toe & sky', active: true },
];
export const ACTIVE = [0, 5, 3];   // same order as the glasses menu
export const isActive = (id) => ACTIVE.includes(id);

export const STYLES = [
  { id: 2, name: 'Stick Figure', img: 'img/style-figure.png', blurb: 'Does every exercise with you' },
  { id: 1, name: 'Coach Head', img: 'img/style-head.png', blurb: 'Sweats with you' },
  { id: 3, name: 'Glow-Up', img: 'img/style-glowup.png', blurb: 'Evolves at 10, 25, 50' },
  { id: 4, name: 'Aura', img: 'img/style-aura.png', blurb: '+100 aura per rep' },
  { id: 5, name: 'Judgy Cat', img: 'img/style-cat.png', blurb: 'Hard to impress' },
  { id: 6, name: 'Stonks', img: 'img/style-stonks.png', blurb: 'Gains go up' },
  { id: 0, name: 'Ring', img: 'img/style-ring.png', blurb: 'Fills as you rise' },
];
export const DEFAULT_STYLE = 2;   // stick figure

function emptyExercise() {
  return { days: {}, best: { reps: 0, date: null }, cal: null };
}

export function emptyData() {
  const ex = {};
  for (const e of EXERCISES) ex[e.id] = emptyExercise();
  return { version: 2, ex, sessions: {}, style: DEFAULT_STYLE, sound: true, current: 0 };
}

export function dateKey(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function addDays(key, delta) {
  const [y, m, d] = key.split('-').map(Number);
  return dateKey(new Date(y, m - 1, d + delta));
}

const isDay = (k) => /^\d{4}-\d{2}-\d{2}$/.test(k);
const posInt = (v) => Math.max(0, Math.floor(Number(v) || 0));

function readDays(raw) {
  const days = {};
  if (raw && typeof raw === 'object') {
    for (const [k, v] of Object.entries(raw)) if (isDay(k) && posInt(v) > 0) days[k] = posInt(v);
  }
  return days;
}

function readBest(raw) {
  return raw && posInt(raw.reps) > 0
    ? { reps: posInt(raw.reps), date: String(raw.date || '') || null }
    : { reps: 0, date: null };
}

function readCal(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const a = posInt(raw.a), b = posInt(raw.b), c = posInt(raw.c);
  if (a < 1 || a > 65535 || b > 65535 || c > 255) return null;
  return { a, b, c, date: String(raw.date || '') || null };
}

// Accepts version-1 data (sit-ups only) and upgrades it: nothing is lost.
export function normalize(raw) {
  const data = emptyData();
  if (!raw || typeof raw !== 'object') return data;
  if (raw.version === 2 && raw.ex && typeof raw.ex === 'object') {
    for (const e of EXERCISES) {
      const src = raw.ex[e.id];
      if (!src) continue;
      data.ex[e.id] = { days: readDays(src.days), best: readBest(src.best), cal: readCal(src.cal) };
    }
    if (isActive(Number(raw.current))) data.current = Number(raw.current);
  } else {
    // version 1: everything was sit-ups
    const sit = data.ex[0];
    sit.days = readDays(raw.days);
    sit.best = readBest(raw.best);
    const deg = posInt(raw.range?.degrees);
    if (deg >= 15 && deg <= 255) sit.cal = { a: deg, b: 0, c: 0, date: String(raw.range.date || '') || null };
  }
  if (raw.sessions && typeof raw.sessions === 'object') {
    for (const [id, s] of Object.entries(raw.sessions)) {
      if (s && typeof s.date === 'string') {
        data.sessions[id] = { date: s.date, reps: posInt(s.reps), at: Number(s.at) || 0,
          ex: EXERCISES.some((e) => e.id === Number(s.ex)) ? Number(s.ex) : 0 };
      }
    }
  }
  const style = Number(raw.style);
  if (STYLES.some((s) => s.id === style)) data.style = style;
  if (raw.sound === false) data.sound = false;
  return data;
}

// One SESSION update from the glasses. Updates are idempotent: the glasses
// always send the running total, so a resend never double-counts.
export function applySession(data, sessionId, reps, exId, today = dateKey(), now = Date.now()) {
  const id = String(sessionId >>> 0);
  const ex = data.ex[exId] ? exId : 0;
  let session = data.sessions[id];
  if (!session) {
    session = { date: today, reps: 0, at: now, ex };
    data.sessions[id] = session;
  }
  if (reps <= session.reps) return false;
  const e = data.ex[session.ex];
  const delta = reps - session.reps;
  session.reps = reps;
  session.at = now;
  e.days[session.date] = (e.days[session.date] || 0) + delta;
  if (reps > e.best.reps) e.best = { reps, date: session.date };
  const cutoff = addDays(today, -2);
  for (const [key, s] of Object.entries(data.sessions)) if (s.date < cutoff) delete data.sessions[key];
  return true;
}

export function latestSession(data) {
  let best = null;
  for (const [id, s] of Object.entries(data.sessions)) {
    if (!best || s.at > best.at) best = { id: Number(id) >>> 0, ...s };
  }
  return best;
}

// Reps per day across every exercise (for the shared workout streak).
export function allDays(data) {
  const out = {};
  for (const e of EXERCISES) {
    for (const [k, v] of Object.entries(data.ex[e.id].days)) out[k] = (out[k] || 0) + v;
  }
  return out;
}

// Days in a row with any workout. If today has nothing yet the streak is
// still alive and counts back from yesterday.
export function currentStreak(days, today = dateKey()) {
  let day = (days[today] || 0) > 0 ? today : addDays(today, -1);
  let streak = 0;
  while ((days[day] || 0) > 0) { streak += 1; day = addDays(day, -1); }
  return streak;
}

export function longestStreak(days) {
  const keys = Object.keys(days).filter((k) => days[k] > 0).sort();
  let longest = 0, run = 0, prev = null;
  for (const k of keys) {
    run = prev && addDays(prev, 1) === k ? run + 1 : 1;
    longest = Math.max(longest, run);
    prev = k;
  }
  return longest;
}

export function summary(data, exId, today = dateKey()) {
  const e = data.ex[exId];
  const all = allDays(data);
  let total = 0, bestDay = null, grand = 0;
  for (const [k, v] of Object.entries(e.days)) {
    total += v;
    if (!bestDay || v > bestDay.reps) bestDay = { date: k, reps: v };
  }
  for (const v of Object.values(all)) grand += v;
  return {
    today: e.days[today] || 0,
    todayAll: all[today] || 0,
    streak: currentStreak(all, today),
    longest: longestStreak(all),
    total, grand,
    activeDays: Object.keys(all).length,
    bestDay, best: e.best, cal: e.cal,
  };
}

// STATS for one exercise (20 bytes, see situp_counter.c).
export function encodeStats(data, exId, today = dateKey()) {
  const s = summary(data, exId, today);
  const latest = latestSession(data);
  const buf = new Uint8Array(20);
  const view = new DataView(buf.buffer);
  const clamp16 = (n) => Math.max(0, Math.min(0xffff, n | 0));
  buf[0] = PROTO;
  buf[1] = 3;
  view.setUint16(2, clamp16(s.best.reps), true);
  if (s.best.date) {
    const [y, m, d] = s.best.date.split('-').map(Number);
    view.setUint16(4, clamp16(y), true);
    buf[6] = m;
    buf[7] = d;
  }
  view.setUint16(8, clamp16(s.streak), true);
  view.setUint16(10, clamp16(s.today), true);
  if (latest) {
    view.setUint32(12, latest.id >>> 0, true);
    view.setUint16(16, clamp16(latest.reps), true);
  }
  buf[18] = data.style;
  buf[19] = exId;
  return buf;
}

// CALS: every exercise's saved setup, so the glasses can skip setup.
export function encodeCals(data) {
  const buf = new Uint8Array(3 + EXERCISES.length * 6);
  const view = new DataView(buf.buffer);
  buf[0] = PROTO; buf[1] = 8; buf[2] = EXERCISES.length;
  for (const e of EXERCISES) {
    const cal = data.ex[e.id].cal;
    const o = 3 + e.id * 6;
    if (!cal) continue;
    view.setUint16(o, cal.a, true);
    view.setUint16(o + 2, cal.b, true);
    buf[o + 4] = cal.c;
    buf[o + 5] = 1;
  }
  return buf;
}

export function encodeSetup(exId) {
  return new Uint8Array([PROTO, 7, exId]);
}

// -> {type:'hello'|'exercise', ex} | {type:'session', id, reps, seconds, ex} |
//    {type:'style', style} | {type:'event', event, style, value} |
//    {type:'cal', ex, a, b, c} | null
export function decodeGlassesMessage(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 2 || bytes[0] !== PROTO) return null;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const exOk = (x) => isActive(x);
  switch (bytes[1]) {
    case 1: return { type: 'hello', ex: exOk(bytes[2]) ? bytes[2] : 0 };
    case 9: return bytes.length >= 3 && exOk(bytes[2]) ? { type: 'exercise', ex: bytes[2] } : null;
    case 2: return bytes.length >= 11 && exOk(bytes[10])
      ? { type: 'session', id: view.getUint32(2, true), reps: view.getUint16(6, true),
          seconds: view.getUint16(8, true), ex: bytes[10] } : null;
    case 4: return bytes.length >= 3 && STYLES.some((s) => s.id === bytes[2]) ? { type: 'style', style: bytes[2] } : null;
    case 5: return bytes.length >= 6
      ? { type: 'event', event: bytes[2], style: bytes[3], value: view.getUint16(4, true) } : null;
    case 6: return bytes.length >= 8 && exOk(bytes[2]) && view.getUint16(3, true) >= 1
      ? { type: 'cal', ex: bytes[2], a: view.getUint16(3, true), b: view.getUint16(5, true), c: bytes[7] } : null;
    default: return null;
  }
}

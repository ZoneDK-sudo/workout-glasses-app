// Sound effects for each animation style. Glasses plugins have no audio API
// and phone plugins can't open the glasses' speaker route (HFP), so the
// glasses send an EVENT message and the phone plays the matching sound
// through its own media output (phone speaker or headphones).
//
// Playback uses Web Audio: phones only allow sound after a tap, and with Web
// Audio one tap unlocks the whole page (separate <audio> players can each
// need their own tap, so sounds triggered later by the glasses were blocked).
// The sounds are embedded in sounds-data.js, so nothing is fetched.
import { SOUND_DATA } from './sounds-data.js';
// All sounds are synthesized by GlassSDK/examples/situp_counter/tools/make_sounds.py.

export const EVENTS = { READY: 1, REP: 2, BEST: 3, PAUSE: 4, RESUME: 5, TIER: 6, ROLLED: 7 };

// style id -> event -> sound name
const SOUND_MAP = {
  0: { 1: 'ding', 2: 'blip', 3: 'chime', 4: 'down', 5: 'up' },                       // Ring
  1: { 1: 'whistle', 2: 'hup', 3: 'cheer', 4: 'snore', 5: 'whistle-short' },         // Coach Head
  2: { 1: 'ding', 2: 'boing', 3: 'fanfare', 4: 'snore', 5: 'boing-up' },             // Sit-up Figure
  3: { 1: 'power-on', 2: 'level', 3: 'choir', 4: 'power-down', 5: 'power-on' },      // Glow-Up
  4: { 1: 'shimmer', 2: 'sparkle', 3: 'boom', 4: 'sad-trombone', 5: 'shimmer' },     // Aura
  5: { 1: 'mrrp', 2: 'purr', 3: 'meow-happy', 4: 'hiss', 5: 'mrrp' },                // Judgy Cat
  6: { 1: 'ticker', 2: 'ka-ching', 3: 'rocket', 4: 'crash', 5: 'ticker' },           // Stonks
};

// What a style sounds like when you pick it on the phone.
const PREVIEW = { 0: 'chime', 1: 'whistle', 2: 'boing', 3: 'power-1', 4: 'boom', 5: 'mrrp', 6: 'ka-ching' };

// Pitch climbs with the rep count so you never hear the same sound twice.
// Reps 1-12 walk up a major scale (a little do-re-mi melody, from a fifth
// below normal pitch to an octave above). After that the pitch keeps rising
// in ever smaller steps, so every rep is still higher than the last.
const MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11];
const SCALE_REPS = 12;
const START_SEMITONES = -7;

export function semitonesFor(count) {
  const step = Math.max(0, Math.floor(count) - 1);
  if (step < SCALE_REPS) {
    return START_SEMITONES + 12 * Math.floor(step / 7) + MAJOR_SCALE[step % 7];
  }
  const top = START_SEMITONES + 12 + MAJOR_SCALE[(SCALE_REPS - 1) % 7]; // +12
  // Slows down but never flattens out: +5.5 semitones by rep 50, +10 by 300.
  return top + 2.2 * Math.log(1 + (step - SCALE_REPS + 1) / 3.5);
}

export function rateFor(count) {
  return 2 ** (semitonesFor(count) / 12);
}

// Glow-up tiers are sent instead of the rep at 10 / 25 / 50 reps.
const TIER_COUNT = [0, 10, 25, 50];

export function soundFor(style, event, value = 0) {
  // The Roll prank: same sting whatever the style.
  if (event === EVENTS.ROLLED) return { name: 'rolled', rate: 1 };
  let name = SOUND_MAP[style]?.[event];
  let count = value;
  if (style === 3 && event === EVENTS.TIER) {
    const tier = Math.max(1, Math.min(3, value));
    name = `power-${tier}`;
    count = TIER_COUNT[tier];
  }
  if (!name) return null;
  // READY has no count yet: play it at normal pitch.
  const rate = event === EVENTS.READY || count <= 0 ? 1 : rateFor(count);
  return { name, rate };
}

export class SoundPlayer {
  // onStatus(state): 'locked' (needs a tap) | 'ready' | 'playing' | 'error'
  constructor({ onStatus = () => {} } = {}) {
    this.enabled = true;
    this.onStatus = onStatus;
    this.ctx = null;
    this.out = null;
    this.buffers = new Map();
    this.decoding = null;
  }

  get unlocked() {
    return !!this.ctx && this.ctx.state === 'running';
  }

  context() {
    if (this.ctx) return this.ctx;
    const AC = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (!AC) return null;
    try {
      this.ctx = new AC();
      this.out = this.ctx.createGain();
      this.out.connect(this.ctx.destination);
      this.ctx.onstatechange = () => this.report();
    } catch {
      this.ctx = null;
    }
    return this.ctx;
  }

  report() {
    if (!this.ctx) this.onStatus('error');
    else this.onStatus(this.ctx.state === 'running' ? 'ready' : 'locked');
  }

  // Decode every embedded sound once (in the background).
  decodeAll() {
    const ctx = this.context();
    if (!ctx || this.decoding) return this.decoding;
    this.decoding = (async () => {
      for (const [name, b64] of Object.entries(SOUND_DATA)) {
        try {
          const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
          const buffer = await new Promise((resolve, reject) => {
            const p = ctx.decodeAudioData(bytes.buffer, resolve, reject);   // old + new API
            if (p && typeof p.then === 'function') p.then(resolve, reject);
          });
          this.buffers.set(name, buffer);
        } catch {
          // one bad sound shouldn't stop the others
        }
      }
    })();
    return this.decoding;
  }

  // Call from a tap/click handler: browsers only start audio there.
  unlock() {
    const ctx = this.context();
    if (!ctx) { this.onStatus('error'); return; }
    try {   // a silent blip inside the tap is what actually unlocks iOS
      const blip = ctx.createBufferSource();
      blip.buffer = ctx.createBuffer(1, 1, 22050);
      blip.connect(ctx.destination);
      blip.start(0);
    } catch { /* ignore */ }
    const done = () => this.report();
    if (ctx.state !== 'running' && ctx.resume) ctx.resume().then(done, done);
    else done();
    void this.decodeAll();
  }

  play(name, rate = 1) {
    if (!this.enabled || !name) return;
    if (!this.unlocked) { this.onStatus('locked'); return; }
    const buffer = this.buffers.get(name);
    if (!buffer) { void this.decodeAll(); return; }
    try {
      const src = this.ctx.createBufferSource();
      src.buffer = buffer;
      src.playbackRate.value = rate;   // higher rate = higher pitch
      src.connect(this.out);
      src.start();
      this.onStatus('playing');
    } catch {
      this.onStatus('error');
    }
  }

  playEvent(style, event, value) {
    const sound = soundFor(style, event, value);
    if (sound) this.play(sound.name, sound.rate);
  }

  preview(style) {
    this.play(PREVIEW[style]);
  }

  stopAll() {
    try { this.ctx?.suspend(); } catch { /* ignore */ }
  }
}

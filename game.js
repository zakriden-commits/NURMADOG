'use strict';
const $ = (id) => document.getElementById(id);
const fighters = { benoit: { name: 'БЕНУА', color: '#ff3f57', photo: 'assets/benoit.jpg', lost: 'assets/benoit-lost.jpg' }, khabib: { name: 'ХАБИБ', color: '#437bff', photo: 'assets/khabib.jpeg', lost: 'assets/khabib-lost.jpg' } };
let state = BattleRules.createMatch(), round = 1, sound = false, audio, winTimer, confettiFrame;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
function tone(win = false) {
  if (!sound) return;
  try {
    audio ||= new (window.AudioContext || window.webkitAudioContext)();
    audio.resume();
    const notes = win ? [523, 659, 784, 1047] : [state.benoit + state.khabib > 170 ? 680 : 480];
    notes.forEach((freq, i) => {
      const oscillator = audio.createOscillator(), gain = audio.createGain(), t = audio.currentTime + i * .12;
      oscillator.type = 'sine'; oscillator.frequency.setValueAtTime(freq, t);
      oscillator.frequency.exponentialRampToValueAtTime(freq * 1.3, t + .08);
      gain.gain.setValueAtTime(.09, t); gain.gain.exponentialRampToValueAtTime(.001, t + .18);
      oscillator.connect(gain); gain.connect(audio.destination); oscillator.start(t); oscillator.stop(t + .2);
    });
  } catch { /* Sound is optional on browsers without Web Audio. */ }
}
function animate(element, name) {
  element.classList.remove(name); void element.offsetWidth; element.classList.add(name);
}
function render() {
  for (const id of Object.keys(fighters)) {
    $(id + '-score').textContent = state[id];
    $(id + '-progress').style.width = state[id] + '%';
    $(id).style.setProperty('--zoom', 1 + state[id] * .0018);
    $(id).setAttribute('aria-label', `Добавить очко ${id === 'benoit' ? 'Бенуа' : 'Хабибу'}. Сейчас ${state[id]} из 100`);
  }
  const diff = state.benoit - state.khabib;
  $('status').textContent = state.winner ? `${fighters[state.winner].name} забирает победу!` : state.benoit + state.khabib === 0 ? 'Первый голос за тобой. Начинаем?' : diff === 0 ? 'Ничья! Кто вырвется вперёд?' : `${fighters[diff > 0 ? 'benoit' : 'khabib'].name} впереди на ${Math.abs(diff)}. Чат, не сдаёмся!`;
}
function addPoint(id, event) {
  if (state.winner || $('result').open) return;
  state = BattleRules.vote(state, id); render(); tone();
  animate($(id), 'hit'); animate($(id + '-score'), 'bump');
  const rect = $(id).getBoundingClientRect();
  const pop = document.createElement('span'); pop.className = 'pop'; pop.textContent = '+1';
  pop.style.left = `${event && event.detail ? event.clientX - rect.left : rect.width / 2}px`;
  pop.style.top = `${event && event.detail ? event.clientY - rect.top : rect.height * .4}px`;
  $(id).append(pop); setTimeout(() => pop.remove(), 750);
  if (state.winner) {
    document.querySelector('.arena').classList.add('finishing'); $(id).classList.add('champion');
    Object.keys(fighters).forEach(key => $(key).disabled = true);
    winTimer = setTimeout(showResult, reducedMotion.matches ? 0 : 850);
  }
}
function showResult() {
  const id = state.winner, loser = id === 'benoit' ? 'khabib' : 'benoit';
  $('result').style.setProperty('--winner-color', fighters[id].color);
  $('winner-title').textContent = `${fighters[id].name} ПОБЕЖДАЕТ!`;
  $('final-score').textContent = `БЕНУА ${state.benoit} : ${state.khabib} ХАБИБ • МАТЧ ${String(round).padStart(2, '0')}`;
  $('winner-image').src = fighters[id].photo; $('winner-image').alt = fighters[id].name + ' — победитель';
  $('loser-image').src = fighters[loser].lost; $('loser-image').alt = fighters[loser].name + ' — проиграл';
  $('loser-label').textContent = `${fighters[loser].name} ПРОИГРАЛ`;
  $('result').showModal(); $('rematch').focus(); tone(true); confetti(fighters[id].color);
}
function restart() {
  clearTimeout(winTimer); cancelAnimationFrame(confettiFrame);
  if ($('result').open) $('result').close();
  state = BattleRules.createMatch(); round++;
  $('round').textContent = `МАТЧ ${String(round).padStart(2, '0')}`;
  document.querySelector('.arena').classList.remove('finishing');
  Object.keys(fighters).forEach(id => { $(id).disabled = false; $(id).classList.remove('champion', 'hit'); });
  render();
}
function confetti(color) {
  if (reducedMotion.matches) return;
  const canvas = $('confetti'), ctx = canvas.getContext('2d');
  canvas.width = innerWidth; canvas.height = innerHeight;
  const particles = Array.from({length: 120}, () => ({x: Math.random() * canvas.width, y: -Math.random() * canvas.height, v: 2 + Math.random() * 4, r: Math.random() * 6, a: Math.random() * 6, c: Math.random() > .4 ? color : '#ffffff'}));
  const end = performance.now() + 5500;
  function frame(now) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (now > end || !$('result').open) return;
    for (const p of particles) { p.y += p.v; p.x += Math.sin(p.a += .025); ctx.fillStyle = p.c; ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.a); ctx.fillRect(0, 0, p.r, p.r * 2); ctx.restore(); }
    confettiFrame = requestAnimationFrame(frame);
  }
  confettiFrame = requestAnimationFrame(frame);
}
Object.keys(fighters).forEach(id => $(id).addEventListener('click', event => addPoint(id, event)));
$('sound').addEventListener('click', () => { sound = !sound; $('sound').classList.toggle('active', sound); $('sound').setAttribute('aria-label', sound ? 'Выключить звук' : 'Включить звук'); $('sound').title = sound ? 'Выключить звук' : 'Включить звук'; $('sound').setAttribute('aria-pressed', String(sound)); tone(); });
async function fullscreen() { try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); } catch { $('status').textContent = 'Для полного экрана используй F11 в браузере.'; } }
$('fullscreen').addEventListener('click', fullscreen);
$('rematch').addEventListener('click', restart);
$('reset').addEventListener('click', () => { if (state.winner || state.benoit + state.khabib === 0 || confirm('Сбросить очки и начать новый матч?')) restart(); });
$('result').addEventListener('cancel', e => e.preventDefault());
document.addEventListener('keydown', event => {
  if (event.repeat || event.altKey || event.ctrlKey || event.metaKey || /INPUT|TEXTAREA/.test(event.target.tagName)) return;
  const key = event.key.toLowerCase();
  if (['arrowleft', 'a', 'ф'].includes(key)) { event.preventDefault(); addPoint('benoit'); }
  if (['arrowright', 'l', 'д'].includes(key)) { event.preventDefault(); addPoint('khabib'); }
  if (key === 'f' || key === 'а') { event.preventDefault(); fullscreen(); }
});
render();

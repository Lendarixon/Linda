/* Inline detector on the home page: paste a text, get a verdict, no account, no counters.
   Talks to the same Modal backend as demo.html. Degrades to a download hint if the API is unreachable. */
(function () {
  var card = document.querySelector('[data-hd]');
  if (!card) return;

  /* locally the pages are served through a proxy that forwards /api/* to the demo backend */
  var local = /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
  var API = local ? '' : 'https://ninjagovlad--linda-pro-demo-web.modal.run';
  var ta = card.querySelector('.hd-input');
  var btn = card.querySelector('.hd-check');
  var out = card.querySelector('.hd-result');
  var err = card.querySelector('.hd-error');
  var hint = card.querySelector('.hd-hint');
  var lang = (document.documentElement.lang || 'en').slice(0, 2);
  var session = null;
  var busy = false;

  var T = {
    en: {
      empty: 'Paste a text first.',
      short: 'Add at least 20 words so the result means something.',
      long: 'That is longer than the demo allows. Use the desktop app for long documents.',
      fail: 'The online check is unavailable right now. The desktop app works offline.',
      ai: 'Looks AI-written', uncertain: 'Unclear', human: 'Looks human-written',
      score: 'AI score', marked: 'Sentences worth a look', none: 'No sentence stood out.',
      again: 'Check another text', checking: 'Checking…', check: 'Check the text'
    },
    ru: {
      empty: 'Сначала вставьте текст.',
      short: 'Нужно хотя бы 20 слов — иначе результат ничего не значит.',
      long: 'Это длиннее, чем принимает демо. Для длинных документов есть приложение.',
      fail: 'Онлайн-проверка сейчас недоступна. Приложение работает офлайн.',
      ai: 'Похоже на ИИ', uncertain: 'Неясно', human: 'Похоже на человека',
      score: 'Оценка ИИ', marked: 'Фрагменты, на которые стоит взглянуть', none: 'Ни один фрагмент не выделился.',
      again: 'Проверить другой текст', checking: 'Проверяю…', check: 'Проверить текст'
    },
    pl: {
      empty: 'Najpierw wklej tekst.',
      short: 'Potrzeba co najmniej 20 słów — inaczej wynik nic nie znaczy.',
      long: 'To dłuższe niż przyjmuje demo. Długie dokumenty sprawdzi aplikacja.',
      fail: 'Sprawdzanie online jest teraz niedostępne. Aplikacja działa offline.',
      ai: 'Wygląda na AI', uncertain: 'Niepewne', human: 'Wygląda na ludzkie',
      score: 'Ocena AI', marked: 'Fragmenty warte uwagi', none: 'Żaden fragment się nie wyróżnił.',
      again: 'Sprawdź inny tekst', checking: 'Sprawdzam…', check: 'Sprawdź tekst'
    }
  }[lang] || null;
  if (!T) T = {
    empty: 'Paste a text first.', short: 'Add at least 20 words.', long: 'Too long for the demo.',
    fail: 'The online check is unavailable right now.', ai: 'Looks AI-written', uncertain: 'Unclear',
    human: 'Looks human-written', score: 'AI score', marked: 'Sentences worth a look',
    none: 'No sentence stood out.', again: 'Check another text', checking: 'Checking…', check: 'Check the text'
  };

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function setState(state) {
    card.setAttribute('data-state', state);
    if (btn) {
      btn.disabled = state === 'busy';
      btn.textContent = state === 'busy' ? T.checking : (state === 'done' ? T.again : T.check);
    }
  }

  function fail(msg) {
    if (err) { err.textContent = msg; err.hidden = false; }
    setState('idle');
  }

  async function getSession() {
    if (session) return session;
    var r = await fetch(API + '/api/session', { mode: 'cors', credentials: 'omit' });
    if (!r.ok) throw new Error('session');
    session = await r.json();
    return session;
  }

  function render(result) {
    var v = result.verdict || 'uncertain';
    var score = Math.round(100 * Number(result.p_ai || 0));
    var sents = (result.sentences || []).slice().sort(function (a, b) { return a.start - b.start; });
    var chars = Array.from(ta.value);
    var html = '';
    var pos = 0;
    var marked = 0;
    sents.forEach(function (s) {
      if (s.start < pos || s.end > chars.length) return;
      html += esc(chars.slice(pos, s.start).join(''));
      var chunk = esc(chars.slice(s.start, s.end).join(''));
      if (s.label === 'ai' || s.label === 'uncertain') {
        html += '<mark class="' + s.label + '">' + chunk + '</mark>';
        marked += 1;
      } else {
        html += chunk;
      }
      pos = s.end;
    });
    html += esc(chars.slice(pos).join(''));

    out.innerHTML =
      '<div class="hd-verdict ' + v + '"><b>' + esc(T[v] || T.uncertain) + '</b>' +
      '<span>' + esc(T.score) + ' ' + score + '%</span></div>' +
      '<div class="hd-text">' + html + '</div>' +
      '<p class="hd-note">' + (marked ? esc(T.marked) : esc(T.none)) + '</p>';
    out.hidden = false;
    setState('done');
  }

  var sample = card.getAttribute('data-sample');
  var sampleBtn = card.querySelector('.hd-sample');
  if (sampleBtn && sample) {
    sampleBtn.addEventListener('click', function () {
      ta.value = sample;
      ta.focus();
      if (err) err.hidden = true;
      setState('idle');
    });
  }

  btn.addEventListener('click', async function () {
    if (busy) return;
    var text = (ta.value || '').trim();
    var words = text.split(/\s+/).filter(Boolean).length;
    if (!text) return fail(T.empty);
    if (words < 20) return fail(T.short);
    if (text.length > 6000) return fail(T.long);

    busy = true;
    if (err) err.hidden = true;
    out.hidden = true;
    setState('busy');
    try {
      await getSession();
      var r = await fetch(API + '/api/detect', {
        method: 'POST',
        mode: 'cors',
        credentials: 'omit',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text, mode: 'sensitive', detector: 'loupe' })
      });
      if (!r.ok) throw new Error('detect');
      var j = await r.json();
      if (!j || !j.result) throw new Error('shape');
      render(j.result);
    } catch (e) {
      fail(T.fail);
    } finally {
      busy = false;
    }
  });

  ta.addEventListener('input', function () {
    if (card.getAttribute('data-state') === 'done') setState('idle');
    if (err) err.hidden = true;
  });
})();

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
      again: 'Check another text', checking: 'Checking…', check: 'Check the text',
      s1: 'Sending the text…', s2: 'Splitting into sentences…', s3: 'Scoring each sentence…', s4: 'Almost there…',
      hz: 'Make it sound more natural', hzRun: 'Rewriting…', hzDone: 'Rewritten — compare it with the original',
      hzFail: 'The rewrite is unavailable right now.', hzNote: 'Style only: names, numbers and facts stay as they are.',
      light: 'This is the lightweight Loupe model running in your browser. The desktop app runs the full ensemble locally.',
      limit: 'The free checks for this browser are used up. The desktop app has no limit and works offline.'
    },
    ru: {
      empty: 'Сначала вставьте текст.',
      short: 'Нужно хотя бы 20 слов — иначе результат ничего не значит.',
      long: 'Это длиннее, чем принимает демо. Для длинных документов есть приложение.',
      fail: 'Онлайн-проверка сейчас недоступна. Приложение работает офлайн.',
      ai: 'Похоже на ИИ', uncertain: 'Неясно', human: 'Похоже на человека',
      score: 'Оценка ИИ', marked: 'Фрагменты, на которые стоит взглянуть', none: 'Ни один фрагмент не выделился.',
      again: 'Проверить другой текст', checking: 'Проверяю…', check: 'Проверить текст',
      s1: 'Отправляю текст…', s2: 'Разбиваю на предложения…', s3: 'Оцениваю каждое предложение…', s4: 'Почти готово…',
      hz: 'Сделать текст естественнее', hzRun: 'Переписываю…', hzDone: 'Переписано — сравните с оригиналом',
      hzFail: 'Переписывание сейчас недоступно.', hzNote: 'Только стиль: имена, числа и факты остаются как были.',
      light: 'Это лёгкая модель Loupe прямо в браузере. В приложении на компьютере работает полный ансамбль — локально.',
      limit: 'Бесплатные проверки для этого браузера закончились. В приложении лимита нет, и оно работает офлайн.'
    },
    pl: {
      empty: 'Najpierw wklej tekst.',
      short: 'Potrzeba co najmniej 20 słów — inaczej wynik nic nie znaczy.',
      long: 'To dłuższe niż przyjmuje demo. Długie dokumenty sprawdzi aplikacja.',
      fail: 'Sprawdzanie online jest teraz niedostępne. Aplikacja działa offline.',
      ai: 'Wygląda na AI', uncertain: 'Niepewne', human: 'Wygląda na ludzkie',
      score: 'Ocena AI', marked: 'Fragmenty warte uwagi', none: 'Żaden fragment się nie wyróżnił.',
      again: 'Sprawdź inny tekst', checking: 'Sprawdzam…', check: 'Sprawdź tekst',
      s1: 'Wysyłam tekst…', s2: 'Dzielę na zdania…', s3: 'Oceniam każde zdanie…', s4: 'Prawie gotowe…',
      hz: 'Brzmi naturalniej', hzRun: 'Przepisuję…', hzDone: 'Przepisane — porównaj z oryginałem',
      hzFail: 'Przepisywanie jest teraz niedostępne.', hzNote: 'Tylko styl: nazwy, liczby i fakty zostają bez zmian.',
      light: 'To lekki model Loupe działający w przeglądarce. Aplikacja na komputerze uruchamia pełny zespół lokalnie.',
      limit: 'Bezpłatne sprawdzenia dla tej przeglądarki się skończyły. Aplikacja nie ma limitu i działa offline.'
    }
  }[lang] || null;
  if (!T) T = {
    empty: 'Paste a text first.', short: 'Add at least 20 words.', long: 'Too long for the demo.',
    fail: 'The online check is unavailable right now.', ai: 'Looks AI-written', uncertain: 'Unclear',
    human: 'Looks human-written', score: 'AI score', marked: 'Sentences worth a look',
    none: 'No sentence stood out.', again: 'Check another text', checking: 'Checking…', check: 'Check the text',
    s1: 'Sending…', s2: 'Splitting…', s3: 'Scoring…', s4: 'Almost there…',
    hz: 'Make it sound more natural', hzRun: 'Rewriting…', hzDone: 'Rewritten', hzFail: 'Unavailable.',
    hzNote: 'Style only.', light: 'Lightweight model in your browser; the desktop app runs the full ensemble locally.',
    limit: 'The free checks for this browser are used up.'
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
      '<p class="hd-note">' + (marked ? esc(T.marked) : esc(T.none)) + '</p>' +
      '<div class="hd-hz"><button class="button hd-hz-btn" type="button">' + esc(T.hz) + '</button>' +
      '<span class="hd-hz-note">' + esc(T.hzNote) + '</span></div>' +
      '<div class="hd-hz-out" hidden></div>' +
      '<p class="hd-light">' + esc(T.light) + '</p>';
    out.hidden = false;
    setState('done');
    var hzBtn = out.querySelector('.hd-hz-btn');
    if (hzBtn) hzBtn.addEventListener('click', runHumanizer);
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

  var progTimer = null;
  function progStart() {
    if (err) err.hidden = true;
    out.hidden = false;
    out.innerHTML = '<div class="hd-prog"><i></i></div><p class="hd-prog-label">' + esc(T.s1) + '</p>';
    var pct = 6, stage = 1;
    progTimer = setInterval(function () {
      pct = Math.min(94, pct + 4);
      var next = pct < 30 ? 1 : pct < 62 ? 2 : pct < 88 ? 3 : 4;
      stage = next;
      var bar = out.querySelector('.hd-prog i');
      var lab = out.querySelector('.hd-prog-label');
      if (bar) bar.style.width = pct + '%';
      if (lab) lab.textContent = T['s' + stage];
    }, 420);
  }
  function progStop() {
    if (progTimer) { clearInterval(progTimer); progTimer = null; }
  }

  async function runHumanizer() {
    var box = out.querySelector('.hd-hz-out');
    var hb = out.querySelector('.hd-hz-btn');
    if (!box || !hb) return;
    hb.disabled = true;
    hb.textContent = T.hzRun;
    box.hidden = false;
    box.innerHTML = '<div class="hd-prog"><i style="width:40%"></i></div>';
    try {
      var r = await fetch(API + '/api/stylize', {
        method: 'POST', mode: 'cors', credentials: 'omit',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: (ta.value || '').trim(), spans: null, detector: 'loupe' })
      });
      if (!r.ok) throw new Error('hz');
      var j = await r.json();
      var res = j.result || {};
      var chs = Array.from(ta.value);
      var changes = (res.changes || []).filter(function (c) { return c.status === 'changed'; })
        .sort(function (a, b) { return a.start - b.start; });
      var html = '', pos = 0;
      changes.forEach(function (c) {
        if (c.start < pos || c.end > chs.length) return;
        html += esc(chs.slice(pos, c.start).join(''));
        html += '<mark class="styled">' + esc(c.new || '') + '</mark>';
        pos = c.end;
      });
      html += esc(chs.slice(pos).join(''));
      box.innerHTML = '<p class="hd-hz-title">' + esc(T.hzDone) + '</p><div class="hd-text">' + html + '</div>';
      hb.textContent = T.hz;
      hb.disabled = false;
    } catch (e) {
      box.innerHTML = '<p class="hd-note">' + esc(T.hzFail) + '</p>';
      hb.textContent = T.hz;
      hb.disabled = false;
    }
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
    setState('busy');
    progStart();
    try {
      await getSession();
      var r = await fetch(API + '/api/detect', {
        method: 'POST',
        mode: 'cors',
        credentials: 'omit',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text, mode: 'sensitive', detector: 'loupe' })
      });
      if (r.status === 429) throw new Error('limit');
      if (!r.ok) throw new Error('detect');
      var j = await r.json();
      if (!j || !j.result) throw new Error('shape');
      progStop();
      render(j.result);
    } catch (e) {
      progStop();
      out.hidden = true;
      fail(e && e.message === 'limit' ? T.limit : T.fail);
    } finally {
      busy = false;
    }
  });

  ta.addEventListener('input', function () {
    if (card.getAttribute('data-state') === 'done') setState('idle');
    if (err) err.hidden = true;
  });
})();

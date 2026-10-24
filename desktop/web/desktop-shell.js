/* Native-feeling desktop workspace; existing analysis, history and export handlers stay attached. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const toolJobs=new Map(),toolClient=crypto.randomUUID();
  const taskChanged=()=>document.dispatchEvent(new Event('linda-task'));
  window.LINDA_tools={
    get active(){return [...toolJobs.values()].map(({id,key,route,stopping})=>({id,key,route,stopping}));},
    async run(url,body,key,route,onProgress){
      if(toolJobs.has(key))throw new Error(window.LINDA_T('task_busy'));
      const job={id:crypto.randomUUID(),key,route,stopping:false};toolJobs.set(key,job);taskChanged();
      let poll=null;
      if(typeof onProgress==='function'){
        poll=setInterval(async()=>{
          try{
            const r=await fetch('/api/progress/'+job.id);
            if(!r.ok)return;
            onProgress(await r.json());
          }catch(e){}
        },400);
      }
      try{
        const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,job_id:job.id,client_id:toolClient})});
        const result=await response.json().catch(()=>({}));
        if(response.status===499){const e=new Error(window.LINDA_T('task_stopped'));e.cancelled=true;throw e;}
        if(!response.ok)throw new Error(result.detail||window.LINDA_T('task_error'));
        return result;
      }finally{if(poll)clearInterval(poll);toolJobs.delete(key);taskChanged();}
    },
    async cancel(key){
      const jobs=[...toolJobs.values()].filter(job=>!key||job.key===key);
      await Promise.all(jobs.map(async job=>{
        if(job.stopping)return;job.stopping=true;taskChanged();
        try{const r=await fetch('/api/detect/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:job.id})});if(!r.ok)throw new Error('cancel');}
        catch(e){job.stopping=false;taskChanged();throw e;}
      }));
    }
  };
  window.addEventListener('pagehide',()=>{for(const job of toolJobs.values())fetch('/api/detect/cancel',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:job.id})}).catch(()=>{});});
  const COPY = {
    ru: {
      work:'Работа с текстом', tools:'Другие инструменты', app:'Приложение',
      check:'Проверить текст', check_desc:'Вставьте текст или откройте документ. Linda оценит признаки ИИ и подсветит фрагменты.',
      history:'История проверок', history_desc:'Сохранённые тексты и результаты. Откройте проверку, чтобы вернуться к ней.',
      batch:'Проверить файлы', batch_desc:'Добавьте документы или выберите папку. Linda проверит файлы по очереди.',
      compare:'Сравнить документы', compare_desc:'Выберите две сохранённые проверки, чтобы увидеть совпадения и изменения.',
      trace:'Сравнить стиль', trace_desc:'Linda Trace сравнивает тексты внутри выбранного набора. Это исследовательский инструмент, а не доказательство авторства.',
      humanize:'Переписать текст', humanize_desc:'Локальная переработка текста. Проверьте смысл и факты самостоятельно; результат детектора не гарантирует качество.',
      models:'Модели и пакеты', models_desc:'Установленные инструменты и параметры анализа. Для обычной проверки подходят автоматические настройки.',
      settings:'Настройки', settings_desc:'Внешний вид, язык, работа моделей и обновления. Изменения применяются кнопкой «Сохранить».',
      help:'Как пользоваться', help_desc:'Коротко о проверке текста, результатах и ограничениях Linda.',
      license:'Лицензия', license_desc:'Состояние лицензии и активация дополнительных возможностей.',
      audit:'Журнал действий', audit_desc:'Локальная история действий программы.',
      back:'К проверке текста', local:'На вашем компьютере', privacy:'Тексты обрабатываются локально',
      language:'Язык интерфейса', editor:'Ваш текст', shortcut:'Ctrl + Enter — проверить',
      recommendation:'Для более надёжной оценки: от 300 слов связного текста.',
      suitability_short:'Списки, формы, формулы и слайды оцениваются ненадёжно. Результат не доказывает авторство.',
      cancel:'Отменить изменения', open_error:'Не удалось связаться со службой Linda. Повторите переход через несколько секунд.',
      suitability:'Какие тексты и файлы подходят',
      guide:'Три простых шага', step1:'Добавьте текст', step1_text:'Вставьте текст в поле или откройте TXT, DOC, DOCX, RTF, ODT, EPUB, FB2, HTML, PDF.',
      step2:'Нажмите «Проверить»', step2_text:'Во время анализа здесь появится прогресс. Текст остаётся на компьютере.',
      step3:'Посмотрите результат', step3_text:'Прочитайте объяснение и подсветку. При необходимости сохраните отчёт.',
      caution:'Оценка не доказывает авторство. Не принимайте решения о человеке только по результату детектора.',
      appearance:'Внешний вид и язык', checking:'Проверка и модели', storage:'Хранение моделей', updates:'Обновления и сведения',
      mode:'Вид результатов', skip:'Перейти к содержимому',
      help_start:'С чего начать', help_start_text:'Откройте «Проверить текст», вставьте связный текст и нажмите «Проверить». Можно перетащить документ прямо в поле. Каждая вкладка хранит свой текст и результат.',
      help_formats:'Подходящие материалы', help_formats_text:'Лучше всего подходят статьи, эссе и другая связная проза от 300 слов. Поддерживаются TXT, MD, DOCX и PDF. PPT/PPTX, списки, формы, формулы и текст со слайдов не подходят для надёжной оценки.',
      help_result:'Как читать результат', help_result_text:'Общая оценка относится ко всему документу. Подсветка показывает локальные оценки фрагментов — это другой показатель. Отсутствие подсветки не доказывает, что текст написал человек.',
      help_local:'Где хранятся данные', help_local_text:'Проверка выполняется на этом компьютере. Тексты и история не отправляются в облако. Для скачивания моделей и обновлений требуется интернет.',
      help_reuse:'Несколько документов', help_reuse_text:'«Проверить файлы» запускает последовательную проверку документов. Результаты доступны в «Истории проверок». «Сравнить документы» показывает изменения между двумя сохранёнными проверками.',
      help_settings:'Если что-то не работает', help_settings_text:'Проверьте наличие моделей в разделе «Модели и пакеты». Обновления и сохранение диагностики находятся в настройках. Если файл не читается, предыдущий текст сохраняется; выберите другой файл или вставьте текст вручную.',
      basic:'Начать проверку', open_models:'Открыть модели и пакеты',
    },
    en: {
      work:'Text workspace', tools:'Other tools', app:'Application',
      check:'Check text', check_desc:'Paste text or open a document. Linda estimates AI signals and highlights passages.',
      history:'Check history', history_desc:'Saved texts and results. Open a check to continue where you left off.',
      batch:'Check files', batch_desc:'Add documents or choose a folder. Linda checks the files one at a time.',
      compare:'Compare documents', compare_desc:'Choose two saved checks to see matching passages and changes.',
      trace:'Compare writing style', trace_desc:'Linda Trace compares texts within your selected collection. It is a research tool, not proof of authorship.',
      humanize:'Rewrite text', humanize_desc:'Local text rewriting. Review meaning and facts yourself; a detector score does not guarantee quality.',
      models:'Models and packages', models_desc:'Installed tools and analysis options. Automatic settings suit everyday checks.',
      settings:'Settings', settings_desc:'Appearance, language, model behaviour and updates. Apply changes with Save.',
      help:'How to use Linda', help_desc:'A short guide to checking text, reading results and understanding the limits.',
      license:'Licence', license_desc:'Licence status and activation of additional features.',
      audit:'Activity log', audit_desc:'A local record of application activity.',
      back:'Back to checking', local:'On your computer', privacy:'Texts are processed locally',
      language:'Interface language', editor:'Your text', shortcut:'Ctrl + Enter to check',
      recommendation:'For a more reliable estimate, use at least 300 words of connected prose.',
      suitability_short:'Lists, forms, formulas and slides are less reliable. An estimate does not prove authorship.',
      cancel:'Cancel changes', open_error:'Could not reach the local Linda service. Try opening this section again in a few seconds.',
      suitability:'Suitable texts and file types',
      guide:'Three simple steps', step1:'Add your text', step1_text:'Paste into the editor or open TXT, DOC, DOCX, RTF, ODT, EPUB, FB2, HTML or PDF.',
      step2:'Choose Check text', step2_text:'Progress appears during analysis. Your text stays on your computer.',
      step3:'Review the result', step3_text:'Read the explanation and highlights. Save a report if needed.',
      caution:'An estimate does not prove authorship. Never make a decision about someone solely on a detector result.',
      appearance:'Appearance and language', checking:'Checking and models', storage:'Model storage', updates:'Updates and information',
      mode:'Result detail', skip:'Skip to content',
      help_start:'Getting started', help_start_text:'Open Check text, paste connected prose and choose Check text. You can also drag a document into the editor. Each tab keeps its own text and result.',
      help_formats:'Suitable materials', help_formats_text:'Articles, essays and other connected prose of at least 300 words work best. TXT, MD, DOCX and PDF are supported. PPT/PPTX, lists, forms, formulas and slide text cannot be assessed reliably.',
      help_result:'Understanding results', help_result_text:'The overall estimate applies to the whole document. Highlights show local passage estimates, which are a different measure. No highlighted passages does not prove human authorship.',
      help_local:'Where your data stays', help_local_text:'Checks run on this computer. Texts and history are not sent to a cloud service. Downloading models and application updates requires internet access.',
      help_reuse:'Working with documents', help_reuse_text:'Check files processes documents one at a time. Find the results in Check history. Compare documents shows changes between two saved checks.',
      help_settings:'If something goes wrong', help_settings_text:'Check installed models in Models and packages. Find updates and diagnostics in Settings. If a file cannot be read, your previous text stays in place; choose another file or paste the text.',
      basic:'Start a check', open_models:'Open models and packages',
    },
    pl: {
      work:'Praca z tekstem', tools:'Inne narzędzia', app:'Aplikacja',
      check:'Sprawdź tekst', check_desc:'Wklej tekst lub otwórz dokument. Linda oceni oznaki AI i zaznaczy fragmenty.',
      history:'Historia sprawdzeń', history_desc:'Zapisane teksty i wyniki. Otwórz sprawdzenie, aby do niego wrócić.',
      batch:'Sprawdź pliki', batch_desc:'Dodaj dokumenty lub wybierz folder. Linda sprawdzi pliki po kolei.',
      compare:'Porównaj dokumenty', compare_desc:'Wybierz dwa zapisane sprawdzenia, aby zobaczyć podobieństwa i zmiany.',
      trace:'Porównaj styl', trace_desc:'Linda Trace porównuje teksty w wybranym zbiorze. To narzędzie badawcze, a nie dowód autorstwa.',
      humanize:'Przeredaguj tekst', humanize_desc:'Lokalne przeredagowanie tekstu. Samodzielnie sprawdź sens i fakty; wynik detektora nie gwarantuje jakości.',
      models:'Modele i pakiety', models_desc:'Zainstalowane narzędzia i opcje analizy. Do zwykłego sprawdzania wystarczą ustawienia automatyczne.',
      settings:'Ustawienia', settings_desc:'Wygląd, język, działanie modeli i aktualizacje. Zastosuj zmiany przyciskiem Zapisz.',
      help:'Jak korzystać', help_desc:'Krótko o sprawdzaniu tekstu, wynikach i ograniczeniach Lindy.',
      license:'Licencja', license_desc:'Stan licencji i aktywacja dodatkowych funkcji.',
      audit:'Dziennik działań', audit_desc:'Lokalny zapis działań aplikacji.',
      back:'Wróć do sprawdzania', local:'Na Twoim komputerze', privacy:'Teksty są przetwarzane lokalnie',
      language:'Język interfejsu', editor:'Twój tekst', shortcut:'Ctrl + Enter — sprawdź',
      recommendation:'Aby uzyskać bardziej wiarygodną ocenę, użyj co najmniej 300 słów ciągłego tekstu.',
      suitability_short:'Listy, formularze, wzory i slajdy dają mniej wiarygodne wyniki. Ocena nie dowodzi autorstwa.',
      cancel:'Anuluj zmiany', open_error:'Nie udało się połączyć z lokalną usługą Lindy. Spróbuj otworzyć tę sekcję ponownie za kilka sekund.',
      suitability:'Odpowiednie teksty i typy plików',
      guide:'Trzy proste kroki', step1:'Dodaj tekst', step1_text:'Wklej tekst lub otwórz plik TXT, DOC, DOCX, RTF, ODT, EPUB, FB2, HTML albo PDF.',
      step2:'Wybierz Sprawdź tekst', step2_text:'Podczas analizy pojawi się postęp. Tekst zostaje na Twoim komputerze.',
      step3:'Przejrzyj wynik', step3_text:'Przeczytaj wyjaśnienie i zaznaczenia. W razie potrzeby zapisz raport.',
      caution:'Ocena nie dowodzi autorstwa. Nigdy nie podejmuj decyzji o człowieku wyłącznie na podstawie wyniku detektora.',
      appearance:'Wygląd i język', checking:'Sprawdzanie i modele', storage:'Przechowywanie modeli', updates:'Aktualizacje i informacje',
      mode:'Szczegółowość wyników', skip:'Przejdź do treści',
      help_start:'Od czego zacząć', help_start_text:'Otwórz Sprawdź tekst, wklej ciągły tekst i wybierz Sprawdź tekst. Możesz też przeciągnąć dokument do edytora. Każda karta zachowuje własny tekst i wynik.',
      help_formats:'Odpowiednie materiały', help_formats_text:'Najlepiej nadają się artykuły, eseje i inne ciągłe teksty liczące co najmniej 300 słów. Obsługiwane formaty to TXT, MD, DOCX i PDF. PPT/PPTX, listy, formularze, wzory i tekst slajdów nie pozwalają na wiarygodną ocenę.',
      help_result:'Jak czytać wynik', help_result_text:'Ocena ogólna dotyczy całego dokumentu. Zaznaczenia pokazują lokalne oceny fragmentów — to inny wskaźnik. Brak zaznaczeń nie dowodzi, że tekst napisał człowiek.',
      help_local:'Gdzie są Twoje dane', help_local_text:'Sprawdzanie odbywa się na tym komputerze. Teksty i historia nie trafiają do chmury. Pobieranie modeli i aktualizacji wymaga internetu.',
      help_reuse:'Wiele dokumentów', help_reuse_text:'Sprawdź pliki analizuje dokumenty po kolei. Wyniki znajdziesz w Historii sprawdzeń. Porównaj dokumenty pokazuje zmiany między dwoma zapisanymi sprawdzeniami.',
      help_settings:'Gdy coś nie działa', help_settings_text:'Sprawdź zainstalowane modele w sekcji Modele i pakiety. Aktualizacje i zapis diagnostyki znajdziesz w Ustawieniach. Jeśli nie uda się odczytać pliku, poprzedni tekst pozostaje na miejscu; wybierz inny plik lub wklej tekst.',
      basic:'Rozpocznij sprawdzanie', open_models:'Otwórz modele i pakiety',
    },
  };
  const LEGACY = {
    ru:{ui_doc_title:'Linda — проверка текста',ui_paste:'Вставить из буфера',ui_attach:'Открыть файл',ui_analyze:'Проверить текст',ui_input_ph:'Вставьте текст сюда или перетащите документ…',ui_heat:'Подсветка текста',ui_models:'Модели для проверки',ui_advanced:'Ручной выбор моделей',ui_single:'Одна модель',ui_compare:'Сравнить модели',ui_ens:'Общая оценка',ui_threshold:'Режим проверки',ui_sensitive:'Чувствительный',ui_precise:'Осторожный',ui_export:'Сохранить результат',exp_title:'Отчёт и экспорт',cab_close:'К проверке текста',cab_batch:'Проверить файлы',cab_cmp:'Сравнить документы',cab_trace:'Сравнить стиль',cab_hum:'Переписать текст',h_empty:'Проверок пока нет. Результаты появятся здесь после первой проверки.',tr_hint:'Добавьте исследуемый текст и не менее трёх текстов для сравнения. Каждый текст — от 300 слов. Результат показывает различия внутри набора и не доказывает авторство.',hu_hint:'Перепишите текст локально. После переработки самостоятельно проверьте смысл, факты и формулировки. Снижение оценки ИИ не гарантирует качество.',style_loop:'Повторная переработка',ui_sw_simple:'Основное',ui_sw_expert:'Все подробности'},
    en:{ui_doc_title:'Linda — text checking',ui_paste:'Paste from clipboard',ui_attach:'Open file',ui_analyze:'Check text',ui_input_ph:'Paste your text here or drag in a document…',ui_heat:'Text highlights',ui_models:'Checking models',ui_advanced:'Choose models manually',ui_single:'One model',ui_compare:'Compare models',ui_ens:'Combined estimate',ui_threshold:'Checking mode',ui_sensitive:'Sensitive',ui_precise:'Cautious',ui_export:'Save result',exp_title:'Report and export',cab_close:'Back to checking',cab_batch:'Check files',cab_cmp:'Compare documents',cab_trace:'Compare writing style',cab_hum:'Rewrite text',h_empty:'No checks yet. Your results will appear here after your first check.',tr_hint:'Add the text you are studying and at least three comparison texts. Each needs at least 300 words. The result describes differences within this collection and does not prove authorship.',hu_hint:'Rewrite text locally. Review meaning, facts and wording yourself afterwards. A lower AI estimate does not guarantee quality.',style_loop:'Rewrite again',ui_sw_simple:'Essentials',ui_sw_expert:'All details'},
    pl:{ui_doc_title:'Linda — sprawdzanie tekstu',ui_paste:'Wklej ze schowka',ui_attach:'Otwórz plik',ui_analyze:'Sprawdź tekst',ui_input_ph:'Wklej tekst tutaj lub przeciągnij dokument…',ui_heat:'Zaznaczenia w tekście',ui_models:'Modele do sprawdzania',ui_advanced:'Ręczny wybór modeli',ui_single:'Jeden model',ui_compare:'Porównaj modele',ui_ens:'Ocena łączna',ui_threshold:'Tryb sprawdzania',ui_sensitive:'Czuły',ui_precise:'Ostrożny',ui_export:'Zapisz wynik',exp_title:'Raport i eksport',cab_close:'Wróć do sprawdzania',cab_batch:'Sprawdź pliki',cab_cmp:'Porównaj dokumenty',cab_trace:'Porównaj styl',cab_hum:'Przeredaguj tekst',h_empty:'Nie ma jeszcze sprawdzeń. Wyniki pojawią się tutaj po pierwszym sprawdzeniu.',tr_hint:'Dodaj badany tekst i co najmniej trzy teksty porównawcze. Każdy musi mieć co najmniej 300 słów. Wynik opisuje różnice w zbiorze i nie dowodzi autorstwa.',hu_hint:'Przeredaguj tekst lokalnie. Następnie samodzielnie sprawdź sens, fakty i sformułowania. Niższa ocena AI nie gwarantuje jakości.',style_loop:'Przeredaguj ponownie',ui_sw_simple:'Podstawowe',ui_sw_expert:'Wszystkie szczegóły'},
  };
  for (const lang of Object.keys(LEGACY)) Object.assign((window.LINDA_I18N||{})[lang]||{},LEGACY[lang]);
  const T = key => (COPY[window.LINDA_LANG]||COPY.en)[key] || COPY.en[key] || key;
  const iconPaths={
    check:'M5 3h10l4 4v14H5z M14 3v5h5 M8 13h8 M8 17h5',
    history:'M3 12a9 9 0 1 0 3-6 M3 3v5h5 M12 7v5l3 2',
    batch:'M3 7h7l2 2h9v12H3z M5 7V3h7l2 2h5v4',
    compare:'M3 4h7v16H3z M14 4h7v16h-7z M7 10h10 M14 7l3 3-3 3',
    trace:'M5 18a10 10 0 0 1 0-12 M9 20a14 14 0 0 1 0-16 M13 20a14 14 0 0 0 0-16 M17 18a10 10 0 0 0 0-12',
    humanize:'M4 20l4-1L20 7l-4-4L4 15z M13 6l4 4 M3 22h18',
    models:'M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z',
    settings:'M12 3v3 M12 18v3 M3 12h3 M18 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2 M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8',
    help:'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5 M12 17v1',
    license:'M5 3h14v18l-7-3-7 3z M9 9l2 2 4-4',
    audit:'M5 3h14v18H5z M8 8h8 M8 12h8 M8 16h5',
  };
  const icon = key => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${iconPaths[key]||iconPaths.check}"/></svg>`;
  const node = (tag,cls,html) => { const el=document.createElement(tag);if(cls)el.className=cls;if(html)el.innerHTML=html;return el; };
  function init(){
    if(document.body.classList.contains('ld-desktop'))return;
    document.body.classList.add('ld-desktop');
    const header=document.querySelector('.header'), grid=document.querySelector('.main-grid');
    const shell=node('div','ld-shell'), nav=node('nav','ld-nav'), workspace=node('div','ld-workspace');
    nav.id='desktopNav';shell.id='desktopShell';workspace.id='desktopWorkspace';
    nav.setAttribute('aria-label',T('work'));
    const skip=node('a','ld-skip-link');skip.href='#desktopPageTitle';skip.dataset.ldText='skip';document.body.prepend(skip);
    const pagehead=node('header','ld-pagehead','<div class="ld-pagehead-top"><h1 id="desktopPageTitle" tabindex="-1"></h1><button class="ld-back" id="desktopBack" type="button" data-ld-text="back"></button></div><p id="desktopPageDescription"></p>');
    const auditSwitch=node('button','ld-back');auditSwitch.id='desktopHistorySwitch';auditSwitch.type='button';auditSwitch.hidden=true;pagehead.querySelector('.ld-pagehead-top').insertBefore(auditSwitch,pagehead.querySelector('#desktopBack'));
    workspace.append(pagehead);shell.append(nav,workspace);header.after(shell);
    workspace.append(grid);
    const models=document.querySelector('.panel-left');models.classList.add('ld-tool-page');models.id='desktopModels';workspace.append(models);models.hidden=true;
    for(const id of ['cabView','cabViewer','lpSet','lpLic'])workspace.append($(id));
    for(const id of ['cabView','lpSet','lpLic']){ $(id).setAttribute('role','region');$(id).removeAttribute('aria-modal'); }
    const help=node('section','ld-tool-page');help.id='desktopHelp';help.hidden=true;
    help.innerHTML='<div class="ld-help-grid">'+['start','formats','result','local','reuse','settings'].map(key=>`<article class="ld-help-card"><h2 data-ld-text="help_${key}"></h2><p data-ld-text="help_${key}_text"></p></article>`).join('')+'</div><button class="lp-btn" id="desktopHelpStart" data-ld-text="basic" style="margin-top:20px"></button>';
    workspace.append(help);
    // Keep the full legal/limitations text in Help; the editor keeps a concise warning.
    let legal=$('footLic');
    if(legal){while(legal.parentElement&&legal.parentElement!==document.body)legal=legal.parentElement;legal.classList.add('ld-help-card','ld-legal');legal.style.cssText='';help.append(legal);}
    const navButton = key => `<button class="ld-nav-button" data-route="${key}" type="button">${icon(key)}<span data-ld-text="${key}"></span></button>`;
    nav.innerHTML='<div class="ld-nav-group" data-ld-text="work"></div>'+['check','history','batch','compare'].map(navButton).join('')+'<div class="ld-nav-group" data-ld-text="tools"></div>'+['trace','humanize'].map(navButton).join('')+'<div class="ld-nav-bottom"><div class="ld-nav-group" data-ld-text="app"></div>'+['models','settings','help','license'].map(navButton).join('')+'</div>';
    nav.querySelector('.ld-nav-bottom').append($('licBadge'));
    $('licBadge').tabIndex=0;$('licBadge').setAttribute('role','button');$('licBadge').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('licBadge').click();}});
    const oldTools=header.lastElementChild;
    const headerTools=node('div','ld-header-tools','<span class="ld-local-badge"><i class="ld-local-dot"></i><span data-ld-text="local"></span></span><select class="ld-language" id="desktopLanguage"><option value="ru">Русский</option><option value="en">English</option><option value="pl">Polski</option></select>');
    header.append(headerTools);oldTools.hidden=true;
    const statusbar=node('footer','ld-statusbar','<span data-ld-text="privacy"></span><span id="desktopServiceStatus"></span><span>Linda 2.3.0.0</span>');
    statusbar.querySelector('#desktopServiceStatus').append($('devInfo'));document.body.append(statusbar);
    // Labelled editor and guidance before the action, without a wall of text.
    const editor=$('textInput'), inputHead=node('div','ld-input-head','<label for="textInput" data-ld-text="editor"></label><span data-ld-text="shortcut"></span>');
    const preflight=$('preflightPanel');preflight.setAttribute('aria-live','off');
    const details=node('details','ld-preflight-details','<summary data-ld-text="suitability"></summary>');
    details.append($('preflightGuidance'),$('preflightFormats'));
    const recommendation=node('p','ld-recommendation');recommendation.dataset.ldText='recommendation';
    const suitability=node('p','ld-preflight-limit');suitability.dataset.ldText='suitability_short';
    preflight.prepend(recommendation,suitability);preflight.append(details);preflight.append($('preflightWarning'));
    editor.before(inputHead,preflight,document.querySelector('.toolbar'));
    editor.setAttribute('aria-describedby','preflightPanel');
    editor.addEventListener('input',()=>{$('statusIndicator').removeAttribute('data-error');$('statusIndicator').setAttribute('role','status');});
    $('emptyState').innerHTML='<div class="ld-guide"><h2 data-ld-text="guide"></h2><ol>'+[1,2,3].map(i=>`<li><b data-ld-text="step${i}"></b><span data-ld-text="step${i}_text"></span></li>`).join('')+'</ol><p class="ld-guide-note" data-ld-text="caution"></p></div>';
    // Turn the existing settings fields into four native-looking categories.
    const settingsGrid=$('lpSet').querySelector('.lp-grid'), settingsLayout=node('div','ld-settings-layout'), settingsNav=node('div','ld-settings-nav'), settingsSections=node('div');
    settingsNav.setAttribute('role','tablist');settingsNav.setAttribute('aria-orientation','vertical');
    const groups={}, ids=['appearance','checking','storage','updates'];
    for(const key of ids){
      const button=node('button');button.type='button';button.dataset.setting=key;button.dataset.ldText=key;button.id='desktopSetting-'+key;button.setAttribute('role','tab');button.setAttribute('aria-controls','desktopGroup-'+key);settingsNav.append(button);
      const group=node('section','ld-settings-group');group.id='desktopGroup-'+key;group.setAttribute('role','tabpanel');group.setAttribute('aria-labelledby',button.id);groups[key]=group;settingsSections.append(group);
    }
    let current='appearance';
    for(const child of Array.from(settingsGrid.children)){
      const key=child.dataset.i18n;
      if(key==='set_appearance')current='appearance';else if(key==='set_sec_device')current='checking';else if(key==='loc_title')current='storage';else if(key==='set_sec_updates')current='updates';
      if(key==='set_language'){ child.style.display='';const field=child.nextElementSibling;if(field)field.style.display=''; }
      groups[current].append(child);
    }
    const modeField=node('div','lp-field lp-full','<span data-ld-text="mode"></span>');modeField.append($('uiSw'));groups.appearance.append(modeField);
    settingsLayout.append(settingsNav,settingsSections);settingsGrid.replaceWith(settingsLayout);
    function setting(key,focus=false){
      for(const id of ids){const on=id===key;groups[id].hidden=!on;const b=$('desktopSetting-'+id);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;}
      if(focus)$('desktopSetting-'+key).focus();
    }
    settingsNav.addEventListener('click',e=>{const b=e.target.closest('[data-setting]');if(b)setting(b.dataset.setting);});
    settingsNav.addEventListener('keydown',e=>{if(!['ArrowDown','ArrowUp','ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;const buttons=[...settingsNav.children],i=buttons.indexOf(document.activeElement);let index=e.key==='Home'?0:e.key==='End'?buttons.length-1:(i+(['ArrowDown','ArrowRight'].includes(e.key)?1:-1)+buttons.length)%buttons.length;e.preventDefault();setting(buttons[index].dataset.setting,true);});
    setting('appearance');
    $('lpSetClose').removeAttribute('data-i18n');$('lpSetClose').dataset.ldText='cancel';
    let route='check',generation=0,transition=false;
    const paneMap={history:'hist',batch:'batch',compare:'cmp',trace:'trace',humanize:'humanize',audit:'audit'};
    const routeForPane=pane=>Object.keys(paneMap).find(k=>paneMap[k]===pane)||'history';
    function activate(next,focus=false){
      route=next;document.body.dataset.route=next;
      grid.hidden=next!=='check';models.hidden=next!=='models';help.hidden=next!=='help';
      // Existing legacy CSS uses !important; native hidden state wins explicitly.
      grid.style.setProperty('display',next==='check'?'grid':'none','important');
      models.style.setProperty('display',next==='models'?'block':'none','important');
      $('desktopPageTitle').textContent=T(next);$('desktopPageDescription').textContent=T(next+'_desc');
      $('desktopBack').hidden=next==='check';
      nav.querySelectorAll('[data-route]').forEach(b=>{if(b.dataset.route===(next==='audit'?'history':next))b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
      auditSwitch.hidden=!['history','audit'].includes(next);auditSwitch.textContent=T(next==='audit'?'history':'audit');
      if(focus)$('desktopPageTitle').focus({preventScroll:true});
      window.dispatchEvent(new CustomEvent('linda-route',{detail:{route:next}}));
    }
    function closeLegacyExcept(next){
      if(next!=='settings'&&$('lpSet').classList.contains('show'))$('lpSetClose').click();
      if(next!=='license'&&$('lpLic').classList.contains('show'))$('lpLicClose').click();
      if(!paneMap[next])window.LINDA_cabinet.close();
      if($('cabViewer').classList.contains('open'))$('vClose')?.click();
    }
    async function navigate(next,options={}){
      const turn=++generation;transition=true;closeLegacyExcept(next);
      if(next==='settings'&&!$('lpSet').classList.contains('show'))$('btnSettings').click();
      if(next==='license'&&!$('lpLic').classList.contains('show'))$('licBadge').click();
      if(paneMap[next]){
        let opened;
        try { opened=await window.LINDA_cabinet.open(paneMap[next]); }
        catch(error){
          if(turn!==generation)return;
          closeLegacyExcept('check');activate('check');transition=false;
          const toast=$('lpToast');toast.textContent=T('open_error');toast.classList.add('show','bad');
          setTimeout(()=>toast.classList.remove('show'),7000);return;
        }
        if(turn!==generation)return;
        if(!opened)next='license';
      }
      activate(next,options.focus!==false);transition=false;
    }
    nav.addEventListener('click',e=>{const b=e.target.closest('.ld-nav-button[data-route]');if(b)navigate(b.dataset.route);});
    $('desktopBack').onclick=() => navigate('check');$('desktopHelpStart').onclick=()=>navigate('check');
    // Rewrite entry next to the verdict; the command row carries the humanize button.
    async function openRewrite(){await navigate('humanize');if(route==='humanize')$('huTake').click();}
    const stylePanel=$('stylePanel');$('simpleVerdict').after(stylePanel);
    const styleOpen=node('button','lp-btn');styleOpen.id='desktopRewriteResult';styleOpen.type='button';styleOpen.dataset.i18n='rewrite_open';styleOpen.onclick=openRewrite;
    stylePanel.querySelector('.heatmap-header').after(styleOpen);
    const styleDetails=node('details','ld-rewrite-details','<summary data-i18n="rewrite_fragments"></summary>');
    stylePanel.append(styleDetails);styleDetails.append($('styleBody'));
    // Humanize entry in the command row: hidden until a check finishes, blinks 5 s once as a recommendation.
    // Note: LINDA_applyI18n overwrites textContent of [data-i18n] nodes, so the label lives in its own span.
    const huCta=node('button','btn-upload');huCta.id='huCta';huCta.type='button';
    const huCtaLabel=node('span');huCtaLabel.dataset.i18n='hu_cta';huCta.append(huCtaLabel);
    huCta.hidden=true;
    $('btnUploadTrigger').after(huCta);
    const HU_SEEN='linda-hu-cta-seen';
    let huBlinkT=0;
    function huSeen(){try{return localStorage.getItem(HU_SEEN)==='1';}catch(e){return true;}}
    function huBlinkStop(){if(huBlinkT){clearTimeout(huBlinkT);huBlinkT=0;}huCta.classList.remove('recommend');}
    function markHuSeen(){try{localStorage.setItem(HU_SEEN,'1');}catch(e){}huBlinkStop();}
    huCta.onclick=()=>{markHuSeen();openRewrite();};
    function syncHuCta(){
      const hasResult=!$('resultsContent').classList.contains('hidden')&&!$('btnAnalyze').classList.contains('loading');
      huCta.hidden=!hasResult;
      if(!hasResult||huSeen()){huBlinkStop();return;}
      if(!huCta.classList.contains('recommend')){
        huCta.classList.add('recommend');
        if(huBlinkT)clearTimeout(huBlinkT);
        huBlinkT=setTimeout(()=>{huBlinkT=0;huCta.classList.remove('recommend');},5000);
      }
    }
    new MutationObserver(syncHuCta).observe($('resultsContent'),{attributes:true,attributeFilter:['class']});
    new MutationObserver(syncHuCta).observe($('btnAnalyze'),{attributes:true,attributeFilter:['class']});
    new MutationObserver(syncHuCta).observe($('tabsBar'),{childList:true});
    document.addEventListener('linda-i18n',syncHuCta);
    $('textInput').addEventListener('input',()=>{huCta.hidden=true;huBlinkStop();});
    document.addEventListener('linda-route',e=>{if(e.detail&&e.detail.route!=='check'){huCta.hidden=true;huBlinkStop();}else syncHuCta();});
    $('styleInfo').setAttribute('role','status');$('styleInfo').setAttribute('aria-live','polite');
    auditSwitch.onclick=()=>navigate(route==='audit'?'history':'audit');
    // Observe actions opened by existing buttons (history links, settings, licence).
    let syncQueued=false;
    function syncLegacy(){
      if(syncQueued)return;syncQueued=true;
      queueMicrotask(()=>{syncQueued=false;if(transition)return;
        if($('lpLic').classList.contains('show'))activate('license');
        else if($('lpSet').classList.contains('show'))activate('settings');
        else if($('cabView').classList.contains('open'))activate(routeForPane(window._cabPane));
        else if(['settings','license',...Object.keys(paneMap)].includes(route))activate('check');
      });
    }
    const observer=new MutationObserver(syncLegacy);
    for(const id of ['lpSet','lpLic','cabView'])observer.observe($(id),{attributes:true,attributeFilter:['class']});
    $('cabView').querySelectorAll('.cab-tab').forEach(b=>b.addEventListener('click',()=>setTimeout(syncLegacy,0)));
    function translate(){
      document.querySelectorAll('[data-ld-text]').forEach(el=>el.textContent=T(el.dataset.ldText));
      $('desktopLanguage').value=window.LINDA_LANG||'en';$('desktopLanguage').setAttribute('aria-label',T('language'));
      nav.setAttribute('aria-label',T('work'));
      $('lpSet').setAttribute('aria-label',T('settings'));$('lpLic').setAttribute('aria-label',T('license'));$('cabView').setAttribute('aria-label',T(route));
      activate(route);
    }
    $('desktopLanguage').addEventListener('change',e=>document.querySelector(`#langSw button[data-l="${e.target.value}"]`).click());
    document.addEventListener('linda-i18n',translate);
    // Замки Trace/Humanize в боковом меню: иконка заменяется стилизованным замком, тултип ведёт в лицензию.
    const lockPath='M7 11V8a5 5 0 0 1 10 0v3 M5 11h14v10H5z M12 15v3';
    function syncNavLocks(){
      const licensed=!!((window.__lindaLicense||{}).licensed);
      for(const key of ['trace','humanize']){
        const b=nav.querySelector(`[data-route="${key}"]`);if(!b)continue;
        const p=b.querySelector('svg path');if(p)p.setAttribute('d',licensed?iconPaths[key]:lockPath);
        if(licensed)b.removeAttribute('title');else b.setAttribute('title',window.LINDA_T('pack_lock'));
      }
    }
    document.addEventListener('linda-i18n',()=>setTimeout(syncNavLocks,0));
    document.addEventListener('linda-license',syncNavLocks);
    document.addEventListener('linda-task',()=>setTimeout(syncNavLocks,0));
    syncNavLocks();
    const stop=node('button','btn-upload');stop.id='desktopStop';stop.type='button';stop.hidden=true;
    const stopCopy={ru:'Остановить',en:'Stop',pl:'Zatrzymaj'};
    const taskCopy={ru:'Идёт проверка · Показать',en:'Checking text · Show',pl:'Sprawdzanie tekstu · Pokaż'};
    const stoppedCopy={ru:'Проверка остановлена. Текст сохранён в поле.',en:'Check stopped. Your text is still in the editor.',pl:'Sprawdzanie zatrzymane. Tekst pozostał w edytorze.'};
    $('btnAnalyze').after(stop);
    const task=node('button');task.id='desktopTask';task.type='button';task.hidden=true;statusbar.insertBefore(task,statusbar.querySelector('#desktopServiceStatus'));
    const globalStop=node('button');globalStop.id='desktopGlobalStop';globalStop.type='button';globalStop.hidden=true;task.after(globalStop);
    task.onclick=()=>navigate(window.LINDA_tools.active[0]?.route||(!$('bCancel').disabled?'batch':'check'));
    function syncStop(){const checking=$('btnAnalyze').classList.contains('loading'),batch=!$('bCancel').disabled,jobs=window.LINDA_tools.active,busy=checking||batch||jobs.length;stop.hidden=!checking;task.hidden=!busy;globalStop.hidden=!busy;globalStop.disabled=!!jobs.length&&jobs.every(j=>j.stopping)&&!checking&&!batch;globalStop.textContent=window.LINDA_T(globalStop.disabled?'task_stopping':'task_stop');task.textContent=jobs.length||batch?window.LINDA_T('task_show'):(taskCopy[window.LINDA_LANG]||taskCopy.en);stop.textContent=stopCopy[window.LINDA_LANG]||stopCopy.en;}
    globalStop.onclick=()=>{if($('btnAnalyze').classList.contains('loading'))stop.click();if(!$('bCancel').disabled)$('bCancel').click();window.LINDA_tools.cancel().catch(()=>{globalStop.textContent=window.LINDA_T('task_retry_stop');});};
    stop.onclick=()=>{cancelCheck();$('statusIndicator').textContent=stoppedCopy[window.LINDA_LANG]||stoppedCopy.en;};
    new MutationObserver(syncStop).observe($('btnAnalyze'),{attributes:true,attributeFilter:['class']});
    new MutationObserver(syncStop).observe($('bCancel'),{attributes:true,attributeFilter:['disabled']});
    document.addEventListener('linda-task',syncStop);
    document.addEventListener('linda-i18n',syncStop);syncStop();
    window.LINDA_desktop={navigate,get route(){return route;},copy:COPY};
    // The first-run tour was removed: persistent instructions replace it.
    $('lpTourAgain').onclick=()=>navigate('help');
    // Only the model-download dialog is modal. Keep keyboard focus inside it.
    let setupWasOpen=false,setupFocus=null;
    const setupCard=$('lpSetup').querySelector('.lp-card');setupCard.tabIndex=-1;
    const setupControls=()=>[...setupCard.querySelectorAll('button,input,select,textarea,a[href],[tabindex="0"]')].filter(el=>!el.disabled&&el.getClientRects().length);
    function setupFocusState(){
      const open=$('lpSetup').classList.contains('show');
      if(open===setupWasOpen)return;setupWasOpen=open;
      window.LINDA_modalLock('setup',[shell,header,statusbar],open);
      if(open){setupFocus=document.activeElement;(setupControls()[0]||setupCard).focus();}
      else if(setupFocus?.isConnected)setupFocus.focus({preventScroll:true});
    }
    new MutationObserver(setupFocusState).observe($('lpSetup'),{attributes:true,attributeFilter:['class']});setupFocusState();
    $('lpSetup').addEventListener('keydown',e=>{if(e.key!=='Tab'||!setupWasOpen)return;const controls=setupControls();if(!controls.length){e.preventDefault();setupCard.focus();return;}const first=controls[0],last=controls[controls.length-1];if(e.shiftKey&&(document.activeElement===first||document.activeElement===setupCard)){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}});
    window.LINDA_applyI18n();translate();activate('check');
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();

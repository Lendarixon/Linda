(()=>{
 'use strict';
 const root=document.documentElement;
 root.dataset.theme='dark';
 try{let saved=localStorage.getItem('linda-site-theme');if(saved!=='light'&&saved!=='dark')saved=localStorage.getItem('linda-theme');if(saved==='light'||saved==='dark')root.dataset.theme=saved}catch(e){}
 document.querySelectorAll('.suite-header .theme-toggle').forEach(button=>button.addEventListener('click',()=>{
  const value=root.dataset.theme==='light'?'dark':'light';root.dataset.theme=value;
  try{localStorage.setItem('linda-site-theme',value)}catch(e){}
 }));
 // Mark the current section in the main navigation (same page in any language).
 const here=(location.pathname.split('/').pop()||'index.html').replace(/-(ru|pl)\.html$/,'.html').replace(/^(ru|pl)\.html$/,'index.html');
 const family={'business.html':'business.html','pricing.html':'pricing.html','downloads.html':'downloads.html','results.html':'results.html','detector-results.html':'results.html'};
 document.querySelectorAll('.suite-header nav a').forEach(a=>{const target=(a.getAttribute('href')||'').split('#')[0].replace(/-(ru|pl)\.html$/,'.html');if(target&&!a.classList.contains('nav-demo')&&target!=='index.html'&&family[here]===target)a.setAttribute('aria-current','page')});
 const menu=document.querySelector('.suite-header nav'),toggle=document.querySelector('.suite-header .menu-toggle');
 if(menu&&toggle){toggle.addEventListener('click',()=>{const open=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(open));menu.classList.toggle('is-open',open)});
  menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{menu.classList.remove('is-open');toggle.setAttribute('aria-expanded','false')}));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&toggle.getAttribute('aria-expanded')==='true'){menu.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');toggle.focus()}});
  document.addEventListener('click',e=>{if(toggle.getAttribute('aria-expanded')==='true'&&!menu.contains(e.target)&&!toggle.contains(e.target)){menu.classList.remove('is-open');toggle.setAttribute('aria-expanded','false')}});
 }
 // Horizontal strips (result tabs, phone start wall): fade the right edge while more content is hidden.
 document.querySelectorAll('.evidence-tabs,.start-wall').forEach(el=>{const check=()=>{const more=el.scrollWidth>el.clientWidth+2;el.classList.toggle('is-scrollable',more);el.classList.toggle('at-end',!more||el.scrollLeft+el.clientWidth>=el.scrollWidth-2)};check();el.addEventListener('scroll',check,{passive:true});addEventListener('resize',check)});
 document.querySelectorAll('[role="tablist"]').forEach(group=>{
  const tabs=[...group.querySelectorAll('[role="tab"]')];
  const isPlans=!!group.closest('.plan-widget');
  const select=(tab,updateURL=false)=>{tabs.forEach(item=>{const selected=item===tab;item.setAttribute('aria-selected',String(selected));item.tabIndex=selected?0:-1;const panel=document.getElementById(item.getAttribute('aria-controls'));if(panel)panel.hidden=!selected});
   if(isPlans){const app=tabs.indexOf(tab)===1?'probe':'detector';
    document.querySelectorAll('.language-switch a').forEach(link=>{const url=new URL(link.href);url.searchParams.set('app',app);link.href=url.href});
    if(updateURL){try{const url=new URL(location.href);url.searchParams.set('app',app);history.replaceState(null,'',url)}catch(e){}}
   }
  };
  tabs.forEach((tab,index)=>{tab.addEventListener('click',()=>select(tab,true));tab.addEventListener('keydown',event=>{
   let next;if(event.key==='ArrowRight')next=(index+1)%tabs.length;else if(event.key==='ArrowLeft')next=(index-1+tabs.length)%tabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=tabs.length-1;else return;
   event.preventDefault();select(tabs[next],true);tabs[next].focus();
  })});
  if(isPlans){const app=new URLSearchParams(location.search).get('app');select(tabs[app==='probe'?1:0])}
 });
 document.querySelectorAll('.catalogue-filters').forEach(group=>{
  const buttons=[...group.querySelectorAll('[data-category]')],cards=[...document.querySelectorAll('[data-product-category]')],count=document.querySelector('[data-catalogue-count]');
  buttons.forEach(button=>button.addEventListener('click',()=>{
   const category=button.dataset.category;
   buttons.forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
   cards.forEach(card=>{card.hidden=category!=='all'&&card.dataset.productCategory!==category});
   if(count)count.textContent=count.dataset.catalogueCount+' '+cards.filter(card=>!card.hidden).length;
  }));
 });
 // Metro pointer tilt: a pressed tile leans away from the press point.

 if(!matchMedia('(prefers-reduced-motion: reduce)').matches){

  document.querySelectorAll('.live-tile,.tool-card,.catalogue-card,.task-choice-card,.download-card').forEach(el=>{

   const reset=()=>{el.style.transform='';el.style.transition='transform .25s cubic-bezier(.1,.9,.2,1)'};

   el.addEventListener('pointerdown',e=>{const r=el.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5,k=r.width>420?3:7;

    el.style.transition='transform .08s ease-out';el.style.transform=`perspective(900px) rotateX(${(-y*k).toFixed(2)}deg) rotateY(${(x*k).toFixed(2)}deg) scale(.985)`});

   ['pointerup','pointerleave','pointercancel'].forEach(t=>el.addEventListener(t,reset));

  });

 }

 const still=matchMedia('(prefers-reduced-motion: reduce)').matches;

 // Pivot indicator that slides between tabs.

 document.querySelectorAll('.evidence-tabs').forEach(bar=>{

  if(still)return;const ink=document.createElement('span');ink.className='tab-ink';ink.setAttribute('aria-hidden','true');bar.appendChild(ink);bar.classList.add('has-ink');

  const place=()=>{const t=bar.querySelector('[aria-selected="true"]');if(!t)return;bar.style.setProperty('--ink-x',(t.offsetLeft)+'px');bar.style.setProperty('--ink-w',t.offsetWidth+'px')};

  place();new MutationObserver(place).observe(bar,{subtree:true,attributes:true,attributeFilter:['aria-selected']});addEventListener('resize',place);

 });

 // Product hero mock-ups play their short demonstration once they are on screen.

 document.querySelectorAll('.mock-search').forEach(box=>{const q=[...box.childNodes].find(n=>n.nodeType===3&&n.textContent.trim())||box.querySelector(':scope>span:not(.app-tile):not(:last-child)');

  if(q&&q.nodeType===3){const s=document.createElement('span');s.className='typed';s.textContent=q.textContent;q.replaceWith(s)}else if(q)q.classList.add('typed')});

 if(!still&&'IntersectionObserver' in window){const live=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-live');live.unobserve(e.target)}}),{threshold:.35});

  document.querySelectorAll('.product-stage').forEach(el=>live.observe(el))}

 // Progressive enhancement: content remains visible if JS or the observer is unavailable.
 if('IntersectionObserver' in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target)}}),{threshold:.08});
  document.querySelectorAll('.reveal').forEach(element=>observer.observe(element));
 }
})();
document.head.append(Object.assign(document.createElement('script'),{src:'count.js'}));

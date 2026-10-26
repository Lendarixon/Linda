(()=>{
 'use strict';
 const root=document.documentElement;
 try{const saved=localStorage.getItem('linda-site-theme');if(saved==='light'||saved==='dark')root.dataset.theme=saved}catch(e){}
 document.querySelectorAll('.suite-header .theme-toggle').forEach(button=>button.addEventListener('click',()=>{
  const value=root.dataset.theme==='light'?'dark':'light';root.dataset.theme=value;
  try{localStorage.setItem('linda-site-theme',value)}catch(e){}
 }));
 const menu=document.querySelector('.suite-header nav'),toggle=document.querySelector('.suite-header .menu-toggle');
 if(menu&&toggle){toggle.addEventListener('click',()=>{const open=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(open));menu.classList.toggle('is-open',open)});
  menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{menu.classList.remove('is-open');toggle.setAttribute('aria-expanded','false')}));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&toggle.getAttribute('aria-expanded')==='true'){menu.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');toggle.focus()}});
 }
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
 // Progressive enhancement: content remains visible if JS or the observer is unavailable.
 if('IntersectionObserver' in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target)}}),{threshold:.08});
  document.querySelectorAll('.reveal').forEach(element=>observer.observe(element));
 }
})();

// Aggregate counter: no cookies, no identifiers, nothing about the visitor is stored (see privacy.html).
(()=>{
 const END='https://ninjagovlad--linda-site-count-hit.us-east.modal.run';
 const q=new URLSearchParams(location.search);
 try{if(q.has('nocount'))localStorage.setItem('linda-nocount','1');if(localStorage.getItem('linda-nocount'))return}catch(e){}
 if(navigator.webdriver||navigator.globalPrivacyControl||navigator.doNotTrack==='1'||!navigator.sendBeacon)return;
 const send=(e,extra)=>navigator.sendBeacon(END,JSON.stringify({e,p:location.pathname,...extra}));
 let host='';try{host=new URL(document.referrer).hostname}catch(e){}
 send('view');
 if(host!==location.hostname)send('visit',{r:host,u:q.get('utm_source')||''});
 document.addEventListener('click',ev=>{
  const a=ev.target.closest&&ev.target.closest('a[href]');if(!a)return;
  const e=/buy\.polar\.sh/.test(a.href)?'buy':/(apps|get)\.microsoft\.com/.test(a.href)?'store':/\/releases(\/|$)|\.exe($|\?)/.test(a.href)?'download':'';
  if(e)send(e);
 },true);
})();

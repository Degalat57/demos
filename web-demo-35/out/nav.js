const b=document.querySelector('.nav-toggle'),l=document.getElementById('nav-list');
b.addEventListener('click',()=>{const o=b.getAttribute('aria-expanded')!=='true';b.setAttribute('aria-expanded',String(o));l.classList.toggle('open',o);if(o)l.querySelector('a').focus();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&b.getAttribute('aria-expanded')==='true'){b.click();b.focus();}});

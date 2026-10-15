document.querySelectorAll('.carousel').forEach(function(c){
 var t=c.querySelector('.track'),s=t.querySelectorAll('.slide'),d=c.querySelector('.dots'),i=0;
 s.forEach(function(_,k){var b=document.createElement('button');b.setAttribute('aria-label','Slide '+(k+1));
  b.onclick=function(){go(k)};d.appendChild(b)});
 function go(k){i=(k+s.length)%s.length;t.scrollTo({left:s[i].offsetLeft-t.offsetLeft,behavior:'smooth'});mark()}
 function mark(){d.querySelectorAll('button').forEach(function(b,k){b.setAttribute('aria-current',k===i)});c.dataset.index=i}
 c.querySelector('.prev').onclick=function(){go(i-1)};c.querySelector('.next').onclick=function(){go(i+1)};
 t.addEventListener('scroll',function(){var n=Math.round(t.scrollLeft/t.clientWidth);if(n!==i){i=n;mark()}});mark()});
var f=document.querySelector('form');if(f){f.onsubmit=function(e){e.preventDefault();
 document.getElementById('status').textContent=f.checkValidity()?'Thanks - message ready to send.':'Please fill all fields.'}}

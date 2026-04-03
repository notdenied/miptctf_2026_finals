(function(){
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  function init() {
    const form = document.getElementById('register-form');
    if(!form) return;
  const pwd = form.querySelector('input[name="pwd"]');
  const pwd2 = form.querySelector('input[name="pwd2"]');
  const btn = document.getElementById('create-btn');

  function showSparkle(x,y){
    const s = document.createElement('div');
    s.className = 'sparkle';
    s.style.left = (x - 4) + 'px';
    s.style.top = (y - 4) + 'px';
    document.body.appendChild(s);
    setTimeout(()=>document.body.removeChild(s),800);
  }

  form.addEventListener('submit', function(ev){
    if(pwd && pwd2 && pwd.value !== pwd2.value){
      ev.preventDefault();
      btn.classList.add('pulse');
      setTimeout(()=>btn.classList.remove('pulse'),600);
      const r = btn.getBoundingClientRect();
      showSparkle(r.left + r.width/2, r.top + 8);
    }
  });

  btn.addEventListener('mouseenter', function(e){
    btn.classList.add('primary-glow');
  });
    btn.addEventListener('mouseleave', function(e){
      btn.classList.remove('primary-glow');
    });
  }
})();

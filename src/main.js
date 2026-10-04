(() => {
  const $ = (s, c = document) => c.querySelector(s), $$ = (s, c = document) => [...c.querySelectorAll(s)];
  // header
  const hdr = $('#hdr');
  const onScroll = () => hdr && hdr.classList.toggle('is-scrolled', scrollY > 10);
  addEventListener('scroll', onScroll, { passive: true }); onScroll();
  // mobile menu
  const burger = $('.burger'), mnav = $('#mnav');
  burger && burger.addEventListener('click', () => {
    const open = burger.getAttribute('aria-expanded') !== 'true';
    burger.setAttribute('aria-expanded', open); mnav.hidden = !open;
    document.body.style.overflow = open ? 'hidden' : '';
  });
  // "Další" dropdown (touch)
  $$('.more__btn').forEach(b => b.addEventListener('click', e => {
    const m = b.parentElement; const o = !m.classList.contains('is-open');
    m.classList.toggle('is-open', o); b.setAttribute('aria-expanded', o); e.stopPropagation();
  }));
  document.addEventListener('click', () => $$('.more.is-open').forEach(m => m.classList.remove('is-open')));
  // reveal
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
  }), { rootMargin: '0px 0px -8% 0px', threshold: .08 });
  $$('.reveal,.clip-reveal,.pop,.rings,#stack').forEach(el => io.observe(el));
  $$('.bento .pop').forEach((el, i) => el.style.setProperty('--d', (([3, 0, 5, 1, 6, 2, 4][i % 7]) * .08) + 's'));
  // category hover preview (desktop)
  const pv = $('.cat-preview');
  if (pv && matchMedia('(hover:hover) and (min-width:701px)').matches) {
    const img = $('img', pv); let x = 0, y = 0, cx = 0, cy = 0, raf = 0;
    const loop = () => { cx += (x - cx) * .16; cy += (y - cy) * .16; pv.style.left = cx + 'px'; pv.style.top = cy + 'px';
      raf = Math.abs(x - cx) + Math.abs(y - cy) > .5 ? requestAnimationFrame(loop) : 0; };
    $$('.cat').forEach(c => {
      c.addEventListener('mouseenter', e => { img.src = c.dataset.img; pv.classList.add('on'); x = cx = e.clientX + 170; y = cy = e.clientY; });
      c.addEventListener('mousemove', e => { x = e.clientX + 170; y = e.clientY; if (!raf) raf = requestAnimationFrame(loop); });
      c.addEventListener('mouseleave', () => pv.classList.remove('on'));
    });
  }
  // magnetic buttons
  if (matchMedia('(hover:hover)').matches) $$('.magnetic').forEach(b => {
    b.addEventListener('mousemove', e => { const r = b.getBoundingClientRect();
      b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * .18}px,${(e.clientY - r.top - r.height / 2) * .3}px)`; });
    b.addEventListener('mouseleave', () => b.style.transform = '');
  });
  // reviews
  const rv = $$('.rv');
  if (rv.length) {
    let i = 0, t; const cnt = $('.rv-count b');
    const show = n => { rv[i].classList.remove('is-on'); i = (n + rv.length) % rv.length; rv[i].classList.add('is-on'); cnt.textContent = i + 1; };
    const auto = () => { clearInterval(t); t = setInterval(() => show(i + 1), 8000); };
    $('.rv-next').onclick = () => { show(i + 1); auto(); }; $('.rv-prev').onclick = () => { show(i - 1); auto(); }; auto();
  }
  // lightbox
  const lb = $('#lb');
  if (lb) {
    let list = [], k = 0; const im = $('img', lb), cap = $('.lb__c', lb);
    const open = n => { k = (n + list.length) % list.length; const a = list[k]; im.src = a.href; cap.textContent = a.dataset.cap || ''; lb.hidden = false; document.body.style.overflow = 'hidden'; };
    const close = () => { lb.hidden = true; im.src = ''; document.body.style.overflow = ''; };
    document.addEventListener('click', e => {
      const a = e.target.closest('a.lbx'); if (!a) return; e.preventDefault();
      const g = a.closest('.gal'); list = g ? $$('a.lbx', g) : [a]; open(list.indexOf(a));
    });
    $('.lb__x', lb).onclick = close; $('.lb__n', lb).onclick = () => open(k + 1); $('.lb__p', lb).onclick = () => open(k - 1);
    lb.addEventListener('click', e => { if (e.target === lb) close(); });
    addEventListener('keydown', e => { if (lb.hidden) return; if (e.key === 'Escape') close(); if (e.key === 'ArrowRight') open(k + 1); if (e.key === 'ArrowLeft') open(k - 1); });
  }
})();

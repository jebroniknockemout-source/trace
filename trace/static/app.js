const $ = (s) => document.querySelector(s);
const frame = $('#frame'), preview = $('#preview'), status = $('#status'), results = $('#results');
let busy = false, blobURL;

const el = (tag, cls, ...kids) => { const n = document.createElement(tag); if (cls) n.className = cls; n.append(...kids); return n; };
const link = (href, cls, ...kids) => { const a = el('a', cls, ...kids); a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; };
const thumb = (url) => {
  const img = el('img'); img.src = url; img.loading = 'lazy'; img.alt = ''; img.referrerPolicy = 'no-referrer';
  const a = link(url, 'thumb', img); img.onerror = () => a.remove(); return a;
};
const block = (title, body) => el('section', 'block', el('h2', '', title), body);

function render(d) {
  results.replaceChildren();
  if (d.best_guess.length) results.append(block('Best guess', el('p', '', d.best_guess.join(', '))));
  if (d.topics.length) results.append(block('Topics on matching pages', el('div', 'chips',
    ...d.topics.map((t) => link('https://www.google.com/search?q=' + encodeURIComponent(t), 'chip', t)))));
  if (d.pages.length) results.append(block('Pages with this image', el('ul', 'pages',
    ...d.pages.map((p) => el('li', '', link(p.url, '',
      el('span', 'domain', p.domain, ...(p.exact ? [el('span', 'tag', 'exact copy')] : [])),
      el('span', 'title', p.title)))))));
  if (d.exact.length) results.append(block('Exact copies', el('div', 'grid', ...d.exact.map((u) => thumb(u)))));
  if (d.similar.length) results.append(block('Similar images', el('div', 'grid', ...d.similar.map((u) => thumb(u)))));
  if (!results.children.length) results.append(el('p', 'empty',
    'No matches. The image may not be published online, or it may be too new or too cropped. Try a clearer, uncropped version.'));
}

async function run(fd, src) {
  if (busy) return;
  busy = true; results.replaceChildren(); status.className = 'status'; status.textContent = 'Searching…';
  preview.src = src; preview.hidden = false;
  frame.classList.add('has-image', 'busy'); $('#reset').hidden = false;
  try {
    const res = await fetch('/api/search', { method: 'POST', body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Something went wrong. Try again.');
    status.textContent = ''; render(data);
  } catch (e) { status.className = 'status error'; status.textContent = e.message; }
  busy = false; frame.classList.remove('busy');
}

async function shrink(file) {  // downscale before upload: faster on mobile data
  try {
    const bmp = await createImageBitmap(file), s = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
    const c = document.createElement('canvas'); c.width = Math.round(bmp.width * s); c.height = Math.round(bmp.height * s);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    return (await new Promise((r) => c.toBlob(r, 'image/jpeg', 0.88))) || file;
  } catch { return file; }
}

async function pick(file) {
  if (!file || busy) return;
  if (blobURL) URL.revokeObjectURL(blobURL);
  blobURL = URL.createObjectURL(file);
  const fd = new FormData(); fd.append('image', await shrink(file), 'photo.jpg');
  run(fd, blobURL);
}

$('#take').onclick = () => $('#camera').click();
$('#choose').onclick = () => $('#file').click();
for (const id of ['camera', 'file']) $('#' + id).onchange = (e) => { pick(e.target.files[0]); e.target.value = ''; };
$('#url-form').onsubmit = (e) => {
  e.preventDefault();
  const u = $('#url').value.trim(); if (!u) return;
  const fd = new FormData(); fd.append('image_url', u); run(fd, u);
};
preview.onerror = () => { preview.hidden = true; };
$('#reset').onclick = () => {
  preview.hidden = true; preview.removeAttribute('src'); frame.classList.remove('has-image');
  results.replaceChildren(); status.textContent = ''; $('#reset').hidden = true; $('#url').value = '';
};
frame.ondragover = (e) => e.preventDefault();
frame.ondrop = (e) => { e.preventDefault(); pick(e.dataTransfer.files[0]); };

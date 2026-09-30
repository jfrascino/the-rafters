import { esc, load, tryLoad, videoCard, bindVideos, photoFig, bindPhotos } from '../ui.js';

export default async function vault(main, _args, core) {
  const media = (await tryLoad('media.json')) || { videos: core.videos || [], photos: [] };
  const vids = media.videos || [];
  const photos = media.photos || [];
  const kinds = [['', 'Everything'], ['full_game', 'Full games'], ['highlights', 'Highlights'], ['moment', 'Moments'], ['documentary', 'Documentaries'], ['interview', 'Interviews']].filter(([k]) => !k || vids.some((v) => v.kind === k));
  const eras = core.eras || [];
  main.innerHTML = `<div data-title="Vault"></div>
  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${vids.length} videos · ${photos.length} photos</span><h1 class="h1">The vault</h1></div>
      <span class="aside">Full games, highlights and the moments that still give you chills. Videos play from the uploader's YouTube channel.</span></div>
    <div class="filters">
      <input type="search" id="vq" placeholder="Search: Duke, Kemba, 1999, Final Four…" autocomplete="off" aria-label="Search videos">
      <select id="vera" aria-label="Era"><option value="">All eras</option>${eras.map((e, i) => `<option value="${i}">${esc(e.name)}</option>`).join('')}</select>
    </div>
    <div class="chips" id="vk" style="margin-bottom:22px">${kinds.map(([k, l], i) => `<button class="chip${i ? '' : ' on'}" data-k="${k}">${l}</button>`).join('')}</div>
    <div class="vids" id="vg"></div>
    <div style="display:flex;justify-content:center;margin-top:24px"><button class="btn" id="vmore" hidden>Show more</button></div>
  </div></section>
  ${photos.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Openly licensed photos, credited</span><h2 class="h2">Photographs</h2></div></div>
    <div class="photos" id="pg">${photos.map(photoFig).join('')}</div>
  </div></section>` : ''}`;
  const $ = (s) => main.querySelector(s);
  let kind = '', shown = 36;
  const render = () => {
    const q = $('#vq').value.trim().toLowerCase();
    const era = eras[$('#vera').value];
    const list = vids.filter((v) => (!kind || v.kind === kind) && (!era || (v.season >= era.from && v.season <= era.to)) && (!q || `${v.title} ${v.description || ''} ${v.opponent || ''} ${(v.players || []).join(' ')} ${v.season || ''} ${v.round || ''}`.toLowerCase().includes(q)));
    $('#vg').innerHTML = list.slice(0, shown).map(videoCard).join('') || '<div class="empty">No videos match.</div>';
    $('#vmore').hidden = list.length <= shown;
  };
  bindVideos($('#vg'), vids);
  $('#vq').addEventListener('input', () => { shown = 36; render(); });
  $('#vera').addEventListener('input', () => { shown = 36; render(); });
  $('#vk').addEventListener('click', (e) => { const b = e.target.closest('[data-k]'); if (!b) return; kind = b.dataset.k; main.querySelectorAll('#vk .chip').forEach((c) => c.classList.toggle('on', c === b)); shown = 36; render(); });
  $('#vmore').addEventListener('click', () => { shown += 36; render(); });
  render();
  if (photos.length) bindPhotos($('#pg'), photos);
}

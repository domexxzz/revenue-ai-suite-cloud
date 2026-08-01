/**
 * flow_inspect_helper.js — ดูว่าการ์ดในหน้า Google Flow มีปุ่มอะไรบ้าง
 *
 * ตัวโหลดคลิปต้องรู้ว่าปุ่ม ⋮ ของ Flow ชื่ออะไร ถึงจะกดถูก แต่ Flow เป็น Labs
 * เปลี่ยน UI บ่อย และชื่อปุ่มไม่ได้อยู่ในข้อความที่เห็น มันอยู่ใน aria-label
 * ไฟล์นี้อ่านออกมาให้ แล้ววางในกล่องที่คัดลอกได้ทันที ไม่ต้องไปงมใน Console
 *
 * ปลอดภัย: อ่านอย่างเดียว มีแค่การเลื่อนหน้ากับ hover ไม่กดปุ่มใดทั้งสิ้น
 * จึงไม่มีทางเผลอเปิดคลิปหรือลบอะไร
 */

(async () => {
  'use strict';

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const hud = document.createElement('div');
  hud.style.cssText = [
    'position:fixed', 'z-index:2147483647', 'right:16px', 'bottom:16px',
    'background:#101418', 'color:#e8f0ee', 'font:13px/1.5 system-ui,sans-serif',
    'padding:14px 16px', 'border-radius:12px', 'width:min(560px,90vw)',
    'box-shadow:0 8px 30px rgba(0,0,0,.45)', 'border:1px solid #2b3a36',
  ].join(';');
  hud.innerHTML =
    '<b style="color:#2dd4bf">🔎 ตรวจปุ่มในหน้า Flow</b>' +
    '<div id="fi-msg" style="margin-top:8px">กำลังอ่าน…</div>';
  document.body.appendChild(hud);
  const say = (t) => { hud.querySelector('#fi-msg').textContent = t; };

  if (!/(^|\.)labs\.google$/.test(location.hostname)) {
    hud.querySelector('#fi-msg').innerHTML =
      '<b style="color:#fbbf24">ยังไม่ได้อยู่บนหน้า Google Flow</b><br>' +
      'ปุ่มนี้ต้อง <b>ลาก</b> ขึ้นแถบบุ๊กมาร์กก่อน แล้วค่อยกดบนหน้า Flow';
    return;
  }

  // หาไทล์แบบเดียวกับตัวโหลด เพื่อให้รายงานตรงกับสิ่งที่ตัวโหลดเห็นจริง ๆ
  function findTiles() {
    const vw = innerWidth;
    const vh = innerHeight;
    const media = [...document.querySelectorAll('img, video')].filter((m) => {
      const r = m.getBoundingClientRect();
      return r.width >= 100 && r.height >= 100 &&
             r.width <= vw * 0.6 && r.height <= vh * 0.9;
    });
    const tiles = new Set();
    for (const m of media) {
      const mr = m.getBoundingClientRect();
      const mArea = mr.width * mr.height;
      let el = m;
      let best = null;
      for (let up = 0; up < 5 && el.parentElement; up++) {
        el = el.parentElement;
        const r = el.getBoundingClientRect();
        if (r.width > vw * 0.7 || r.height > vh * 0.9) break;
        if (el.querySelectorAll('img, video').length > 1) break;
        if (r.width * r.height > mArea * 3) break;
        best = el;
      }
      if (best) tiles.add(best);
    }
    return [...tiles];
  }

  async function hover(el) {
    const r = el.getBoundingClientRect();
    const at = { bubbles: true, cancelable: true,
                 clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
    for (const type of ['pointerover', 'pointerenter', 'mouseover', 'mouseenter',
                        'pointermove', 'mousemove']) {
      const Ctor = type.startsWith('pointer') && window.PointerEvent
        ? PointerEvent : MouseEvent;
      el.dispatchEvent(new Ctor(type, at));
    }
    await sleep(500);   // รอให้ปุ่มที่โผล่ตอน hover เรนเดอร์เสร็จก่อนอ่าน
  }

  const tiles = findTiles();
  const report = { url: location.href, ไทล์ที่เจอ: tiles.length, การ์ด: [] };

  for (let i = 0; i < Math.min(3, tiles.length); i++) {
    const tile = tiles[i];
    tile.scrollIntoView({ block: 'center' });
    await sleep(400);
    await hover(tile);
    say(`อ่านการ์ดที่ ${i + 1}/${Math.min(3, tiles.length)}…`);

    report.การ์ด.push({
      ปุ่ม: [...tile.querySelectorAll('button, [role="button"], a')].map((b) => ({
        tag: b.tagName,
        text: (b.textContent || '').trim().slice(0, 30),
        aria: b.getAttribute('aria-label'),
        title: b.getAttribute('title'),
        testid: b.getAttribute('data-testid'),
        cls: (b.className || '').toString().slice(0, 60),
        มองเห็น: b.offsetParent !== null,
      })),
      // ไอคอนบางตัวไม่ได้อยู่ใน <button> แต่เป็น span ที่มีชื่อไอคอนเป็นข้อความ
      ไอคอน: [...tile.querySelectorAll('span, i, svg')]
        .map((s) => (s.textContent || '').trim())
        .filter((t) => t && t.length < 24),
    });
  }

  const text = JSON.stringify(report, null, 1);
  hud.querySelector('#fi-msg').innerHTML =
    `เจอไทล์ ${tiles.length} ชิ้น — คัดลอกข้อความข้างล่างไปวางให้ผมได้เลย` +
    '<textarea id="fi-out" readonly style="width:100%;height:180px;margin-top:8px;' +
    'background:#0b0f12;color:#cfe;border:1px solid #2b3a36;border-radius:8px;' +
    'padding:8px;font:12px/1.4 ui-monospace,monospace"></textarea>' +
    '<div style="display:flex;gap:8px;margin-top:8px">' +
    '<button id="fi-copy" style="flex:1;padding:6px;border-radius:8px;' +
    'border:1px solid #3d4f4a;background:#1b2724;color:#e8f0ee;cursor:pointer">' +
    '📋 คัดลอก</button>' +
    '<button id="fi-close" style="flex:1;padding:6px;border-radius:8px;' +
    'border:1px solid #3d4f4a;background:#1b2724;color:#e8f0ee;cursor:pointer">' +
    'ปิด</button></div>';
  hud.querySelector('#fi-out').value = text;
  hud.querySelector('#fi-copy').onclick = async () => {
    const ta = hud.querySelector('#fi-out');
    ta.select();
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      document.execCommand('copy');   // เผื่อหน้าไม่อนุญาต clipboard API
    }
    hud.querySelector('#fi-copy').textContent = '✅ คัดลอกแล้ว';
  };
  hud.querySelector('#fi-close').onclick = () => hud.remove();
  console.log('[flow-inspect]', report);
})();

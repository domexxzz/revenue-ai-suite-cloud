/**
 * flow_download_helper.js — กดดาวน์โหลดสื่อทุกชิ้นในหน้า Google Flow
 *
 * ใช้ยังไง
 *   1. เปิดโปรเจกต์ Flow ใน Chrome ปกติของคุณ (ที่ล็อกอินอยู่แล้ว)
 *   2. กด F12 → แท็บ Console
 *   3. วางไฟล์นี้ทั้งอัน แล้ว Enter
 *
 * สคริปต์ทำงานบนหน้าที่คุณเปิดอยู่เอง — ไม่มีเบราว์เซอร์อัตโนมัติ ไม่มีการล็อกอินผ่าน
 * โปรแกรม จึงไม่ไปยุ่งกับระบบตรวจจับใด ๆ ของ Google
 *
 * ⚠️ ยังเป็นการโหลดเป็นชุด ซึ่งอาจขัด ToS ของ Flow — จึงหน่วง 3-5 วิต่อไฟล์
 *    และจำกัดจำนวนต่อรอบ อย่าถอดตัวจำกัดออก
 *
 * ตั้งค่าให้ Chrome โหลดลง G:\My Drive\Lemed\ ก่อน แล้วปิด "Ask where to save"
 * จากนั้น flow_watch.py จะจัดไฟล์เข้าโฟลเดอร์แพลตฟอร์มให้เอง
 */

(async () => {
  'use strict';

  // ── ตัวจำกัด — อย่าถอดออก ────────────────────────────────────────────────
  const MAX_PER_RUN = 15;      // ดาวน์โหลดสูงสุดต่อรอบ
  const MIN_DELAY_MS = 3000;   // หน่วงขั้นต่ำต่อไฟล์
  const MAX_DELAY_MS = 5000;

  // ข้อความบนเมนู — Flow เป็น Labs ปรับ UI บ่อย ถ้าหาไม่เจอให้แก้ตรงนี้
  const DOWNLOAD_LABELS = ['ดาวน์โหลด', 'Download'];
  const MENU_LABELS = ['more_vert', 'ตัวเลือกเพิ่มเติม', 'More options', 'เพิ่มเติม'];

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const humanDelay = () =>
    sleep(MIN_DELAY_MS + Math.random() * (MAX_DELAY_MS - MIN_DELAY_MS));

  // ── แถบแสดงความคืบหน้า ───────────────────────────────────────────────────
  const hud = document.createElement('div');
  hud.style.cssText = [
    'position:fixed', 'z-index:2147483647', 'right:16px', 'bottom:16px',
    'background:#101418', 'color:#e8f0ee', 'font:13px/1.5 system-ui,sans-serif',
    'padding:14px 16px', 'border-radius:12px', 'min-width:250px',
    'box-shadow:0 8px 30px rgba(0,0,0,.45)', 'border:1px solid #2b3a36',
  ].join(';');
  hud.innerHTML =
    '<b style="color:#2dd4bf">⬇️ Flow Download Helper</b>' +
    '<div id="fdh-msg" style="margin-top:8px">กำลังเริ่ม…</div>' +
    '<button id="fdh-stop" style="margin-top:10px;width:100%;padding:6px;' +
    'border-radius:8px;border:1px solid #3d4f4a;background:#1b2724;' +
    'color:#e8f0ee;cursor:pointer">หยุด</button>';
  document.body.appendChild(hud);

  let stopped = false;
  hud.querySelector('#fdh-stop').onclick = () => {
    stopped = true;
    say('กำลังหยุด…');
  };
  const say = (t) => {
    const el = hud.querySelector('#fdh-msg');
    if (el) el.textContent = t;
    console.log('[flow-helper]', t);
  };

  // ── หาไทล์สื่อ ───────────────────────────────────────────────────────────
  // ไทล์ = การ์ดที่มี <img>/<video> อยู่ข้างใน และไม่ได้ซ้อนไทล์อื่น
  function findTiles() {
    const media = [...document.querySelectorAll('img, video')];
    const tiles = new Set();
    for (const m of media) {
      let el = m;
      for (let up = 0; up < 6 && el; up++) {
        el = el.parentElement;
        if (!el) break;
        const r = el.getBoundingClientRect();
        if (r.width > 120 && r.height > 120) {
          tiles.add(el);
          break;
        }
      }
    }
    return [...tiles];
  }

  function findByText(root, labels) {
    const nodes = [...root.querySelectorAll('button, [role="button"], [role="menuitem"], span, div')];
    for (const label of labels) {
      const hit = nodes.find((n) => {
        const t = (n.textContent || '').trim();
        return t === label || t.startsWith(label);
      });
      if (hit) return hit;
    }
    return null;
  }

  // ── เริ่มทำงาน ───────────────────────────────────────────────────────────
  const tiles = findTiles();
  say(`เจอสื่อ ${tiles.length} ชิ้น — เริ่มดาวน์โหลด (สูงสุด ${MAX_PER_RUN})`);
  if (!tiles.length) {
    say('หาไทล์สื่อไม่เจอ — เลื่อนหน้าให้เห็นสื่อก่อนแล้วลองใหม่');
    return;
  }

  let ok = 0;
  let fail = 0;

  for (let i = 0; i < tiles.length && ok < MAX_PER_RUN && !stopped; i++) {
    const tile = tiles[i];
    say(`[${i + 1}/${tiles.length}] สำเร็จ ${ok} · พลาด ${fail}`);

    tile.scrollIntoView({ block: 'center', behavior: 'smooth' });
    await sleep(600);
    tile.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
    await sleep(400);

    // เปิดเมนู ⋮ ของไทล์นี้
    let menuBtn = findByText(tile, MENU_LABELS);
    if (!menuBtn) {
      const btns = tile.querySelectorAll('button, [role="button"]');
      menuBtn = btns.length ? btns[btns.length - 1] : null;
    }
    if (!menuBtn) { fail++; continue; }

    menuBtn.click();
    await sleep(700);

    // กด "ดาวน์โหลด" ในเมนูที่เพิ่งเปิด (เมนูมัก render ที่ body)
    const item = findByText(document.body, DOWNLOAD_LABELS);
    if (!item) {
      document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      fail++;
      await sleep(500);
      continue;
    }

    item.click();
    ok++;
    await humanDelay();   // หน่วงแบบคน — กันยิงถี่
  }

  say(`เสร็จ — ดาวน์โหลด ${ok} ชิ้น${fail ? ` · ข้าม ${fail}` : ''}`);
  console.log('[flow-helper] เสร็จแล้ว ไฟล์จะไปอยู่ในโฟลเดอร์ดาวน์โหลดของ Chrome');
  setTimeout(() => hud.remove(), 12000);
})();

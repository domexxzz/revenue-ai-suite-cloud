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
  // ไทล์ = การ์ดที่หุ้ม media ชิ้นเดียว
  //
  // เวอร์ชันแรกไต่ขึ้นไปจนเจอ element ที่ใหญ่กว่า 120x120 แล้วหยุด — ทดสอบกับหน้า
  // จริงของ Google แล้วพบว่า "ไทล์" แรกที่ได้คือทั้งหน้า (1920x945 มี media 86 ชิ้น
  // ปุ่ม 65 ปุ่ม) เพราะ DOM จริงมี wrapper ซ้อนหลายชั้นที่ใหญ่เกินเกณฑ์ทันที
  // จึงต้องกันสามอย่าง: อย่าโตเกินสัดส่วนของ media, อย่าหุ้ม media มากกว่าหนึ่งชิ้น
  // (แปลว่าเป็น grid) และอย่าใหญ่เกือบเต็มจอ
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
        if (r.width > vw * 0.7 || r.height > vh * 0.9) break;   // เกือบเต็มจอ = ไม่ใช่การ์ด
        if (el.querySelectorAll('img, video').length > 1) break; // หุ้มหลายชิ้น = grid
        if (r.width * r.height > mArea * 3) break;               // โตเกินตัว media
        best = el;
      }
      if (best) tiles.add(best);
    }
    return [...tiles];
  }

  // หาปุ่ม/เมนูจากข้อความ
  //
  // เวอร์ชันแรกเอา match แรกใน document order ซึ่งคือ div ที่ "ห่อ" เมนูอยู่ ไม่ใช่
  // ตัวเมนูเอง — เพราะ textContent ของกล่องข้างนอกก็เท่ากับข้อความข้างในเป๊ะ พอคลิก
  // กล่องข้างนอก handler ที่ผูกไว้กับลูกจึงไม่ทำงาน แต่สคริปต์นับว่าสำเร็จ ทดสอบแล้ว
  // ได้ ok=4 ทั้งที่ไม่มีไฟล์ถูกโหลดสักไฟล์
  //
  // จึงต้องเลือกสามชั้น: ชนิดที่กดได้จริงมาก่อน → ข้อความตรงเป๊ะมาก่อนขึ้นต้นด้วย →
  // ตัวที่ลึกที่สุดมาก่อน (ไม่มีลูกที่ข้อความเหมือนกัน)
  const CLICKABLE = ['[role="menuitem"]', 'button', '[role="button"]', 'a', 'li',
                     'span', 'div'];

  function findByText(root, labels) {
    for (const label of labels) {
      for (const sel of CLICKABLE) {
        const hits = [...root.querySelectorAll(sel)].filter((n) => {
          const t = (n.textContent || '').trim();
          return t === label || t.startsWith(label);
        });
        if (!hits.length) continue;
        const exact = hits.filter((n) => (n.textContent || '').trim() === label);
        const pool = exact.length ? exact : hits;
        // ตัวที่ไม่มีตัวอื่นในกองซ้อนอยู่ข้างใน = ตัวจริง ไม่ใช่กล่องห่อ
        const deepest = pool.find((n) => !pool.some((o) => o !== n && n.contains(o)));
        return deepest || pool[pool.length - 1];
      }
    }
    return null;
  }

  // ── เริ่มทำงาน ───────────────────────────────────────────────────────────
  // กันกดผิดหน้า: ปุ่มในแอปเป็น "ของที่ต้องลาก" ไม่ใช่ปุ่มสั่งงาน พอกดมันเลย
  // รันบนหน้าแอปเอง แล้วไปไล่หา media ของหน้านั้นแทน ซึ่งไม่มีวันเจอคลิปจาก Flow
  // เช็คแค่โฮสต์ ไม่เช็ค path เพราะ Labs ย้าย path บ่อยกว่าโดเมน
  if (!/(^|\.)labs\.google$/.test(location.hostname)) {
    say('ยังไม่ได้อยู่บนหน้า Google Flow');
    hud.querySelector('#fdh-msg').innerHTML =
      '<b style="color:#fbbf24">ยังไม่ได้อยู่บนหน้า Google Flow</b><br>' +
      'ปุ่มนี้ต้อง <b>ลาก</b> ขึ้นแถบบุ๊กมาร์กก่อน (ไม่ใช่กด)<br>' +
      'แล้วค่อยเปิดโปรเจกต์ใน Flow และกดบุ๊กมาร์กนั้น';
    hud.querySelector('#fdh-stop').textContent = 'ปิด';
    hud.querySelector('#fdh-stop').onclick = () => hud.remove();
    return;
  }

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

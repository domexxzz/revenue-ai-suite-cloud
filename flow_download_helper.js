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
  //
  // 'download' คือชื่อ ligature ของไอคอน ซึ่ง Material วางไว้ติดหน้าป้ายกำกับโดยไม่มี
  // ตัวคั่น ข้อความจริงของรายการเมนูจึงเป็น "downloadดาวน์โหลด" — เดิมจับด้วย
  // startsWith('ดาวน์โหลด') อย่างเดียวเลยไม่เจอ ทั้งที่เมนูเปิดอยู่ตรงหน้า
  const DOWNLOAD_LABELS = ['ดาวน์โหลด', 'download', 'Download'];

  // เมนูย่อยหลังกด "ดาวน์โหลด" — เรียงตามลำดับที่อยากได้ ตัวแรกที่เจอชนะ
  // ตั้งใจไม่ใส่ 270p (เป็น GIF) และไม่เอา 1080p/4K ที่เป็นการอัปสเกลจากต้นฉบับ
  const QUALITY_LABELS = ['ขนาดตั้งเดิม', 'Original size', 'Original'];
  // บนหน้าจริง ปุ่มเมนูมี textContent ว่า "more_vertเพิ่มเติม" — Material วางชื่อ
  // ligature ของไอคอนไว้ติดกับป้ายกำกับโดยไม่มีตัวคั่น จึงจับด้วย startsWith ได้
  const MENU_LABELS = ['more_vert', 'more_horiz', 'ตัวเลือกเพิ่มเติม', 'More options',
                       'เพิ่มเติม', 'ตัวเลือก', 'Options', 'overflow'];

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
        // includes เป็นด่านสุดท้าย เพราะข้อความจริงอาจมีชื่อไอคอนนำหน้าและมีคำอื่น
        // ต่อท้าย เช่น "downloadดาวน์โหลดวิดีโอ" — แต่ยังจัดลำดับ exact > startsWith
        // ไว้ข้างล่าง จึงไม่กลายเป็นการจับมั่ว
        const hits = [...root.querySelectorAll(sel)].filter((n) => {
          const t = (n.textContent || '').trim();
          if (t === label || t.startsWith(label) || t.includes(label)) return true;
          // ปุ่มไอคอนไม่มีข้อความ ชื่อจริงอยู่ใน aria-label
          const aria = (n.getAttribute('aria-label') || '').trim();
          return aria === label || aria.startsWith(label) || aria.includes(label);
        });
        if (!hits.length) continue;
        // ตรงเป๊ะมาก่อน ขึ้นต้นด้วยมาถัดมา แล้วค่อยเป็นแค่มีคำนั้นอยู่
        const txt = (n) => (n.textContent || '').trim();
        let pool = hits.filter((n) => txt(n) === label);
        if (!pool.length) pool = hits.filter((n) => txt(n).startsWith(label));
        if (!pool.length) pool = hits;
        // ในชั้นเดียวกัน ข้อความสั้นกว่า = มีคำเกินน้อยกว่า = ตรงกับที่ขอมากกว่า
        // เมนูจริงมีทั้ง "ดาวน์โหลด" และ "ดาวน์โหลดต้นฉบับ" การเรียงตาม DOM จะได้
        // อันไหนก็ได้แล้วแต่ลำดับ ซึ่งไม่ใช่การเลือก
        pool = [...pool].sort((a, b) => txt(a).length - txt(b).length);
        // ตัวที่ไม่มีตัวอื่นในกองซ้อนอยู่ข้างใน = ตัวจริง ไม่ใช่กล่องห่อ
        const deepest = pool.find((n) => !pool.some((o) => o !== n && n.contains(o)));
        return deepest || pool[pool.length - 1];
      }
    }
    return null;
  }

  // รอจนกว่าเงื่อนไขจะเป็นจริง แทนการเช็คครั้งเดียวแล้วยอมแพ้
  //
  // รอบแรกใช้ sleep คงที่ (400ms รอ hover, 700ms รอเมนู) แล้วเช็คทีเดียว รันบนหน้า
  // Flow จริงได้ สำเร็จ 1 พลาด 9 — เพราะปุ่ม ⋮ กับเมนูใช้เวลาเรนเดอร์ไม่เท่ากันทุกครั้ง
  // เช็คตอนที่ยังไม่ขึ้นก็คือพลาดทันทีทั้งที่อีก 200ms มันจะมา
  async function waitFor(fn, ms) {
    const until = Date.now() + ms;
    for (;;) {
      const v = fn();
      if (v) return v;
      if (Date.now() > until) return null;
      await sleep(120);
    }
  }

  // hover จริง ๆ ไม่ใช่แค่ mouseover
  //
  // ปุ่ม ⋮ ของ Flow โผล่เฉพาะตอนเมาส์อยู่บนการ์ด และ UI สมัยใหม่ฟัง pointer event
  // ส่วน mouseenter/pointerenter ไม่ bubble จึงต้องยิงที่ตัวมันเองด้วย พร้อมพิกัด
  // เมาส์ที่สมเหตุสมผล ไม่งั้นบางไลบรารีจะไม่ถือว่าเมาส์เข้ามาแล้ว
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
    await sleep(200);
  }

  // บอกว่าเมาส์ออกจากตรงนั้นแล้ว
  //
  // เดิมยิงแต่ event ตอนเมาส์เข้า ไม่เคยบอกว่าออก Flow จึงถือว่าเมาส์ยังอยู่ที่การ์ด
  // ใบเดิมและไม่ย้ายแถบ ❤️ ↩️ ⋮ ไปไหน — log จริงเห็นการ์ดอยู่ที่ x=726 แต่ ⋮ ยังค้าง
  // ที่ x=507 ของใบก่อน ทุกใบหลังจากนั้นจึงหาปุ่มของตัวเองไม่เจอ
  async function unhover(el) {
    if (!el || !el.isConnected) return;
    const at = { bubbles: true, cancelable: true, clientX: 0, clientY: 0 };
    for (const type of ['pointermove', 'mousemove', 'pointerout', 'mouseout',
                        'pointerleave', 'mouseleave']) {
      const Ctor = type.startsWith('pointer') && window.PointerEvent
        ? PointerEvent : MouseEvent;
      el.dispatchEvent(new Ctor(type, at));
    }
    // ขยับ "เมาส์" ไปมุมจอ เผื่อ Flow ดูจากตำแหน่งไม่ใช่จาก event ที่ element
    document.body.dispatchEvent(new MouseEvent('mousemove', at));
    await sleep(250);
  }

  // ปุ่มเปิดเมนูของการ์ด — ต้องหานอกการ์ด ไม่ใช่ในการ์ด
  //
  // ตรวจหน้าจริงแล้วพบว่าในการ์ดมีของกดได้แค่สองชิ้น: <a> ที่ลิงก์ไป /edit/ กับปุ่ม
  // play_circle — ไม่มี ⋮ อยู่เลยสักชั้นใน 8 ชั้นเหนือรูป แถบ ❤️ ↩️ ⋮ ถูกเรนเดอร์
  // แยกออกไปแล้ววางทับการ์ดด้วย CSS การค้นในการ์ดจึงไม่มีวันเจอ และนั่นคือเหตุผลที่
  // fallback เดิมไปกดโดน <a> จนเด้งเข้าหน้าคลิป
  //
  // แต่จะค้นทั้งหน้าเฉย ๆ ก็ไม่ได้ เพราะแถบหัวเว็บมีปุ่ม more_vert ของตัวเองอยู่ด้วย
  // จึงต้องใช้สองสัญญาณประกอบกัน: เพิ่งโผล่มาหลัง hover และอยู่ทับกรอบการ์ดใบนี้
  function isMenuButton(b) {
    const t = (b.textContent || '').trim();
    return MENU_LABELS.some((l) => {
      const needle = l.toLowerCase();
      return t.startsWith(l) || t.includes(l)
        || (b.getAttribute('aria-label') || '').toLowerCase().includes(needle)
        || (b.getAttribute('title') || '').toLowerCase().includes(needle)
        || (b.getAttribute('data-testid') || '').toLowerCase().includes(needle);
    });
  }

  // ระยะห่างจากปุ่มถึงกรอบการ์ด — 0 คือซ้อนทับกัน
  //
  // เกณฑ์แรกคือ "จุดกึ่งกลางปุ่มต้องอยู่ในกรอบการ์ด" ซึ่งเข้มเกินไป แถบควบคุมที่วาง
  // ทับการ์ดมักล้นขอบออกมาเล็กน้อย พอล้นแล้วก็หาไม่เจอทั้งที่เห็นอยู่ตรงนั้น
  // วัดระยะแทนแล้วยอมให้คลาดได้นิดหน่อย ซึ่งยังห่างจากปุ่ม ⋮ บนหัวเว็บอยู่มาก
  const NEAR_PX = 48;

  function distanceTo(b, tileRect) {
    const r = b.getBoundingClientRect();
    if (!r.width || !r.height) return Infinity;
    const dx = Math.max(tileRect.left - r.right, r.left - tileRect.right, 0);
    const dy = Math.max(tileRect.top - r.bottom, r.top - tileRect.bottom, 0);
    return Math.sqrt(dx * dx + dy * dy);
  }

  const overlaps = (b, tileRect) => distanceTo(b, tileRect) <= NEAR_PX;

  function findMenuButton(tile, seenBefore) {
    const tileRect = tile.getBoundingClientRect();
    const all = [...document.querySelectorAll('button, [role="button"]')]
      .filter(isMenuButton);
    const near = (list) => list
      .map((b) => ({ b, d: distanceTo(b, tileRect) }))
      .filter((x) => x.d <= NEAR_PX)
      .sort((x, y) => x.d - y.d);

    // ที่เพิ่งโผล่มาหลัง hover คือแถบของการ์ดใบนี้แน่นอน จึงเอามาก่อน
    const fresh = seenBefore ? all.filter((b) => !seenBefore.has(b)) : all;
    const hit = near(fresh)[0] || near(all)[0];
    return hit ? hit.b : null;
  }

  // รายงานตอนหาไม่เจอ — ต้องเป็นระดับหน้า ไม่ใช่ระดับการ์ด เพราะแถบควบคุมอยู่นอกการ์ด
  // ใส่พิกัดมาด้วย จะได้รู้ว่าที่ไม่เข้าเกณฑ์เพราะไม่ทับกรอบ หรือเพราะไม่มีปุ่มเลย
  function describeButtons(tile) {
    const tr = tile.getBoundingClientRect();
    const box = (r) => `${Math.round(r.left)},${Math.round(r.top)} `
                     + `${Math.round(r.width)}x${Math.round(r.height)}`;
    return {
      กรอบการ์ด: box(tr),
      ปุ่มที่เข้าข่ายเมนูทั้งหน้า: [...document.querySelectorAll('button, [role="button"]')]
        .filter(isMenuButton).map((b) => ({
          text: (b.textContent || '').trim().slice(0, 30),
          cls: (b.className || '').toString().slice(0, 40),
          ที่: box(b.getBoundingClientRect()),
          ทับการ์ด: overlaps(b, tr),
        })),
    };
  }

  // ปิดเมนูที่ค้างอยู่ ไม่งั้นรอบถัดไปจะนับเมนูเดิมเป็นเมนูใหม่
  async function closeMenu() {
    document.body.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27, bubbles: true }));
    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await sleep(400);
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

  const tileCount = findTiles().length;
  say(`เจอสื่อ ${tileCount} ชิ้น — เริ่มดาวน์โหลด (สูงสุด ${MAX_PER_RUN})`);
  if (!tileCount) {
    say('หาไทล์สื่อไม่เจอ — เลื่อนหน้าให้เห็นสื่อก่อนแล้วลองใหม่');
    return;
  }

  // หาไทล์ใหม่ทุกรอบ อย่าเก็บรายการไว้ตั้งแต่ต้น
  //
  // เดิมเก็บ tiles ไว้ครั้งเดียวแล้ววนใช้ พอโหลดใบแรกเสร็จ React เรนเดอร์รายการใหม่
  // node ที่ถืออยู่ก็หลุดจาก DOM — getBoundingClientRect คืน 0x0 ทุกไทล์ที่เหลือ
  // ปุ่มทุกตัวจึงถือว่า "ไม่ทับการ์ด" และรายงานออกมาว่าหาปุ่ม ⋮ ไม่เจอ 13 ครั้งรวด
  // จำด้วย src ของสื่อแทน เพราะเป็นค่าที่อยู่รอดข้ามการเรนเดอร์
  const seen = new Set();
  const keyOf = (tile) => {
    const m = tile.querySelector('img, video');
    return m ? (m.currentSrc || m.src || m.getAttribute('poster') || '') : '';
  };
  function nextTile() {
    for (const t of findTiles()) {
      const k = keyOf(t);
      if (k && !seen.has(k)) return { tile: t, key: k };
    }
    return null;
  }

  let ok = 0;
  let fail = 0;
  const why = { noMenuButton: 0, menuDidNotOpen: 0, noDownloadItem: 0 };
  const buttonReport = [];
  let menuDump = '';

  // ถ้าหน้าเปลี่ยน แปลว่ามีคลิกไปโดนอะไรที่พาเข้าไปในคลิป ไทล์ที่จำไว้ก็ไม่อยู่ใน DOM
  // แล้ว การไล่กดต่อมีแต่จะกดมั่วไปเรื่อย — หยุดทันทีและบอกว่าเกิดอะไรขึ้น
  const startUrl = location.href;
  const navigatedAway = () => location.href !== startUrl;
  let lastTile = null;

  for (let i = 0; i < tileCount && ok < MAX_PER_RUN && !stopped; i++) {
    if (navigatedAway()) {
      say('หน้าเปลี่ยนไประหว่างทาง — หยุดไว้ก่อน');
      break;
    }
    const next = nextTile();
    if (!next) break;                 // ไล่ครบทุกใบที่มองเห็นแล้ว
    seen.add(next.key);
    const tile = next.tile;
    say(`[${i + 1}/${tileCount}] สำเร็จ ${ok} · พลาด ${fail}`);

    // ต้องบอกว่าเมาส์ออกจากใบก่อนหน้าแล้ว ไม่งั้นแถบควบคุมจะไม่ย้ายมาใบนี้
    await unhover(lastTile);
    lastTile = tile;

    tile.scrollIntoView({ block: 'center', behavior: 'smooth' });
    await sleep(600);

    // จดปุ่มทั้งหน้าไว้ก่อน hover เพื่อแยกแถบของการ์ดใบนี้ออกจากปุ่ม ⋮ ของหัวเว็บ
    const btnsBefore = new Set(document.querySelectorAll('button, [role="button"]'));
    await hover(tile);

    // เปิดเมนู ⋮ ของไทล์นี้ — แถบโผล่ตอน hover เท่านั้น จึงต้องรอ ไม่ใช่เช็คครั้งเดียว
    let menuBtn = await waitFor(() => findMenuButton(tile, btnsBefore), 2000);
    if (!menuBtn) {
      why.noMenuButton++;
      fail++;
      if (buttonReport.length < 3) buttonReport.push(describeButtons(tile));
      continue;
    }

    // จำสิ่งที่อยู่ใต้ body ไว้ก่อน เพื่อให้รู้ว่าอันไหนคือเมนูที่เพิ่งเปิด — เดิมค้นทั้ง
    // body ซึ่งอาจไปเจอเมนูค้างจากรอบก่อน หรือคำว่า "ดาวน์โหลด" ที่อื่นในหน้า
    const before = new Set(document.body.children);
    await hover(menuBtn);
    menuBtn.click();

    const menuRoot = await waitFor(
      () => [...document.body.children].find(
        (n) => !before.has(n) && (n.textContent || '').trim()), 2500);
    if (!menuRoot) {
      why.menuDidNotOpen++;
      fail++;
      await closeMenu();
      continue;
    }

    const item = findByText(menuRoot, DOWNLOAD_LABELS);
    if (!item) {
      why.noDownloadItem++;
      fail++;
      // ต่อเป็นสตริงเดียว ไม่ใช่ array — Console ย่อ array ไว้เป็น "Array(22)"
      // ต้องกดกางถึงจะเห็น ซึ่งพอส่งภาพหน้าจอมาก็อ่านอะไรไม่ได้เลย
      const menuText = (menuRoot.innerText || '').split('\n')
        .map((s) => s.trim()).filter(Boolean).join(' | ');
      console.warn('[flow-helper] เมนูเปิดแต่ไม่เจอ "ดาวน์โหลด" — เมนูมี: ' + menuText);
      if (!menuDump) menuDump = menuText;
      await closeMenu();
      continue;
    }

    // "ดาวน์โหลด" ไม่ได้โหลดทันที มันกางเมนูย่อยเลือกความละเอียดต่ออีกชั้น
    // (270p GIF · 720p ขนาดตั้งเดิม · 1080p เพิ่มความละเอียดแล้ว · 4K)
    //
    // และเมนูย่อยเปิดด้วยการ hover ไม่ใช่การคลิก — คลิกก่อนอาจปิดเมนูทิ้งเลย
    // จึง hover ก่อน ถ้าไม่มีอะไรกางค่อยคลิกเป็นทางสำรอง
    await hover(item);
    let quality = await waitFor(
      () => findByText(document.body, QUALITY_LABELS), 1800);
    if (!quality) {
      item.click();
      quality = await waitFor(() => findByText(document.body, QUALITY_LABELS), 1800);
    }

    if (quality) {
      // เลือก "ขนาดตั้งเดิม" — ได้คลิปจริงตามที่เรนเดอร์มา ไม่ใช่ GIF และไม่ใช่
      // ไฟล์อัปสเกลที่ใหญ่กว่าโดยไม่ได้รายละเอียดเพิ่มจริง
      await hover(quality);
      await sleep(200);
      quality.click();
      await sleep(500);
    } else {
      item.click();   // เผื่อ UI รุ่นที่กดแล้วโหลดตรง ไม่มีเมนูย่อย
    }

    ok++;
    // รอให้เมนูปิดก่อนไปไทล์ถัดไป ไม่งั้นรอบหน้าจะมองเห็นเมนูเดิมเป็นของใหม่
    await waitFor(() => !document.body.contains(menuRoot), 1500);
    await closeMenu();
    await humanDelay();   // หน่วงแบบคน — กันยิงถี่
  }

  // สรุปสาเหตุลง HUD ไม่ใช่แค่ Console — คนที่ใช้งานเห็น HUD อย่างเดียว เลข "ข้าม 7"
  // เฉย ๆ ไม่บอกอะไรเลยว่าจะแก้ตรงไหน
  const REASON_TH = {
    noMenuButton: 'หาปุ่ม ⋮ ไม่เจอ',
    menuDidNotOpen: 'กด ⋮ แล้วเมนูไม่เปิด',
    noDownloadItem: 'เมนูเปิดแต่ไม่มี "ดาวน์โหลด"',
  };
  const reasons = Object.entries(why).filter(([, n]) => n)
    .map(([k, n]) => `${REASON_TH[k]} ${n}`);

  if (fail) {
    console.warn('[flow-helper] สาเหตุที่พลาด:', why);
    if (buttonReport.length) {
      console.warn('[flow-helper] ปุ่มที่มีในการ์ด (ส่งอันนี้มาให้ดูได้เลย):',
                   JSON.stringify(buttonReport, null, 1));
    }
  }

  hud.querySelector('#fdh-msg').innerHTML =
    `<b>เสร็จ — ดาวน์โหลด ${ok} ชิ้น${fail ? ` · ข้าม ${fail}` : ''}</b>`
    + (reasons.length ? `<br><span style="color:#fbbf24">${reasons.join('<br>')}</span>` : '')
    + (navigatedAway() ? '<br><span style="color:#fbbf24">หน้าเปลี่ยนระหว่างทาง — '
                       + 'กด Back แล้วลองใหม่</span>' : '')
    // เมนูที่เปิดได้แต่ไม่เจอรายการดาวน์โหลด — โชว์ทั้งเมนูตรงนี้เลย จะได้คัดลอกส่งมา
    // ได้โดยไม่ต้องเปิด Console แล้วนั่งกางกล่อง Array
    + (menuDump ? '<br><span style="color:#9aa5a2">รายการในเมนู:</span>'
                + '<textarea readonly style="width:100%;height:90px;margin-top:6px;'
                + 'background:#0b0f12;color:#cfe;border:1px solid #2b3a36;'
                + 'border-radius:8px;padding:6px;font:12px/1.4 ui-monospace,monospace">'
                + menuDump.replace(/</g, '&lt;') + '</textarea>' : '')
    + (fail && !menuDump
        ? '<br><span style="color:#9aa5a2">รายละเอียดอยู่ใน Console (F12)</span>' : '');
  hud.querySelector('#fdh-stop').textContent = 'ปิด';
  hud.querySelector('#fdh-stop').onclick = () => hud.remove();
  console.log('[flow-helper] เสร็จแล้ว ไฟล์จะไปอยู่ในโฟลเดอร์ดาวน์โหลดของ Chrome');
  if (!fail) setTimeout(() => hud.remove(), 12000);
})();

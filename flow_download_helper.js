/**
 * flow_download_helper.js — ชี้เมาส์ที่คลิป แล้วที่เหลือระบบกดให้เอง
 *
 * ใช้ยังไง
 *   1. เปิดโปรเจกต์ Flow ใน Chrome ปกติของคุณ (ที่ล็อกอินอยู่แล้ว)
 *   2. กดบุ๊กมาร์ก "⬇️ โหลดคลิปจาก Flow"
 *   3. เอาเมาส์ไปชี้ที่คลิปทีละใบ — พอแถบ ⋮ โผล่ ระบบจะกดต่อให้เองจนจบ
 *      แล้วเลื่อนเมาส์ไปใบถัดไป ทำไปเรื่อย ๆ
 *
 * ทำไมต้องชี้เมาส์เอง
 *   แถบ ❤️ ↩️ ⋮ ของ Flow โผล่จากสถานะ :hover ซึ่ง **เบราว์เซอร์ไม่ยอมให้สคริปต์
 *   สร้างขึ้นเองได้** ทดสอบตรง ๆ แล้ว: ยิง pointerover/pointerenter/mouseover/
 *   mouseenter/pointermove/mousemove ครบทุกตัวบน element ที่มี CSS :hover
 *   → element.matches(':hover') คืน false และปุ่มยัง display:none อยู่เหมือนเดิม
 *
 *   เวอร์ชันก่อนหน้าจึงได้ผลลัพธ์แปลก ๆ คือบางรอบโหลดได้ 1-4 ไฟล์ บางรอบได้ 0
 *   ทั้งที่โค้ดเหมือนกัน — เพราะที่โหลดได้คือใบที่ "เมาส์จริงของผู้ใช้" บังเอิญค้างอยู่
 *   ไม่ใช่ฝีมือสคริปต์ พอผู้ใช้เอามือออกจากเมาส์จริง ๆ ก็ได้ 0 จาก 15 ทันที
 *
 *   สิ่งที่สคริปต์ทำแทนได้คือทุกขั้นหลังจากนั้น — กด ⋮ หาเมนู ชี้ "ดาวน์โหลด"
 *   รอเมนูย่อย แล้วเลือกความละเอียด รวม 4 จังหวะต่อคลิป เหลือแค่ชี้เมาส์ค้างไว้
 *
 * ปลอดภัย: ทำงานบนหน้าที่คุณเปิดเอง ไม่มีเบราว์เซอร์อัตโนมัติ ไม่มีการล็อกอินผ่าน
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

  // บนหน้าจริง ปุ่มเมนูมี textContent ว่า "more_vertเพิ่มเติม" — Material วางชื่อ
  // ligature ของไอคอนไว้ติดกับป้ายกำกับโดยไม่มีตัวคั่น จึงจับด้วย startsWith ได้
  const MENU_LABELS = ['more_vert', 'more_horiz', 'ตัวเลือกเพิ่มเติม', 'More options',
                       'เพิ่มเติม', 'ตัวเลือก', 'Options', 'overflow'];

  // 'download' คือชื่อ ligature ของไอคอน รายการจริงจึงเป็น "downloadดาวน์โหลด"
  const DOWNLOAD_LABELS = ['ดาวน์โหลด', 'download', 'Download'];

  // เมนูย่อยหลังกด "ดาวน์โหลด" — 270p เป็น GIF ส่วน 1080p/4K เป็นการอัปสเกลจาก
  // ไฟล์เดิม ได้ไฟล์ใหญ่ขึ้นแต่รายละเอียดเท่าเดิม จึงเลือกขนาดตั้งเดิม
  const QUALITY_LABELS = ['ขนาดตั้งเดิม', 'Original size', 'Original'];

  // ปุ่ม ⋮ บนหัวเว็บก็เข้าข่ายชื่อเดียวกัน แต่มันอยู่บนสุดของหน้าเสมอ
  const HEADER_ZONE_PX = 60;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const humanDelay = () =>
    sleep(MIN_DELAY_MS + Math.random() * (MAX_DELAY_MS - MIN_DELAY_MS));

  // ── แถบแสดงสถานะ ─────────────────────────────────────────────────────────
  const hud = document.createElement('div');
  hud.style.cssText = [
    'position:fixed', 'z-index:2147483647', 'right:16px', 'bottom:16px',
    'background:#101418', 'color:#e8f0ee', 'font:13px/1.6 system-ui,sans-serif',
    'padding:14px 16px', 'border-radius:12px', 'width:300px',
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
  hud.querySelector('#fdh-stop').onclick = () => { stopped = true; };
  const say = (html) => { hud.querySelector('#fdh-msg').innerHTML = html; };
  const log = (t) => console.log('[flow-helper]', t);

  // ── ตัวช่วยเล็ก ๆ ────────────────────────────────────────────────────────
  async function waitFor(fn, ms) {
    const until = Date.now() + ms;
    for (;;) {
      if (stopped) return null;
      const v = fn();
      if (v) return v;
      if (Date.now() > until) return null;
      await sleep(120);
    }
  }

  // ชี้เมาส์ไปที่ element — ใช้ได้กับเมนูที่เปิดด้วย JS แต่ไม่ได้กับ CSS :hover
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

  const CLICKABLE = ['[role="menuitem"]', 'button', '[role="button"]', 'a', 'li',
                     'span', 'div'];

  // หาปุ่ม/รายการจากข้อความ — ชนิดที่กดได้จริงมาก่อน ตรงเป๊ะมาก่อนขึ้นต้นด้วย
  // ขึ้นต้นด้วยมาก่อนแค่มีคำนั้นอยู่ และในชั้นเดียวกันข้อความสั้นกว่าชนะ เพราะ
  // เมนูจริงมีทั้ง "ดาวน์โหลด" และ "ดาวน์โหลดต้นฉบับ"
  function findByText(root, labels) {
    for (const label of labels) {
      for (const sel of CLICKABLE) {
        const hits = [...root.querySelectorAll(sel)].filter((n) => {
          const t = (n.textContent || '').trim();
          if (t === label || t.startsWith(label) || t.includes(label)) return true;
          const aria = (n.getAttribute('aria-label') || '').trim();
          return aria === label || aria.startsWith(label) || aria.includes(label);
        });
        if (!hits.length) continue;
        const txt = (n) => (n.textContent || '').trim();
        let pool = hits.filter((n) => txt(n) === label);
        if (!pool.length) pool = hits.filter((n) => txt(n).startsWith(label));
        if (!pool.length) pool = hits;
        pool = [...pool].sort((a, b) => txt(a).length - txt(b).length);
        // ตัวที่ไม่มีตัวอื่นในกองซ้อนอยู่ข้างใน = ตัวจริง ไม่ใช่กล่องห่อ
        const deepest = pool.find((n) => !pool.some((o) => o !== n && n.contains(o)));
        return deepest || pool[pool.length - 1];
      }
    }
    return null;
  }

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

  // ปุ่ม ⋮ ของการ์ดที่ผู้ใช้กำลังชี้อยู่ — เล็ก อยู่ในจอ และไม่ใช่แถบหัวเว็บ
  function cardMenuButton() {
    const cands = [...document.querySelectorAll('button, [role="button"]')]
      .filter(isMenuButton)
      .map((b) => ({ b, r: b.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && r.height > 0
        && r.width <= 48 && r.height <= 48          // ปุ่มไอคอน ไม่ใช่กล่องห่อ
        && r.top >= HEADER_ZONE_PX                   // ไม่ใช่ ⋮ ของหัวเว็บ
        && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth);
    return cands.length ? cands[0].b : null;
  }

  function posKey(b) {
    const r = b.getBoundingClientRect();
    return `${Math.round(r.left)},${Math.round(r.top)}`;
  }

  async function closeMenu() {
    document.body.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27, bubbles: true }));
    await sleep(400);
  }

  // ── คลิกขวา ──────────────────────────────────────────────────────────────
  // เป็นทางที่ใช้ได้จริงถ้า Flow ดัก contextmenu เอง เพราะนั่นคือ JS event ที่
  // สคริปต์ยิงได้ ต่างจาก :hover ที่เบราว์เซอร์ปิดตายไม่ให้ปลอม
  // (การยิง contextmenu แบบสังเคราะห์ไม่ทำให้เมนูของ Chrome เด้งขึ้นมาด้วย)
  async function rightClick(el) {
    const r = el.getBoundingClientRect();
    const at = { bubbles: true, cancelable: true, button: 2, buttons: 2,
                 clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
    el.dispatchEvent(new MouseEvent('pointerdown', at));
    el.dispatchEvent(new MouseEvent('mousedown', at));
    el.dispatchEvent(new MouseEvent('contextmenu', at));
    el.dispatchEvent(new MouseEvent('mouseup', at));
    await sleep(250);
  }

  // หาไทล์สื่อ — การ์ดที่หุ้ม media ชิ้นเดียว ไม่ใช่ทั้ง grid
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

  // เมนูที่เพิ่งโผล่ใต้ body — ใช้ diff แทนการค้นทั้งหน้า จะได้ไม่ไปเจอเมนูค้าง
  const bodyKids = () => new Set(document.body.children);
  const newMenu = (before) => [...document.body.children].find(
    (n) => !before.has(n) && (n.textContent || '').trim());

  // กดดาวน์โหลดในเมนูที่เปิดอยู่ แล้วเลือกความละเอียด
  // คืน true เมื่อกดสำเร็จ · คืนข้อความเหตุผลเมื่อไม่สำเร็จ
  async function downloadFromMenu(menuRoot) {
    const item = findByText(menuRoot, DOWNLOAD_LABELS);
    if (!item) {
      const menuText = (menuRoot.innerText || '').split('\n')
        .map((s) => s.trim()).filter(Boolean).join(' | ');
      console.warn('[flow-helper] เมนูมี: ' + menuText);
      return 'เมนูเปิดแต่ไม่มี "ดาวน์โหลด"';
    }
    // เมนูย่อยความละเอียดเปิดด้วย hover — อันนี้เป็น JS ไม่ใช่ CSS :hover จึงสั่งได้
    await hover(item);
    let quality = await waitFor(() => findByText(document.body, QUALITY_LABELS), 1800);
    if (!quality) {
      item.click();
      quality = await waitFor(() => findByText(document.body, QUALITY_LABELS), 1800);
    }
    if (quality) {
      await hover(quality);
      await sleep(200);
      quality.click();
    } else {
      item.click();   // เผื่อ UI รุ่นที่กดแล้วโหลดตรง ไม่มีเมนูย่อย
    }
    return true;
  }

  // ── กันกดผิดหน้า ─────────────────────────────────────────────────────────
  if (!/(^|\.)labs\.google$/.test(location.hostname)) {
    say('<b style="color:#fbbf24">ยังไม่ได้อยู่บนหน้า Google Flow</b><br>'
      + 'ปุ่มนี้ต้อง <b>ลาก</b> ขึ้นแถบบุ๊กมาร์กก่อน (ไม่ใช่กด)<br>'
      + 'แล้วค่อยเปิดโปรเจกต์ใน Flow และกดบุ๊กมาร์กนั้น');
    hud.querySelector('#fdh-stop').textContent = 'ปิด';
    hud.querySelector('#fdh-stop').onclick = () => hud.remove();
    return;
  }

  // ── วนรอผู้ใช้ชี้เมาส์ แล้วกดต่อให้เอง ───────────────────────────────────
  const IDLE_MSG = (n) =>
    `<b style="color:#fbbf24">👉 เอาเมาส์ไปชี้ที่คลิปสักใบ</b><br>`
    + `พอแถบ ⋮ โผล่ ระบบจะกดดาวน์โหลดให้เอง<br>`
    + `<span style="color:#9aa5a2">แล้วเลื่อนไปใบถัดไปเรื่อย ๆ</span><br>`
    + `<b>โหลดแล้ว ${n}/${MAX_PER_RUN}</b>`;

  let ok = 0;
  let lastKey = '';
  const problems = [];

  // ครอบไว้ทั้งก้อน — error ใน async IIFE จะกลายเป็น unhandled rejection ที่ไม่โผล่
  // ที่ไหนเลย HUD ค้างอยู่ที่ข้อความเดิมเหมือนกำลังรออยู่ ทั้งที่ตายไปแล้ว
  // (เจอมาแล้วตอน cardMenuButton คืน object แทนที่จะคืนตัวปุ่ม)
  try {

  // ── ลองคลิกขวาก่อน ───────────────────────────────────────────────────────
  // ถ้า Flow ดัก contextmenu เอง ทางนี้ทำได้อัตโนมัติทั้งหมดโดยไม่ต้องพึ่ง :hover
  // ที่ปลอมไม่ได้ ลองกับไทล์ใบแรกก่อน แล้วค่อยตัดสินว่าจะเดินทางไหน
  say('🔍 กำลังลองคลิกขวา…');
  let autoMode = false;
  const probe = findTiles()[0];
  if (probe) {
    const before = bodyKids();
    await rightClick(probe);
    const menu = await waitFor(() => newMenu(before), 1500);
    if (menu) {
      autoMode = findByText(menu, DOWNLOAD_LABELS) ? true : false;
      if (!autoMode) log('คลิกขวาเปิดเมนูได้ แต่ในเมนูไม่มี "ดาวน์โหลด"');
      await closeMenu();
    }
  }
  log(autoMode ? 'คลิกขวาใช้ได้ — ทำอัตโนมัติทั้งหมด'
               : 'คลิกขวาไม่ได้ผล — เปลี่ยนเป็นโหมดชี้เมาส์');

  if (autoMode) {
    // จำด้วย src ของสื่อ เพราะ node จะหลุดเมื่อ Flow เรนเดอร์รายการใหม่
    const seen = new Set();
    const keyOf = (t) => {
      const m = t.querySelector('img, video');
      return m ? (m.currentSrc || m.src || m.getAttribute('poster') || '') : '';
    };
    const total = findTiles().length;
    say(`⚙️ คลิกขวาใช้ได้ — ไล่โหลด ${Math.min(total, MAX_PER_RUN)} ไฟล์ให้เอง`);

    for (let i = 0; i < total && ok < MAX_PER_RUN && !stopped; i++) {
      const tile = findTiles().find((t) => keyOf(t) && !seen.has(keyOf(t)));
      if (!tile) break;
      seen.add(keyOf(tile));

      tile.scrollIntoView({ block: 'center', behavior: 'smooth' });
      await sleep(500);

      const before = bodyKids();
      await rightClick(tile);
      const menuRoot = await waitFor(() => newMenu(before), 2500);
      if (!menuRoot) { problems.push('คลิกขวาแล้วเมนูไม่เปิด'); await closeMenu(); continue; }

      const res = await downloadFromMenu(menuRoot);
      if (res !== true) { problems.push(res); await closeMenu(); continue; }

      ok++;
      log(`ดาวน์โหลดแล้ว ${ok} ไฟล์`);
      say(`⚙️ กำลังไล่โหลด… <b>${ok}/${Math.min(total, MAX_PER_RUN)}</b>`);
      await waitFor(() => !document.body.contains(menuRoot), 1500);
      await closeMenu();
      await humanDelay();   // หน่วงแบบคน — กันยิงถี่
    }
  } else {

  say(IDLE_MSG(0));
  log(`พร้อมแล้ว — ชี้เมาส์ที่คลิปได้เลย (สูงสุด ${MAX_PER_RUN} ไฟล์ต่อรอบ)`);

  while (ok < MAX_PER_RUN && !stopped) {
    // รอปุ่ม ⋮ ที่ยังไม่เคยทำ — ผู้ใช้ต้องชี้เมาส์ก่อน สคริปต์สร้าง :hover เองไม่ได้
    const btn = await waitFor(
      () => { const b = cardMenuButton(); return b && posKey(b) !== lastKey ? b : null; },
      60000);
    if (!btn) {
      if (stopped) break;
      say('รอนานเกินไป — ปิดแล้วกดใหม่ได้เลย' + `<br><b>โหลดแล้ว ${ok}</b>`);
      break;
    }

    lastKey = posKey(btn);
    say(`⏳ เจอแล้ว — กำลังกดดาวน์โหลด…<br><b>โหลดแล้ว ${ok}/${MAX_PER_RUN}</b>`);

    const before = new Set(document.body.children);
    await hover(btn);
    btn.click();

    const menuRoot = await waitFor(
      () => [...document.body.children].find(
        (n) => !before.has(n) && (n.textContent || '').trim()), 2500);
    if (!menuRoot) {
      problems.push('กด ⋮ แล้วเมนูไม่เปิด');
      await closeMenu();
      continue;
    }

    const res = await downloadFromMenu(menuRoot);
    if (res !== true) { problems.push(res); await closeMenu(); continue; }

    ok++;
    log(`ดาวน์โหลดแล้ว ${ok} ไฟล์`);
    await waitFor(() => !document.body.contains(menuRoot), 1500);
    await closeMenu();
    say(`✅ โหลดใบนี้แล้ว — เลื่อนเมาส์ไปใบถัดไป<br><b>โหลดแล้ว ${ok}/${MAX_PER_RUN}</b>`);
    await humanDelay();   // หน่วงแบบคน — กันยิงถี่
    if (ok < MAX_PER_RUN && !stopped) say(IDLE_MSG(ok));
  }
  }
  } catch (e) {
    console.error('[flow-helper] พัง:', e);
    say(`<b style="color:#f87171">สคริปต์พัง</b><br>${String(e).slice(0, 200)}`
      + `<br><b>โหลดไปแล้ว ${ok}</b>`);
    hud.querySelector('#fdh-stop').textContent = 'ปิด';
    hud.querySelector('#fdh-stop').onclick = () => hud.remove();
    return;
  }

  const note = problems.length
    ? `<br><span style="color:#fbbf24">มีบางใบไม่สำเร็จ: `
      + [...new Set(problems)].join(' · ') + '</span>'
    : '';
  say(`<b>เสร็จ — ดาวน์โหลด ${ok} ชิ้น</b>${note}`
    + (ok >= MAX_PER_RUN ? '<br>ครบเพดานต่อรอบแล้ว กดบุ๊กมาร์กใหม่ได้ถ้ายังเหลือ' : ''));
  hud.querySelector('#fdh-stop').textContent = 'ปิด';
  hud.querySelector('#fdh-stop').onclick = () => hud.remove();
  log('เสร็จแล้ว ไฟล์จะไปอยู่ในโฟลเดอร์ดาวน์โหลดของ Chrome');
})();

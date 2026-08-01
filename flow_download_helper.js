/**
 * flow_download_helper.js — คลิกขวาไล่โหลดคลิปในหน้า Google Flow ให้อัตโนมัติ
 *
 * ใช้ยังไง
 *   1. เปิดโปรเจกต์ Flow ใน Chrome ปกติของคุณ (ที่ล็อกอินอยู่แล้ว)
 *   2. กดบุ๊กมาร์ก "⬇️ โหลดคลิปจาก Flow" — แล้วปล่อยให้มันทำงาน
 *
 * ทำไมต้องคลิกขวา ไม่ใช่กดปุ่ม ⋮
 *   แถบ ❤️ ↩️ ⋮ ของ Flow โผล่จากสถานะ :hover ซึ่ง **เบราว์เซอร์ไม่ยอมให้สคริปต์
 *   สร้างขึ้นเองได้** ทดสอบตรง ๆ แล้ว: ยิง pointerover/pointerenter/mouseover/
 *   mouseenter/pointermove/mousemove ครบทุกตัวบน element ที่มี CSS :hover
 *   → element.matches(':hover') คืน false และปุ่มยัง display:none อยู่เหมือนเดิม
 *
 *   เวอร์ชันที่ไล่กด ⋮ จึงได้ผลแปลก ๆ คือบางรอบโหลดได้ 1-4 ไฟล์ บางรอบได้ 0 ทั้งที่
 *   โค้ดเหมือนกัน — ที่โหลดได้คือใบที่ "เมาส์จริงของผู้ใช้" บังเอิญค้างอยู่ ไม่ใช่
 *   ฝีมือสคริปต์ พอผู้ใช้เอามือออกจากเมาส์จริง ๆ ก็ได้ 0 จาก 15 ทันที
 *
 *   แต่คลิกขวาเป็นคนละเรื่อง — contextmenu คือ event ที่หน้าเว็บดักเอง สคริปต์ยิงได้
 *   ต่างจาก :hover ที่เป็นสถานะของเบราว์เซอร์ ถ้า Flow ทำเมนูคลิกขวาของตัวเอง
 *   (ซึ่งมันทำ) ทางนี้จึงเดินได้ครบโดยไม่ต้องแตะเมาส์เลย
 *
 *   การยิง contextmenu แบบสังเคราะห์ไม่ทำให้เมนูของ Chrome เด้งขึ้นมาด้วย
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

  // 'download' คือชื่อ ligature ของไอคอน ซึ่ง Material วางไว้ติดหน้าป้ายกำกับโดยไม่มี
  // ตัวคั่น รายการจริงในเมนูจึงเป็น "downloadดาวน์โหลด"
  const DOWNLOAD_LABELS = ['ดาวน์โหลด', 'download', 'Download'];

  // เมนูย่อยหลังกด "ดาวน์โหลด" — 270p เป็น GIF ส่วน 1080p/4K เป็นการอัปสเกลจาก
  // ไฟล์เดิม ได้ไฟล์ใหญ่ขึ้นแต่รายละเอียดเท่าเดิม จึงเลือกขนาดตั้งเดิม
  const QUALITY_LABELS = ['ขนาดตั้งเดิม', 'Original size', 'Original'];

  // ห้ามกดเด็ดขาด
  //
  // เมนูคลิกขวาที่สคริปต์เปิดได้จริงบางทีมีแค่ "ลบ" รายการเดียว ซึ่งแปลว่าถ้าการจับ
  // ข้อความพลาดเมื่อไหร่ คลิปของผู้ใช้หายทันทีและเอาคืนไม่ได้ ต่อให้ตรรกะตอนนี้จะ
  // หาแต่คำว่า "ดาวน์โหลด" ก็ตาม — ราคาของการพลาดสูงเกินกว่าจะไว้ใจตรรกะอย่างเดียว
  // จึงเช็คซ้ำที่ปลายทางก่อนกดทุกครั้ง
  const DESTRUCTIVE_LABELS = ['ลบ', 'ย้ายลงถังขยะ', 'ถังขยะ', 'delete', 'Delete',
                              'remove', 'Remove', 'Trash', 'trash', 'Move to trash'];

  const isDestructive = (el) => {
    const t = ((el.textContent || '') + ' ' + (el.getAttribute('aria-label') || ''))
      .toLowerCase();
    return DESTRUCTIVE_LABELS.some((l) => t.includes(l.toLowerCase()));
  };

  // กดได้ก็ต่อเมื่อไม่เข้าข่ายทำลาย — ถ้าเข้าข่าย ไม่กดและบอกออกมา
  function safeClick(el, what) {
    if (isDestructive(el)) {
      console.warn(`[flow-helper] ไม่กด "${(el.textContent || '').trim().slice(0, 40)}" `
                 + `ตอน${what} เพราะเข้าข่ายลบ/ทิ้ง`);
      return false;
    }
    el.click();
    return true;
  }

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
      menuDump = (menuRoot.innerText || '').split('\n')
        .map((s) => s.trim()).filter(Boolean).join(' | ');
      console.warn('[flow-helper] เมนูมี: ' + menuDump);
      return 'เมนูเปิดแต่ไม่มี "ดาวน์โหลด"';
    }
    if (isDestructive(item)) return 'รายการที่จับได้เข้าข่ายลบ — ไม่กด';

    // เมนูย่อยความละเอียดเปิดด้วย hover — อันนี้เป็น JS ไม่ใช่ CSS :hover จึงสั่งได้
    await hover(item);
    let quality = await waitFor(() => findByText(document.body, QUALITY_LABELS), 1800);
    if (!quality) {
      if (!safeClick(item, 'กดดาวน์โหลด')) return 'รายการที่จับได้เข้าข่ายลบ — ไม่กด';
      quality = await waitFor(() => findByText(document.body, QUALITY_LABELS), 1800);
    }
    if (quality) {
      await hover(quality);
      await sleep(200);
      if (!safeClick(quality, 'เลือกความละเอียด')) {
        return 'ตัวเลือกความละเอียดเข้าข่ายลบ — ไม่กด';
      }
    } else {
      // เผื่อ UI รุ่นที่กดแล้วโหลดตรง ไม่มีเมนูย่อย
      if (!safeClick(item, 'กดดาวน์โหลด')) return 'รายการที่จับได้เข้าข่ายลบ — ไม่กด';
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

  // ── บอกตลอดว่าอยู่ขั้นไหน และกันค้าง ─────────────────────────────────────
  //
  // รอบก่อนผู้ใช้เจออาการ "ค้าง" แล้วบอกไม่ได้ว่าค้างตรงไหน เพราะ HUD เขียนข้อความ
  // ทีเดียวตอนเริ่มขั้นแล้วเงียบยาว ตอนนี้เดินนาฬิกาให้เห็น และถ้าขั้นไหนใช้เวลา
  // เกิน STEP_TIMEOUT ก็เลิกเองพร้อมบอกว่าค้างที่ขั้นอะไร ดีกว่าค้างไปเงียบ ๆ
  const STEP_TIMEOUT_MS = 25000;
  let ok = 0;
  let total = 0;
  const problems = [];
  let step = 'กำลังเริ่ม';
  let stepAt = Date.now();
  let stuckAt = '';
  let menuDump = '';
  const setStep = (s) => { step = s; stepAt = Date.now(); };

  const ticker = setInterval(() => {
    if (Date.now() - stepAt > STEP_TIMEOUT_MS && !stuckAt) {
      stuckAt = step;
      stopped = true;
      return;
    }
    const secs = Math.round((Date.now() - stepAt) / 1000);
    say(`⚙️ ${step}${secs >= 2 ? ` (${secs} วิ)` : ''}`
      + `<br><b>โหลดแล้ว ${ok}${total ? '/' + Math.min(total, MAX_PER_RUN) : ''}</b>`);
  }, 500);

  // ครอบไว้ทั้งก้อน — error ใน async IIFE จะกลายเป็น unhandled rejection ที่ไม่โผล่
  // ที่ไหนเลย HUD ค้างอยู่ที่ข้อความเดิมเหมือนกำลังรออยู่ ทั้งที่ตายไปแล้ว
  // (เจอมาแล้วตอน cardMenuButton คืน object แทนที่จะคืนตัวปุ่ม)
  try {

  // ── คลิกขวาทุกใบ ─────────────────────────────────────────────────────────
  // ไม่ลองก่อนแล้วค่อยเลือกทางอีกต่อไป — คลิกขวาคือทางหลัก ทำไปเลย ถ้าใบไหน
  // ไม่ขึ้นเมนูก็ข้ามใบนั้นแล้วไปต่อ สรุปเหตุผลทั้งหมดตอนจบทีเดียว
  //
  // จำด้วย src ของสื่อ เพราะ node จะหลุดเมื่อ Flow เรนเดอร์รายการใหม่หลังโหลดเสร็จ
  const seen = new Set();
  const keyOf = (t) => {
    const m = t.querySelector('img, video');
    return m ? (m.currentSrc || m.src || m.getAttribute('poster') || '') : '';
  };

  setStep('กำลังหาคลิปในหน้า');
  total = findTiles().length;
  log(`เจอสื่อ ${total} ชิ้น — เริ่มคลิกขวาทีละใบ (สูงสุด ${MAX_PER_RUN})`);
  if (!total) {
    clearInterval(ticker);
    say('หาคลิปในหน้าไม่เจอ — เลื่อนหน้าให้เห็นคลิปก่อนแล้วกดใหม่');
    hud.querySelector('#fdh-stop').textContent = 'ปิด';
    hud.querySelector('#fdh-stop').onclick = () => hud.remove();
    return;
  }

  for (let i = 0; i < total && ok < MAX_PER_RUN && !stopped; i++) {
    setStep(`เลื่อนไปคลิปที่ ${i + 1}`);
    const tile = findTiles().find((t) => keyOf(t) && !seen.has(keyOf(t)));
    if (!tile) break;
    seen.add(keyOf(tile));

    tile.scrollIntoView({ block: 'center', behavior: 'smooth' });
    await sleep(500);

    setStep(`คลิกขวาคลิปที่ ${i + 1}`);
    const before = bodyKids();
    await rightClick(tile);

    setStep(`รอเมนูของคลิปที่ ${i + 1}`);
    const menuRoot = await waitFor(() => newMenu(before), 2500);
    if (!menuRoot) { problems.push('คลิกขวาแล้วเมนูไม่เปิด'); await closeMenu(); continue; }

    setStep(`กดดาวน์โหลดคลิปที่ ${i + 1}`);
    const res = await downloadFromMenu(menuRoot);
    if (res !== true) {
      problems.push(res);
      await closeMenu();
      // เมนูที่คลิกขวาเปิดได้ไม่มี "ดาวน์โหลด" — ใบอื่นก็จะเหมือนกันทั้งหมด
      // การคลิกขวาต่ออีก 14 ครั้งไม่ได้อะไรเพิ่ม นอกจากเปิดเมนูที่มีแต่ "ลบ" ซ้ำ ๆ
      if (menuDump) { stopped = true; }
      continue;
    }

    ok++;
    log(`ดาวน์โหลดแล้ว ${ok} ไฟล์`);
    setStep('รอเมนูปิด');
    await waitFor(() => !document.body.contains(menuRoot), 1500);
    await closeMenu();
    setStep('พักก่อนไฟล์ถัดไป');
    await humanDelay();   // หน่วงแบบคน — กันยิงถี่
  }
  } catch (e) {
    clearInterval(ticker);
    console.error('[flow-helper] พัง:', e);
    say(`<b style="color:#f87171">สคริปต์พัง</b><br>${String(e).slice(0, 200)}`
      + `<br><b>โหลดไปแล้ว ${ok}</b>`);
    hud.querySelector('#fdh-stop').textContent = 'ปิด';
    hud.querySelector('#fdh-stop').onclick = () => hud.remove();
    return;
  }

  clearInterval(ticker);
  const note = problems.length
    ? `<br><span style="color:#fbbf24">มีบางใบไม่สำเร็จ: `
      + [...new Set(problems)].join(' · ') + '</span>'
    : '';
  const stuckNote = stuckAt
    ? `<br><span style="color:#f87171">หยุดเองเพราะค้างที่ขั้น: ${stuckAt}</span>`
    : '';
  // เมนูที่คลิกขวาได้ไม่มีดาวน์โหลด = ทางนี้ตันบนหน้านี้ บอกให้ชัดว่าเจออะไรและ
  // ต้องทำยังไงต่อ ดีกว่าปล่อยให้เดาว่าทำไมได้ 0 ไฟล์
  const dumpNote = menuDump
    ? '<br><span style="color:#9aa5a2">เมนูที่คลิกขวาเปิดได้มีแค่:</span>'
      + `<div style="margin-top:4px;padding:6px;background:#0b0f12;border-radius:6px;`
      + `font:12px/1.4 ui-monospace,monospace">${menuDump.replace(/</g, '&lt;')}</div>`
      + '<span style="color:#fbbf24">คลิกขวาแบบสคริปต์ได้เมนูสั้นกว่าที่คุณคลิกเอง '
      + '— ทางนี้ตัน ต้องคลิกขวาด้วยมือ แล้วเลือกดาวน์โหลดเอง</span>'
    : '';
  say(`<b>เสร็จ — ดาวน์โหลด ${ok} ชิ้น</b>${stuckNote}${note}${dumpNote}`
    + (ok >= MAX_PER_RUN ? '<br>ครบเพดานต่อรอบแล้ว กดบุ๊กมาร์กใหม่ได้ถ้ายังเหลือ' : ''));
  if (stuckAt) console.warn('[flow-helper] ค้างที่ขั้น: ' + stuckAt);
  hud.querySelector('#fdh-stop').textContent = 'ปิด';
  hud.querySelector('#fdh-stop').onclick = () => hud.remove();
  log('เสร็จแล้ว ไฟล์จะไปอยู่ในโฟลเดอร์ดาวน์โหลดของ Chrome');
})();

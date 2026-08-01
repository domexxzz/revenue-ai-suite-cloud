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

  // ปุ่ม ⋮ ของการ์ด — textContent จริงคือ "more_vertเพิ่มเติม"
  const MENU_LABELS = ['more_vert', 'more_horiz', 'ตัวเลือกเพิ่มเติม', 'More options',
                       'เพิ่มเติม', 'ตัวเลือก', 'Options', 'overflow'];

  // ปุ่ม ⋮ บนหัวเว็บก็ชื่อเดียวกัน แต่มันอยู่บนสุดของหน้าเสมอ
  const HEADER_ZONE_PX = 60;

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

  // ตัวที่กดได้จริง อาจไม่ใช่ตัวที่ข้อความตรง
  //
  // รายการเมนูมักเป็นแถวที่มีข้อความซ้อนข้างใน เช่น แถวเลือกความละเอียดมีทั้ง
  // "720p" กับ "ขนาดตั้งเดิม" เป็นคนละ span การหาแบบ "ข้อความสั้นสุดชนะ" จึงไปได้
  // span ตัวใน ซึ่งไม่มี handler อะไรผูกอยู่ — กดแล้วเงียบ
  //
  // ประวัติดาวน์โหลดของ Chrome ยืนยัน: ทั้งรอบ 15 ไฟล์และรอบ 3 ไฟล์ Chrome ไม่เคย
  // ถูกสั่งให้โหลดเลย (มีรายการเดียวจากรอบแรก) แปลว่าคลิกไม่ได้ไปถึงตัวที่ทำงาน
  const CLICK_HOSTS = '[role="menuitem"], [role="option"], button, [role="button"], li, a';

  function clickTarget(el) {
    if (el.matches && el.matches(CLICK_HOSTS)) return el;
    return (el.closest && el.closest(CLICK_HOSTS)) || el;
  }

  // กดแบบครบลำดับ ไม่ใช่ .click() เฉย ๆ — UI หลายตัวทำงานตอน pointerdown/mouseup
  // ไม่ใช่ตอน click และบางตัวไม่สนใจ click ที่ไม่มี pointer นำมาก่อนเลย
  function realClick(el) {
    const r = el.getBoundingClientRect();
    const at = { bubbles: true, cancelable: true, view: window,
                 clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
    for (const type of ['pointerover', 'pointerenter', 'pointermove', 'mouseover',
                        'mousemove', 'pointerdown', 'mousedown', 'pointerup',
                        'mouseup', 'click']) {
      const Ctor = type.startsWith('pointer') && window.PointerEvent
        ? PointerEvent : MouseEvent;
      el.dispatchEvent(new Ctor(type, at));
    }
  }

  // บอกว่ากำลังจะกดอะไร — เวลาพัง จะได้รู้ว่าจับผิดตัวหรือกดถูกตัวแต่ไม่มีผล
  function describeClick(what, el) {
    console.log(`[flow-helper] ${what}: <${el.tagName.toLowerCase()}`
      + `${el.getAttribute('role') ? ` role=${el.getAttribute('role')}` : ''}> `
      + `"${(el.textContent || '').trim().slice(0, 40)}"`);
  }

  // กดได้ก็ต่อเมื่อไม่เข้าข่ายทำลาย — ถ้าเข้าข่าย ไม่กดและบอกออกมา
  function safeClick(el, what) {
    const target = clickTarget(el);
    // เช็คทั้งตัวที่เจอและตัวที่จะกดจริง เผื่อไต่ขึ้นไปโดนแถว "ลบ"
    if (isDestructive(el) || isDestructive(target)) {
      console.warn(`[flow-helper] ไม่กด "${(target.textContent || '').trim().slice(0, 40)}" `
                 + `ตอน${what} เพราะเข้าข่ายลบ/ทิ้ง`);
      return false;
    }
    realClick(target);
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
  // เลขรุ่น — ต้องเห็นได้จาก HUD ว่ากำลังรันตัวไหน
  //
  // บุ๊กมาร์กเก็บโค้ดไว้ในตัวเอง แก้ไฟล์แล้วไม่ลากใหม่ก็ยังรันของเก่า และไม่มีทางรู้
  // จากภายนอกเลยว่าที่รันอยู่คือรุ่นไหน เสียเวลาไปหนึ่งรอบเต็มเพราะแยกไม่ออกว่า
  // "แก้แล้วไม่ได้ผล" หรือ "ยังไม่ได้ลากใหม่" — ขึ้นเลขไว้ ปัญหานี้จบ
  const BUILD = 'v9';

  // ── ดูว่าคลิกทำให้ Flow ขยับจริงไหม ──────────────────────────────────────
  //
  // v7 เช็คว่า "เมนูปิดแล้ว" ซึ่งไม่ใช่หลักฐานว่าเลือกสำเร็จ — คลิกที่ไม่โดนอะไรเลย
  // ก็ทำให้เมนูปิดได้ (overlay ปิดตัวเองเวลาคลิกนอกรายการ) v7 จึงรายงานว่ากด 3 ครั้ง
  // ไม่มีข้อผิดพลาด ทั้งที่ Chrome ไม่เคยถูกสั่งโหลดเลย
  //
  // หลักฐานจริงคือคำขอที่วิ่งออกไป — ถ้ากดติด Flow ต้องยิง request ไปเอาไฟล์
  // PerformanceObserver เห็นทุก resource ที่โหลด รวมถึงที่เกิดจาก XHR/fetch
  const netHits = [];
  let netObserver = null;
  try {
    netObserver = new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (/\.(mp4|webm|mov|jpe?g|png|gif)(\?|$)|download|videoblob|storage|media/i
            .test(e.name)) {
          netHits.push({ at: Date.now(), url: e.name.slice(0, 120) });
        }
      }
    });
    netObserver.observe({ entryTypes: ['resource'] });
  } catch (e) { /* เบราว์เซอร์เก่าไม่มีก็ข้ามไป ไม่ใช่เรื่องคอขาดบาดตาย */ }

  const netSince = (t) => netHits.filter((h) => h.at >= t);

  hud.innerHTML =
    `<b style="color:#2dd4bf">⬇️ Flow Download Helper</b>` +
    `<span style="color:#5f7a74;font-size:11px;margin-left:6px">${BUILD}</span>` +
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
  async function rightClick(el, corner) {
    const r = el.getBoundingClientRect();
    const p = corner === 'ซ้ายบน' ? { x: r.left + 8, y: r.top + 8 }
      : corner === 'ขวาล่าง' ? { x: r.right - 8, y: r.bottom - 8 }
      : { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    const at = { bubbles: true, cancelable: true, button: 2, buttons: 2,
                 clientX: p.x, clientY: p.y };
    el.dispatchEvent(new MouseEvent('pointerdown', at));
    el.dispatchEvent(new MouseEvent('mousedown', at));
    el.dispatchEvent(new MouseEvent('contextmenu', at));
    el.dispatchEvent(new MouseEvent('mouseup', at));
    await sleep(250);
  }

  // มุมที่จะลองคลิกขวา เรียงจากที่น่าจะเป็นการ์ดจริงที่สุด
  //
  // คลิกขวาที่ตัวรูปตรง ๆ ได้เมนูสั้นที่มีแค่ "ลบ" — Flow ไม่ถือว่ากำลังพูดถึงคลิปใบนั้น
  // แต่มุมอื่นของการ์ดอาจได้เมนูเต็ม จึงไล่ลองจนกว่าจะเจอเมนูที่มี "ดาวน์โหลด"
  // ระหว่างไล่ลองจะไม่กดรายการใดในเมนูเลย ปิดด้วย Escape อย่างเดียว
  //
  // เหลือ 3 มุมพอ — วัดบนหน้าจริงแล้วว่าไม่มีมุมไหนเปิดเมนูได้เลย การไล่ 8 มุมจึงเป็น
  // การเสียเวลา 13 วินาทีทุกครั้งก่อนจะไปโหมดที่ใช้ได้จริง
  function menuTargets(tile) {
    const out = [{ el: tile, corner: 'กลาง', ชื่อ: 'ไทล์ กลาง' }];
    if (tile.parentElement && tile.parentElement !== document.body) {
      out.push({ el: tile.parentElement, corner: 'กลาง', ชื่อ: 'ชั้นเหนือไทล์' });
    }
    const media = tile.querySelector('img, video');
    if (media) out.push({ el: media, corner: 'กลาง', ชื่อ: 'ตัวรูป' });
    return out;
  }

  // เปิดเมนูของการ์ดใบนี้ให้ได้เมนูที่มี "ดาวน์โหลด" — คืน {menuRoot, ชื่อมุม}
  async function openCardMenu(tile, onStep) {
    let lastSeen = '';
    for (const t of menuTargets(tile)) {
      if (stopped || !t.el.isConnected) continue;
      if (onStep) onStep(t.ชื่อ);
      const before = bodyKids();
      await rightClick(t.el, t.corner);
      const menu = await waitFor(() => newMenu(before), 1200);
      if (!menu) continue;
      if (findByText(menu, DOWNLOAD_LABELS)) return { menuRoot: menu, via: t.ชื่อ };
      lastSeen = (menu.innerText || '').split('\n')
        .map((s) => s.trim()).filter(Boolean).join(' | ');
      await closeMenu();   // เมนูไม่ใช่อันที่ต้องการ ปิดทิ้ง ไม่กดอะไรในนั้น
    }
    return { menuRoot: null, lastSeen };
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

  // ปุ่ม ⋮ ของการ์ดที่ผู้ใช้กำลังชี้อยู่ — ปุ่มไอคอนเล็ก อยู่ในจอ ไม่ใช่แถบหัวเว็บ
  function cardMenuButton() {
    const hit = [...document.querySelectorAll('button, [role="button"]')]
      .filter(isMenuButton)
      .map((b) => ({ b, r: b.getBoundingClientRect() }))
      .find(({ r }) => r.width > 0 && r.height > 0
        && r.width <= 48 && r.height <= 48
        && r.top >= HEADER_ZONE_PX
        && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth);
    return hit ? hit.b : null;
  }

  const posKey = (b) => {
    const r = b.getBoundingClientRect();
    return `${Math.round(r.left)},${Math.round(r.top)}`;
  };

  // ── ตรวจว่าเมนูเปิดหรือยัง ───────────────────────────────────────────────
  //
  // เดิมดูแค่ "มีลูกใหม่ใต้ body ไหม" ซึ่งพลาดตอน Flow แทรกเมนูเข้าไปในคอนเทนเนอร์
  // ที่มีอยู่แล้ว — ไม่มีลูกใหม่ให้เห็น สคริปต์เลยสรุปว่าเมนูไม่เปิด ทั้งที่เมนูเต็ม
  // กางอยู่ตรงหน้าพร้อมคำว่า "ดาวน์โหลด" (เห็นจากภาพหน้าจอของผู้ใช้)
  //
  // จึงจำทั้งลูกของ body และ element ที่มี role เมนู แล้วดูว่ามีอะไรใหม่ทางไหนก็ได้
  const visible = (n) => {
    const r = n.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const menuRoles = () =>
    document.querySelectorAll('[role="menu"], [role="menuitem"], [role="listbox"], [role="option"]');

  const bodyKids = () => ({
    kids: new Set(document.body.children),
    roles: new Set(menuRoles()),
  });

  const newMenu = (before) => {
    // เมนูที่มาเป็นลูกใหม่ของ body
    const kid = [...document.body.children].find(
      (n) => !before.kids.has(n) && (n.textContent || '').trim() && visible(n));
    if (kid) return kid;
    // เมนูที่แทรกอยู่ในคอนเทนเนอร์เดิม — จับจาก role ที่เพิ่งโผล่แทน
    const fresh = [...menuRoles()].filter((n) => !before.roles.has(n) && visible(n));
    if (fresh.length) {
      return fresh[0].closest('[role="menu"], [role="listbox"]')
          || fresh[0].parentElement || fresh[0];
    }
    return null;
  };

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
      const target = clickTarget(quality);
      describeClick('ตัวเลือกความละเอียด', target);
      if (!safeClick(quality, 'เลือกความละเอียด')) {
        return 'ตัวเลือกความละเอียดเข้าข่ายลบ — ไม่กด';
      }
      // เมนูปิดอย่างเดียวไม่พอ — ต้องเห็นว่ามีคำขอวิ่งออกไปด้วย
      const t0 = Date.now();
      const closed = await waitFor(() => !document.body.contains(target)
        || !visible(target), 2000);
      if (!closed) return 'กดตัวเลือกความละเอียดแล้วเมนูไม่ปิด — คลิกไม่ติด';

      // บันทึกคำขอไว้ดูเฉย ๆ — ใช้เป็นข้อพิสูจน์ไม่ได้
      //
      // v8 เคยถือว่า "มีคำขอวิ่งออกไป = Flow รับคำสั่งแล้ว" และรายงานว่าสำเร็จครบ 14
      // ครั้ง ทั้งที่ประวัติดาวน์โหลดของ Chrome บอกว่าไม่มีไฟล์เลย สาเหตุคือหน้า Flow
      // โหลดรูปย่อของคลิปตลอดเวลาที่เราเลื่อนไปทีละใบ คำขอพวกนั้นเข้าเกณฑ์อยู่แล้ว
      // การเลื่อนหน้าจึงสร้าง "หลักฐาน" ขึ้นมาเอง
      await sleep(1200);
      const fired = netSince(t0);
      if (fired.length) {
        console.log('[flow-helper] คำขอหลังกด (อาจเป็นรูปย่อจากการเลื่อนหน้า):',
                    fired.map((h) => h.url.slice(0, 90)).join(' , '));
      } else {
        console.log('[flow-helper] ไม่มีคำขอใดวิ่งออกไปหลังกด');
      }
    } else {
      // เผื่อ UI รุ่นที่กดแล้วโหลดตรง ไม่มีเมนูย่อย
      describeClick('รายการดาวน์โหลด', clickTarget(item));
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

  // ตอนรอผู้ใช้ชี้เมาส์ไม่ใช่การค้าง — คนอาจละสายตาไปทำอย่างอื่นก่อน จึงยกเว้น
  // ตัวจับเวลาให้ขั้นนี้ ไม่งั้นมันจะตัดจบเองทั้งที่ทุกอย่างปกติ
  let waitingForUser = false;

  const ticker = setInterval(() => {
    if (!waitingForUser && Date.now() - stepAt > STEP_TIMEOUT_MS && !stuckAt) {
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

  // จำด้วย src ของสื่อ เพราะ node จะหลุดเมื่อ Flow เรนเดอร์รายการใหม่หลังโหลดเสร็จ
  const seen = new Set();
  const keyOf = (t) => {
    const m = t.querySelector('img, video');
    return m ? (m.currentSrc || m.src || m.getAttribute('poster') || '') : '';
  };

  setStep('กำลังหาคลิปในหน้า');
  total = findTiles().length;
  log(`เจอสื่อ ${total} ชิ้น (สูงสุด ${MAX_PER_RUN} ไฟล์ต่อรอบ)`);
  if (!total) {
    clearInterval(ticker);
    say('หาคลิปในหน้าไม่เจอ — เลื่อนหน้าให้เห็นคลิปก่อนแล้วกดใหม่');
    hud.querySelector('#fdh-stop').textContent = 'ปิด';
    hud.querySelector('#fdh-stop').onclick = () => hud.remove();
    return;
  }

  // ── ลองคลิกขวาแค่ใบเดียว แล้วค่อยตัดสิน ──────────────────────────────────
  // วัดบนหน้าจริงแล้ว: ยิง contextmenu ครบ 8 มุม ไม่มีเมนูโผล่สักมุม — Flow ไม่รับ
  // event สังเคราะห์ (น่าจะเช็ค isTrusted) เหมือนที่ :hover ก็ปลอมไม่ได้
  // จึงลองแค่ใบแรกใบเดียวพอ ถ้าไม่ขึ้นก็ไม่เสียเวลาไล่ลองอีก 14 ใบ
  setStep('ลองคลิกขวา');
  const first = findTiles()[0];
  let autoMode = false;
  if (first) {
    const probe = await openCardMenu(first, (n) => setStep(`ลองคลิกขวา — ${n}`));
    if (probe.menuRoot) {
      autoMode = true;
      log(`คลิกขวาใช้ได้ที่: ${probe.via}`);
      await closeMenu();
    } else if (probe.lastSeen) {
      menuDump = probe.lastSeen;
      log('คลิกขวาเปิดเมนูได้ แต่ไม่มี "ดาวน์โหลด" ในนั้น');
    } else {
      log('คลิกขวาแบบสคริปต์ไม่มีผลบนหน้านี้ — เปลี่ยนเป็นโหมดชี้เมาส์');
    }
  }

  if (autoMode) {
    // ── ทางอัตโนมัติ ─────────────────────────────────────────────────────
    for (let i = 0; i < total && ok < MAX_PER_RUN && !stopped; i++) {
      setStep(`เลื่อนไปคลิปที่ ${i + 1}`);
      const tile = findTiles().find((t) => keyOf(t) && !seen.has(keyOf(t)));
      if (!tile) break;
      seen.add(keyOf(tile));

      tile.scrollIntoView({ block: 'center', behavior: 'smooth' });
      await sleep(500);

      setStep(`คลิกขวาคลิปที่ ${i + 1}`);
      const { menuRoot } = await openCardMenu(tile);
      if (!menuRoot) { problems.push('คลิกขวาแล้วเมนูไม่เปิด'); await closeMenu(); continue; }

      setStep(`กดดาวน์โหลดคลิปที่ ${i + 1}`);
      const res = await downloadFromMenu(menuRoot);
      if (res !== true) { problems.push(res); await closeMenu(); continue; }

      ok++;
      log(`ดาวน์โหลดแล้ว ${ok} ไฟล์`);
      setStep('รอเมนูปิด');
      await waitFor(() => !document.body.contains(menuRoot), 1500);
      await closeMenu();
      setStep('พักก่อนไฟล์ถัดไป');
      await humanDelay();   // หน่วงแบบคน — กันยิงถี่
    }
  } else {
    // ── ทางที่ต้องมีเมาส์จริง ────────────────────────────────────────────
    // แถบ ⋮ โผล่จาก :hover ซึ่งสคริปต์สร้างไม่ได้ แต่ทุกขั้นหลังจากนั้นสั่งได้หมด
    // จึงรอให้ผู้ใช้ชี้เมาส์ แล้วรับช่วงต่อ — 4 จังหวะต่อคลิปเหลือแค่วางเมาส์
    let lastKey = '';
    while (ok < MAX_PER_RUN && !stopped) {
      setStep('รอคุณชี้เมาส์ที่คลิป 👉');
      waitingForUser = true;
      const btn = await waitFor(
        () => { const b = cardMenuButton(); return b && posKey(b) !== lastKey ? b : null; },
        180000);
      waitingForUser = false;
      setStep('เจอแล้ว');
      if (!btn) break;
      lastKey = posKey(btn);

      setStep('เจอแล้ว — กำลังเปิดเมนู');
      const before = bodyKids();
      await hover(btn);
      if (!safeClick(btn, 'เปิดเมนู')) { problems.push('ปุ่มที่จับได้เข้าข่ายลบ'); continue; }

      const menuRoot = await waitFor(() => newMenu(before), 2500);
      if (!menuRoot) { problems.push('กด ⋮ แล้วเมนูไม่เปิด'); await closeMenu(); continue; }

      setStep('กดดาวน์โหลด');
      const res = await downloadFromMenu(menuRoot);
      if (res !== true) { problems.push(res); await closeMenu(); continue; }

      ok++;
      log(`ดาวน์โหลดแล้ว ${ok} ไฟล์`);
      setStep('รอเมนูปิด');
      await waitFor(() => !document.body.contains(menuRoot), 1500);
      await closeMenu();
      setStep('✅ เสร็จใบนี้ — เลื่อนเมาส์ไปใบถัดไป');
      await humanDelay();
    }
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
  // "กดไปแล้ว" ไม่เท่ากับ "ได้ไฟล์"
  //
  // รอบจริงรายงานว่าดาวน์โหลด 15 ชิ้น แต่มีไฟล์ลงเครื่องแค่ 1 — ตัวเลขนี้นับจำนวน
  // ครั้งที่กดปุ่มในเมนู ซึ่งสคริปต์ในหน้าเว็บมองไม่เห็นว่าไฟล์ลงจริงหรือไม่
  // (ไม่มีสิทธิ์อ่านไฟล์ในเครื่อง) การเรียกมันว่า "ดาวน์โหลดแล้ว" คือการโกหก
  // จึงเปลี่ยนถ้อยคำให้ตรงกับสิ่งที่รู้จริง แล้วชี้ให้ไปดูของจริงที่คิวอนุมัติ
  say(`<b>สั่งดาวน์โหลดไปแล้ว ${ok} ครั้ง</b>`
    + '<br><span style="color:#fbbf24">สคริปต์ยืนยันไม่ได้ว่าไฟล์ออกจริงหรือไม่ '
    + '— มันมองไม่เห็นไฟล์ในเครื่อง</span>'
    + '<br><span style="color:#9aa5a2">ของที่มาถึงจริงดูที่หน้า “คิวอนุมัติ” ในแอป '
    + 'ถ้าไม่มีอะไรเพิ่ม แปลว่าการกดแบบสคริปต์ไม่ได้ผลบนหน้านี้ '
    + 'ให้คลิกขวาโหลดเองแทน แล้วระบบจะจัดไฟล์ต่อให้เอง</span>'
    + `${stuckNote}${note}${dumpNote}`
    + (ok >= MAX_PER_RUN ? '<br>ครบเพดานต่อรอบแล้ว กดบุ๊กมาร์กใหม่ได้ถ้ายังเหลือ' : ''));
  if (stuckAt) console.warn('[flow-helper] ค้างที่ขั้น: ' + stuckAt);
  hud.querySelector('#fdh-stop').textContent = 'ปิด';
  hud.querySelector('#fdh-stop').onclick = () => hud.remove();
  log('เสร็จแล้ว ไฟล์จะไปอยู่ในโฟลเดอร์ดาวน์โหลดของ Chrome');
})();

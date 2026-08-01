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
  const BUILD = 'v16';

  // ── ชื่อไฟล์จาก prompt บนการ์ด ───────────────────────────────────────────
  //
  // Flow ตั้งชื่อไฟล์ที่มันโหลดเองตาม prompt ซึ่งพาหมวดฉากติดมาด้วย คิวอนุมัติจึง
  // อ่านออกว่าคลิปนี้ถ่ายมาเพื่ออะไรและให้คะแนน Mandala ได้ พอเราโหลดตรงจาก URL
  // ชื่อกลายเป็น flow_<uuid> ข้อมูลนั้นหายไปหมด — ดึงข้อความจากการ์ดมาแทน
  //
  // ไล่จากที่แน่นอนที่สุดไปหาที่คลุมเครือที่สุด แล้วหยุดที่อันแรกที่ใช้ได้
  const ICON_WORD = /^[a-z_]{3,24}$/;          // more_vert, play_circle ฯลฯ ไม่ใช่ prompt

  function promptTextFor(media) {
    const attrs = ['alt', 'title', 'aria-label'];
    let el = media;
    for (let up = 0; up <= 5 && el; up++) {
      for (const a of attrs) {
        const v = (el.getAttribute && el.getAttribute(a) || '').trim();
        if (v.length >= 8 && !ICON_WORD.test(v)) return v;
      }
      el = el.parentElement;
    }
    // ไม่มี attribute ก็ลองข้อความในการ์ด แต่ต้องยาวพอจะเป็นประโยค ไม่ใช่ชื่อไอคอน
    //
    // หยุดไต่เมื่อเจอ element ที่หุ้มสื่อมากกว่าชิ้นเดียว — นั่นคือกริดไม่ใช่การ์ด
    // และข้ามตัวที่หุ้ม HUD ของเราเอง ไม่งั้นพอไต่ถึง body จะได้ชื่อไฟล์เป็น
    // "Flow_Download_Helperv12" ซึ่งเป็นข้อความของสคริปต์เอง (เจอมาแล้วตอนเทสต์)
    el = media.parentElement;
    for (let up = 0; up < 5 && el; up++) {
      if (el.querySelectorAll('img, video').length > 1) break;
      if (!el.contains(hud)) {
        const t = (el.innerText || '').split('\n')
          .map((s) => s.trim())
          .filter((s) => s.length >= 12 && !ICON_WORD.test(s))[0];
        if (t) return t;
      }
      el = el.parentElement;
    }
    return '';
  }

  // ทำให้เป็นชื่อไฟล์ที่ Windows รับได้ และสั้นพอจะอ่านออก
  function safeName(text, id) {
    const cleaned = (text || '')
      // เก็บเฉพาะตัวอักษร ตัวเลข ขีด และเว้นวรรค แทนการไล่แบนอักขระต้องห้าม
      //
      // เขียนแบบแบนต้องใส่เครื่องหมายคำพูดลงใน regex literal ซึ่งตัวตัดคอมเมนต์ตอน
      // สร้างบุ๊กมาร์กอ่านว่าเป็นจุดเริ่มสตริง แล้วเลิกตัดคอมเมนต์ไปทั้งช่วง โค้ดโต
      // จาก 19k เป็น 27k โดยไม่มีอาการบอก — วิธีนี้ไม่ต้องมีเครื่องหมายคำพูดเลย
      // ต้องมี \p{M} ด้วย ไม่ใช่แค่ \p{L} — สระและวรรณยุกต์ไทยเป็น mark ไม่ใช่ letter
      // ถ้าไม่ใส่ "สบู่" จะเหลือ "สบ" (เจอมาแล้วตอนเทสต์)
      .replace(/[^\p{L}\p{M}\p{N}_\- ]/gu, ' ')
      .replace(/\s+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 60);
    // ใส่ id ต่อท้ายเสมอ — prompt เดียวกันสร้างได้หลายคลิป ถ้าไม่มีจะชนกัน
    return cleaned ? `${cleaned}_${id}.mp4` : `flow_${id}.mp4`;
  }

  // เก็บ URL ของสื่อจากทุกที่ที่พอจะหาได้ในหน้า
  function mediaUrls() {
    const out = new Map();          // url -> ชื่อไฟล์ที่จะตั้ง
    const add = (u, prompt) => {
      if (!u || u.startsWith('data:') || u.startsWith('blob:')) return;
      if (out.has(u)) return;
      // URL ของ Flow เป็น .../media.getMediaUrlRedirect?name=<uuid> ซึ่งไม่มีนามสกุล
      // และ path เหมือนกันทุกคลิป ต้องใช้ uuid มาตั้งชื่อ ไม่งั้นได้ชื่อซ้ำกันหมด
      let base = '';
      try {
        const parsed = new URL(u, location.href);
        const last = parsed.pathname.split('/').pop() || '';
        if (/\.\w{2,5}$/.test(last)) {
          base = last;
        } else {
          // id อยู่ได้สองที่: ?name=<uuid> ในลิงก์ redirect ของ labs.google
          // หรือท้าย path /video/<uuid> ในลิงก์ที่ CDN เซ็นมา — เอาอันที่มี
          const id = (parsed.searchParams.get('name') || last || '').slice(0, 8)
                     || String(out.size + 1);
          base = safeName(prompt, id);
        }
      } catch (e) {
        base = safeName(prompt, out.size + 1);
      }
      out.set(u, base);
    };
    for (const v of document.querySelectorAll('video')) {
      add(v.currentSrc || v.src, promptTextFor(v));
    }
    try {
      for (const e of performance.getEntriesByType('resource')) {
        // ไฟล์จริงของ Flow ไม่มีนามสกุล — เป็น flow-content.google/video/<uuid>?Signature=…
        // เกณฑ์เดิมบังคับ .mp4 จึงไม่เคยเจอ URL ที่ต้องการเลยสักอัน
        // ใช้ indexOf ไม่ใช่ regex — ตัวตัดคอมเมนต์ตอนสร้างบุ๊กมาร์กไม่รู้จัก regex
        // literal พอเจอ \// ท้ายรูปแบบก็อ่านเป็นคอมเมนต์แล้วกินโค้ดที่เหลือทั้งบรรทัด
        if (/\.(mp4|webm|mov)(\?|$)/i.test(e.name) || e.name.indexOf('/video/') >= 0) {
          // มาจาก resource timing ไม่มีการ์ดให้ดู จึงไม่มี prompt — ได้ชื่อ flow_<id>
          add(e.name, '');
        }
      }
    } catch (e) { /* ไม่มีก็ข้าม */ }
    return [...out.entries()].map(([url, name]) => ({ url, name }));
  }

  // แปลงลิงก์ redirect เป็นลิงก์จริงที่ CDN เซ็นมา
  //
  // <video src> ชี้ไป labs.google/…/getMediaUrlRedirect?name=… ซึ่งต้องมีคุกกี้ถึงจะ
  // เข้าได้ ฝั่ง Python ไม่มีคุกกี้จึงได้ 401 ทุกตัว (8 จาก 13 ในรอบจริง) ส่วนตัวที่
  // สำเร็จคือลิงก์ flow-content.google ที่เก็บมาจาก resource timing ซึ่งเซ็นมาแล้ว
  //
  // เบราว์เซอร์แปลงให้ได้เพราะมันมีคุกกี้ — ยิง fetch แล้วอ่าน response.url ที่ตามลิงก์
  // ไปจนสุด แล้ว abort ทิ้งทันที ไม่ต้องโหลดตัวไฟล์ลงมา (คลิปละ 2.4MB × 15 คงเปล่า
  // ประโยชน์) และชื่อจาก prompt ก็ผูกอยู่กับลิงก์กลุ่มนี้พอดี จึงติดไปด้วย
  async function resolveSigned(entries) {
    const byFinal = new Map();
    for (const e of entries) {
      let final = e.url;
      if (e.url.indexOf('getMediaUrlRedirect') >= 0) {
        try {
          const ctrl = new AbortController();
          const res = await fetch(e.url, { signal: ctrl.signal });
          if (res.url) final = res.url;
          ctrl.abort();
        } catch (err) {
          // แปลงไม่ได้ก็ส่งของเดิมไป ฝั่งแอปจะรายงาน 401 ให้เห็นเอง
          console.warn('[flow-helper] แปลงลิงก์ไม่ได้:', String(err).slice(0, 60));
        }
      }
      // ลิงก์เดียวกันอาจมาทั้งแบบ redirect และแบบเซ็นแล้ว — เก็บอันที่มีชื่อไว้
      const prev = byFinal.get(final);
      if (!prev || (!prev.name && e.name)) byFinal.set(final, { url: final, name: e.name });
    }
    return [...byFinal.values()];
  }

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
  // วัดบนหน้าจริงแล้ว และผลกลับหัวกับที่เดาไว้:
  //   ตัวรูป/วิดีโอ → เมนูเต็ม 22 รายการ มี "ดาวน์โหลด"
  //   ลิงก์ <a>     → เมนูเต็มเหมือนกัน
  //   ไทล์ขึ้นไป     → เมนูสองรายการ มีแต่ "ลบ"
  // เดิมเรียงไทล์ไว้อันดับแรกและตัวรูปไว้ท้ายสุด จึงเปิดเมนูลบก่อนทุกครั้งโดยไม่จำเป็น
  // ตอนนี้เอาตัวที่ให้เมนูเต็มขึ้นก่อน และไม่แตะไทล์เลย — เมนูที่มีแต่ "ลบ" ไม่มีอะไร
  // ให้เราอยู่แล้ว การเปิดมันคือความเสี่ยงเปล่า ๆ
  function menuTargets(tile) {
    const out = [];
    const media = tile.querySelector('img, video');
    if (media) out.push({ el: media, corner: 'กลาง', ชื่อ: 'ตัวรูป/วิดีโอ' });
    const link = tile.closest('a') || tile.querySelector('a');
    if (link) out.push({ el: link, corner: 'กลาง', ชื่อ: 'ลิงก์ <a>' });
    return out.length ? out : [{ el: tile, corner: 'กลาง', ชื่อ: 'ไทล์' }];
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

  // ── ทางที่ 1: โหลดจาก URL ตรง ๆ ─────────────────────────────────────────
  // ต้องมาก่อนการหาไทล์ เพราะไม่ได้พึ่งไทล์เลย — URL มีได้แม้หาการ์ดไม่เจอ
  // (เคยวางไว้ทีหลัง แล้วโดนบรรทัด "หาคลิปในหน้าไม่เจอ" ตัดจบก่อนถึง)
  // ไม่ต้องแตะเมนูของ Flow เลย จึงไม่ติดกำแพงที่วัดมาแล้วสองชั้น
  // ทำก่อนเสมอ เพราะถ้าได้ก็จบ และเป็นทางเดียวที่รู้ผลทันทีว่าไฟล์ออกหรือไม่
  setStep('หา URL ของไฟล์ในหน้า');
  const found = mediaUrls();
  log(`เจอ URL วิดีโอในหน้า ${found.length} รายการ`);
  if (found.length) {
    setStep(`แปลงลิงก์ให้ใช้ได้นอกเบราว์เซอร์ (${found.length} รายการ)`);
    const urls = await resolveSigned(found);
    log(`แปลงแล้วเหลือ ${urls.length} รายการ (ตัดซ้ำ)`);
    clearInterval(ticker);
    const picked = urls.slice(0, MAX_PER_RUN);

    // ไม่โหลดลงเครื่องแล้ว — ส่งลิงก์ให้แอปไปโหลดขึ้น Drive ตรง
    //
    // ลิงก์ที่ CDN เซ็นมาใช้ได้โดยไม่ต้องมีคุกกี้ ฝั่ง Python จึงดึงไฟล์เข้าหน่วยความจำ
    // แล้วอัปขึ้น Drive ได้เลย ไม่ต้องผ่านดิสก์ ไม่ต้องรอ Drive for Desktop ซิงก์
    // และไม่กินที่ในเครื่อง — ตรงกับที่ผู้ใช้ขอว่า "อย่าเพิ่งลงในเครื่อง"
    hud.querySelector('#fdh-msg').innerHTML =
      `<b>เจอคลิป ${picked.length} ไฟล์</b>`
      + '<br><span style="color:#9aa5a2">กดคัดลอก แล้วเอาไปวางในแอป หน้า '
      + '“คิวอนุมัติ” → ช่อง “วางลิงก์จาก Flow” → เลือก “ขึ้น Google Drive ตรง”</span>'
      + '<textarea id="fdh-urls" readonly style="width:100%;height:110px;margin-top:8px;'
      + 'background:#0b0f12;color:#cfe;border:1px solid #2b3a36;border-radius:8px;'
      + 'padding:6px;font:11px/1.4 ui-monospace,monospace"></textarea>'
      + '<button id="fdh-copy" style="width:100%;margin-top:6px;padding:6px;'
      + 'border-radius:8px;border:1px solid #3d4f4a;background:#1b2724;color:#e8f0ee;'
      + 'cursor:pointer">📋 คัดลอกลิงก์ทั้งหมด</button>';
    const ta = hud.querySelector('#fdh-urls');
    // แนบชื่อที่อ่านจาก prompt มาด้วยเป็นคอมเมนต์ ฝั่งแอปตัดทิ้งตอนแยกลิงก์
    ta.value = picked.map((m) => `${m.url}  # ${m.name}`).join('\n');
    hud.querySelector('#fdh-copy').onclick = async () => {
      ta.select();
      try { await navigator.clipboard.writeText(ta.value); }
      catch (e) { document.execCommand('copy'); }
      hud.querySelector('#fdh-copy').textContent = '✅ คัดลอกแล้ว';
    };
    hud.querySelector('#fdh-stop').textContent = 'ปิด';
    hud.querySelector('#fdh-stop').onclick = () => hud.remove();
    log('เสร็จแล้ว — เอาลิงก์ไปวางในแอป');
    return;
  }
  log('ไม่เจอ URL วิดีโอในหน้า — ลองทางเมนูแทน');

  setStep('กำลังหาคลิปในหน้า');
  total = findTiles().length;
  log(`เจอสื่อ ${total} ชิ้น (สูงสุด ${MAX_PER_RUN} ไฟล์ต่อรอบ)`);
  if (!total) {
    clearInterval(ticker);
    say('หาคลิปในหน้าไม่เจอ และไม่เจอ URL ของไฟล์ด้วย'
      + '<br><span style="color:#9aa5a2">ลองเลื่อนหน้าให้เห็นคลิป หรือกดเล่นสักคลิป '
      + 'หนึ่งก่อน แล้วกดบุ๊กมาร์กใหม่ — พอคลิปถูกโหลด URL จะโผล่ให้จับได้</span>');
    hud.querySelector('#fdh-stop').textContent = 'ปิด';
    hud.querySelector('#fdh-stop').onclick = () => hud.remove();
    return;
  }

  // ── ทางที่ 2: ผ่านเมนูคลิกขวา ────────────────────────────────────────────
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

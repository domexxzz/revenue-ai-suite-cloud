"""Scene presets — pickable themes for image/video master prompts.

Each preset is one creative direction ("ห้องแล็บ", "นักเรียน", "UGC รีวิวจริง")
expressed as the concrete levers a generation model responds to: setting, props,
lighting, camera, who is on screen, and a three-shot breakdown for video.

The master prompt builders in content_copilot compose these with the brand's own
subject line, so the same product can be shot twenty different ways without the
user writing a prompt by hand.
"""

from __future__ import annotations

# group → ordering in the picker
GROUPS = [
    "🧪 ความน่าเชื่อถือ / วิทยาศาสตร์",
    "👤 คน / ไลฟ์สไตล์",
    "🏠 สถานที่ / บรรยากาศ",
    "📸 สไตล์ภาพ",
    "🎁 โปรโมชัน / เทศกาล",
]

# `cast` empty means product-only (no humans in frame).
PRESETS: dict[str, dict] = {

    # ── 🧪 ความน่าเชื่อถือ / วิทยาศาสตร์ ──────────────────────────────────────
    "lab": {
        "goal": "🔬 สร้างความน่าเชื่อถือ — ตอกย้ำว่ามีงานวิจัยรองรับ ลดความกลัวว่าจะแพ้",
        "signals": ["วิจัย", "เวชสำอาง", "ผู้เชี่ยวชาญ", "ทดสอบ", "มาตรฐาน", "ปลอดภัย"],
        "label": "🧪 ห้องแล็บ / งานวิจัย",
        "group": "🧪 ความน่าเชื่อถือ / วิทยาศาสตร์",
        "setting": "a clean modern research laboratory, white surfaces, subtle glassware "
                   "and pipettes softly blurred in the background",
        "styling": "sterile lab bench, a few precision instruments, nothing cluttered",
        "lighting": "cool even diffused laboratory lighting, crisp and clinical, minimal shadow",
        "camera": "50mm lens, f/4, straight-on eye-level angle, everything precisely aligned",
        "cast": "",
        "mood": "clinical, precise, trustworthy, evidence-backed",
        "shots": [
            "Macro detail of the formula texture on a clean glass slide",
            "Product standing on the lab bench with instruments softly out of focus behind",
            "Slow settle on the product, label sharp and centred",
        ],
    },
    "ingredient": {
        "goal": "🌿 ให้ความรู้ — อธิบายว่าสารสกัดแต่ละตัวทำอะไร",
        "signals": ["สารสกัด", "ไนอะซินาไมด์", "BHA", "ใบบัวบก", "ชะเอมเทศ", "วิตามิน", "ส่วนผสม"],
        "label": "🌿 สารสกัดเด่น",
        "group": "🧪 ความน่าเชื่อถือ / วิทยาศาสตร์",
        "setting": "a clean neutral surface surrounded by the raw botanical ingredients "
                   "the formula is made from",
        "styling": "fresh leaves, herbs and extract droplets arranged in a deliberate arc, "
                   "a small glass dish of the raw material",
        "lighting": "soft directional daylight, gentle shadow revealing texture",
        "camera": "100mm macro lens, f/2.8, slight top-down angle",
        "cast": "",
        "mood": "natural, pure, ingredient-led",
        "shots": [
            "Extreme macro of a fresh botanical leaf with a water droplet",
            "Ingredients arranged around the product, camera drifting across them",
            "Product centred with the ingredients framing it symmetrically",
        ],
    },
    "clinic": {
        "goal": "🩺 สร้างความมั่นใจ — วางแบรนด์ให้ดูเป็นมืออาชีพด้านผิว",
        "signals": ["เวชสำอาง", "ผู้เชี่ยวชาญ", "ผิวแพ้ง่าย", "อ่อนโยน", "แนะนำ"],
        "label": "🩺 คลินิกผิวหนัง",
        "group": "🧪 ความน่าเชื่อถือ / วิทยาศาสตร์",
        "setting": "a calm dermatology clinic consultation room, soft white and pale "
                   "green tones, professional but warm",
        "styling": "minimal clinical props, a folded clean towel, no medical clutter",
        "lighting": "soft even clinical lighting, flattering and shadow-free",
        "camera": "35mm lens, f/2.8, natural eye-level documentary framing",
        "cast": "a friendly Thai skincare professional in a clean white coat, "
                "fully visible in frame with a calm reassuring expression, "
                "natural healthy skin",
        "mood": "reassuring, expert, calm",
        "shots": [
            "The professional presents the product to camera, face and hands both "
            "clearly in frame",
            "Close-up of the product being placed on the consultation counter, "
            "the professional still visible behind it",
            "Product resting on the counter with the professional softly blurred behind",
        ],
    },

    # ── 👤 คน / ไลฟ์สไตล์ ─────────────────────────────────────────────────────
    "teen": {
        "goal": "🧒 เข้าถึงวัยรุ่นผิวมัน — กลุ่มที่สิวขึ้นง่ายและกังวลเรื่องความมั่นใจ",
        "signals": ["วัยรุ่น", "สิว", "ผิวมัน", "มั่นใจ", "T-Zone", "รูขุมขน"],
        "label": "🧒 วัยรุ่น",
        "group": "👤 คน / ไลฟ์สไตล์",
        "setting": "a bright casual bedroom corner with soft colourful accents",
        "styling": "relaxed everyday items, a small mirror, simple and un-staged",
        "lighting": "bright soft daylight from a window, fresh and airy",
        "camera": "35mm lens, f/2.0, natural handheld-style eye-level framing",
        "movement": "light handheld feel — gentle natural sway, small organic "
                    "reframes. Loose and human rather than mechanically smooth",
        "cast": "a cheerful Thai teenager with healthy natural skin, minimal makeup, "
                "genuine relaxed expression",
        "mood": "youthful, honest, upbeat",
        "shots": [
            "Teen holding the product up to camera with a natural smile",
            "Close-up of the product being applied, calm and unhurried",
            "Teen looking into the mirror confidently, product on the shelf beside",
        ],
    },
    "student": {
        "goal": "🎓 เข้าถึงนักเรียนนักศึกษา — ชีวิตเร่งรีบ พักผ่อนน้อย สิวขึ้นง่าย",
        "signals": ["วัยรุ่น", "นักศึกษา", "สิว", "ผิวมัน", "มั่นใจ"],
        "label": "🎓 นักเรียน / นักศึกษา",
        "group": "👤 คน / ไลฟ์สไตล์",
        "setting": "a university study desk or campus corner, books and a laptop nearby",
        "styling": "study notes, a coffee cup, backpack — lived-in but tidy",
        "lighting": "natural afternoon daylight, warm and soft",
        "camera": "35mm lens, f/2.2, candid documentary angle",
        "movement": "observational documentary movement — slow drifts and small "
                    "reframes as if following the moment, not choreographing it",
        "cast": "a Thai university student in casual clothes, natural skin, focused "
                "then relaxed expression",
        "mood": "relatable, everyday, aspirational-but-real",
        "shots": [
            "Student at the desk, tired after studying, reaching for the product",
            "Close-up of the product on the desk beside open books",
            "Student looking refreshed and confident, product in frame",
        ],
    },
    "office": {
        "goal": "💼 เข้าถึงวัยทำงาน — หน้ามันระหว่างวัน เครื่องสำอางไหล",
        "signals": ["วัยทำงาน", "หน้ามัน", "T-Zone", "เครื่องสำอาง", "มลภาวะ", "PM2.5"],
        "label": "💼 วัยทำงาน / ออฟฟิศ",
        "group": "👤 คน / ไลฟ์สไตล์",
        "setting": "a modern minimal office desk or office washroom mirror",
        "styling": "laptop, notebook, a small plant — clean professional surface",
        "lighting": "cool daylight mixed with soft interior light",
        "camera": "50mm lens, f/2.0, composed eye-level framing",
        "cast": "a Thai working professional in smart casual clothing, natural skin, "
                "composed confident expression",
        "mood": "confident, capable, polished",
        "shots": [
            "Professional touching up during a busy workday",
            "Close-up of the product beside the laptop on the desk",
            "Confident look to camera, product resting in frame",
        ],
    },
    "male": {
        "goal": "🧔 ขยายกลุ่มผู้ชาย — ตลาดที่แบรนด์สกินแคร์ไทยยังแข่งกันน้อย",
        "signals": ["ผู้ชาย", "ผิวมัน", "สิว", "ล้างหน้า"],
        "label": "🧔 ผู้ชาย",
        "group": "👤 คน / ไลฟ์สไตล์",
        "setting": "a clean modern bathroom with dark stone or concrete tones",
        "styling": "simple masculine grooming items, folded dark towel",
        "lighting": "directional side light with defined contrast, slightly moody",
        "camera": "50mm lens, f/2.0, three-quarter angle",
        "cast": "a Thai man with natural healthy skin, understated confident expression",
        "mood": "clean, straightforward, understated",
        "shots": [
            "Man washing his face, water and motion in frame",
            "Close-up of the product held in one hand",
            "Man looking at the mirror, calm and satisfied",
        ],
    },
    "friends": {
        "goal": "👯 กระตุ้นการบอกต่อ — ใช้แรงเพื่อนแนะนำเพื่อน",
        "signals": ["บอกต่อ", "รีวิว", "แนะนำ", "เพื่อน", "ลูกค้า"],
        "label": "👯 กลุ่มเพื่อน",
        "group": "👤 คน / ไลฟ์สไตล์",
        "setting": "a bright relaxed room or cafe table where friends are hanging out",
        "styling": "casual shared items, drinks, a phone on the table",
        "lighting": "warm natural daylight, lively and inviting",
        "camera": "35mm lens, f/2.2, candid group framing",
        "movement": "loose candid movement — the camera drifts between faces as the "
                    "moment unfolds, unstaged and natural",
        "cast": "two or three Thai friends laughing together, natural skin, genuine "
                "unposed interaction",
        "mood": "social, warm, word-of-mouth",
        "shots": [
            "Friends laughing while one shows the product to the others",
            "Close-up of the product being passed between hands",
            "Group smiling together, product visible on the table",
        ],
    },

    # ── 🏠 สถานที่ / บรรยากาศ ─────────────────────────────────────────────────
    "vanity": {
        "goal": "🪞 สอนวิธีใช้ — ทำให้เห็นว่าแทรกเข้ากิจวัตรได้ง่าย",
        "signals": ["ล้างหน้า", "กิจวัตร", "ใช้ทุกวัน", "routine", "ดูแลผิว"],
        "label": "🪞 โต๊ะเครื่องแป้ง / ห้องน้ำ",
        "group": "🏠 สถานที่ / บรรยากาศ",
        "setting": "a tidy vanity counter with a soft-lit mirror, pale marble surface",
        "styling": "a few elegant everyday skincare items, folded towel, small vase",
        "lighting": "soft warm vanity bulbs plus gentle daylight fill",
        "camera": "50mm lens, f/2.8, slight three-quarter angle",
        "cast": "a Thai woman doing her evening skincare routine, fully visible in "
                "frame and reflected in the mirror, natural bare skin, calm unhurried "
                "expression",
        "mood": "intimate, routine, self-care",
        "shots": [
            "She reaches across the vanity counter toward the product, "
            "face and hands both in frame",
            "Close-up as she places the product down on the marble, "
            "her reflection visible in the mirror behind",
            "She looks at her reflection calmly, the product settled in front of "
            "the softly lit mirror",
        ],
    },
    "morning": {
        "goal": "🌅 ย้ำความต่อเนื่อง — การดูแลผิวต้องทำสม่ำเสมอ",
        "signals": ["ทุกวัน", "ต่อเนื่อง", "เช้า", "กิจวัตร", "ดูแลผิว"],
        "label": "🌅 เช้าในห้องนอน",
        "group": "🏠 สถานที่ / บรรยากาศ",
        "setting": "a serene bedroom in early morning, rumpled white linen, window nearby",
        "styling": "linen sheets, a glass of water, soft neutral textiles",
        "lighting": "warm golden morning sunlight streaming through sheer curtains, "
                    "visible light rays",
        "camera": "50mm lens, f/1.8, low intimate angle",
        "cast": "",
        "mood": "calm, fresh start, restorative",
        "shots": [
            "Morning light creeping across the linen toward the product",
            "Close-up of the product glowing in the warm sunbeam",
            "Wide serene shot of the bedside with the product in focus",
        ],
    },
    "cafe": {
        "goal": "☕ สร้างการรับรู้ — วางแบรนด์ให้อยู่ในไลฟ์สไตล์คนเมือง",
        "signals": ["คนเมือง", "ไลฟ์สไตล์", "วัยทำงาน", "มั่นใจ"],
        "label": "☕ คาเฟ่",
        "group": "🏠 สถานที่ / บรรยากาศ",
        "setting": "a stylish minimal cafe table by a large window, city softly blurred outside",
        "styling": "a coffee cup, small notebook, warm wooden table surface",
        "lighting": "soft window daylight with pleasant bokeh behind",
        "camera": "50mm lens, f/1.8, eye-level lifestyle framing",
        "cast": "",
        "mood": "urban, everyday-premium, relaxed",
        "shots": [
            "Rack focus from the coffee cup to the product",
            "Close-up of the product on the wooden table, bokeh behind",
            "Wider table scene settling with the product centred",
        ],
    },
    "outdoor": {
        "goal": "☀️ ชูการปกป้อง — แดดและมลภาวะเป็นตัวกระตุ้นสิว",
        "signals": ["มลภาวะ", "PM2.5", "แดด", "ปกป้อง", "วิตามิน E"],
        "label": "☀️ กลางแจ้ง / แดด",
        "group": "🏠 สถานที่ / บรรยากาศ",
        "setting": "bright outdoors — a sunny terrace or greenery-lined path",
        "styling": "natural foliage, dappled shadows, a stone or wooden ledge",
        "lighting": "strong natural sunlight with crisp dappled leaf shadows",
        "camera": "35mm lens, f/2.8, slightly low angle against open sky",
        "cast": "",
        "mood": "energetic, protective, outdoor-ready",
        "shots": [
            "Sunlight and leaf shadows moving across the product",
            "Close-up with lens flare grazing the edge of the frame",
            "Product resting on a sunlit stone ledge against bright open sky",
        ],
    },
    "gym": {
        "goal": "🏋️ จับจังหวะเหงื่อ/หน้ามัน — ช่วงที่คนรู้สึกถึงปัญหาชัดที่สุด",
        "signals": ["หน้ามัน", "เหงื่อ", "คุมมัน", "รูขุมขน", "อุดตัน"],
        "label": "🏋️ ยิม / ออกกำลังกาย",
        "group": "🏠 สถานที่ / บรรยากาศ",
        "setting": "a modern gym locker area or training floor, dark tones with accent light",
        "styling": "a rolled towel, a stainless steel flask, gym bag",
        "lighting": "punchy directional light with strong contrast",
        "camera": "35mm lens, f/2.0, dynamic slightly-tilted angle",
        "cast": "a fit Thai person in gym clothes after a workout, fully visible in "
                "frame, natural skin with a light sheen of sweat, relaxed and "
                "energised expression",
        "mood": "active, sweat-proof, high-energy",
        "shots": [
            "The person pulls the product from their gym bag, whole upper body in "
            "frame, quick energetic motion",
            "Close-up of the product in their hand, condensation and water droplets "
            "on the surface",
            "The person sets the product on the bench and looks to camera, "
            "accent light behind them",
        ],
    },

    # ── 📸 สไตล์ภาพ ────────────────────────────────────────────────────────────
    "studio": {
        "goal": "🎞️ ภาพสินค้ามาตรฐาน — ใช้ซ้ำได้ทุกที่ ทั้งเว็บและโฆษณา",
        "signals": ["สินค้า", "สบู่", "แพ็กเกจ", "ราคา"],
        "label": "🎞️ สตูดิโอ สินค้าเดี่ยว",
        "group": "📸 สไตล์ภาพ",
        "setting": "a seamless studio backdrop in a soft neutral tone with a subtle "
                   "reflection beneath the product",
        "styling": "nothing but the product — pure negative space around it",
        "lighting": "single large softbox at 45 degrees plus a rim light, controlled falloff",
        "camera": "85mm lens, f/5.6, straight-on hero angle, product tack-sharp",
        "cast": "",
        "mood": "premium, deliberate, catalogue-perfect",
        "shots": [
            "Extreme close-up racking focus onto the label",
            "Slow orbit around the product on the seamless backdrop",
            "Product settling dead-centre, perfectly lit",
        ],
    },
    "flatlay": {
        "goal": "📐 เล่าองค์ประกอบ — โชว์ของครบชุดในภาพเดียว",
        "signals": ["ส่วนผสม", "เซ็ต", "สินค้า", "5-FREE"],
        "label": "📐 Flat lay จัดวาง",
        "group": "📸 สไตล์ภาพ",
        "setting": "a perfectly top-down flat lay on a textured neutral surface",
        "styling": "the product plus complementary items arranged in a balanced grid, "
                   "generous even spacing",
        "lighting": "even diffused overhead light, soft consistent shadows",
        "camera": "50mm lens, f/5.6, exact 90-degree top-down angle",
        "movement": "camera stays exactly parallel to the surface at 90 degrees — "
                    "only a slow vertical push-in or pull-out. Never tilts off "
                    "top-down, never orbits",
        "cast": "",
        "mood": "organised, editorial, considered",
        "shots": [
            "Top-down view with items sliding into their final positions",
            "Slow push-in toward the product at the centre",
            "Final balanced flat lay held steady",
        ],
    },
    "beforeafter": {
        "goal": "↔️ พิสูจน์ผลลัพธ์ — หลักฐานที่คนลังเลอยากเห็นที่สุด",
        "signals": ["ก่อน", "หลัง", "ผลลัพธ์", "รีวิว", "รอยสิว", "รอยดำ"],
        "label": "↔️ Before / After",
        "group": "📸 สไตล์ภาพ",
        "setting": "a clean neutral background split into two matched halves",
        "styling": "identical framing, lighting and distance on both sides so only the "
                   "result differs",
        "lighting": "flat even lighting, deliberately identical across both halves",
        "camera": "50mm lens, f/4, locked-off straight-on angle, zero camera movement",
        "movement": "camera locked off on a tripod — absolutely no push-in, drift or "
                    "handheld motion. The only movement in frame is the wipe "
                    "transition between the two halves",
        "cast": "the same subject on both sides, natural realistic skin, no retouching",
        "mood": "honest, evidence-based, restrained",
        "shots": [
            "Left half: the starting state, held steady",
            "Wipe transition revealing the right half",
            "Both halves side by side, product placed centre",
        ],
    },
    "ugc": {
        "goal": "📱 ใช้เสียงผู้ใช้จริง — น่าเชื่อกว่าโฆษณาที่แบรนด์พูดเอง",
        "signals": ["รีวิว", "ผู้ใช้จริง", "บอกต่อ", "ลูกค้า", "10,000"],
        "label": "📱 UGC รีวิวจริง",
        "group": "📸 สไตล์ภาพ",
        "setting": "an ordinary home room, genuinely un-styled and lived-in",
        "styling": "everyday clutter left as-is, nothing arranged for the camera",
        "lighting": "plain available indoor light, slightly uneven, unpolished",
        "camera": "front-facing phone camera look, slight handheld wobble, arm's-length "
                  "selfie distance",
        "movement": "handheld phone held at arm's length — natural human wobble and "
                    "small reframing adjustments throughout. Deliberately NOT smooth "
                    "or stabilised; it should feel filmed by the person themselves",
        "cast": "an ordinary Thai person talking casually to camera, natural skin "
                "including real texture, no professional makeup",
        "mood": "authentic, unpolished, trustworthy word-of-mouth",
        "shots": [
            "Person talking to camera holding the product up",
            "Quick handheld cut to the product in their hand",
            "Person nodding approvingly, product still in frame",
        ],
    },
    "macro": {
        "goal": "🔬 โชว์เนื้อสัมผัส — ตอบคนที่กลัวว่าจะแรงเกินจนผิวแห้ง",
        "signals": ["เนื้อสัมผัส", "ฟอง", "อ่อนโยน", "ไม่แห้งตึง", "ชุ่มชื้น"],
        "label": "🔬 Macro เนื้อสัมผัส",
        "group": "📸 สไตล์ภาพ",
        "setting": "an extreme close-up of the product's own surface texture filling "
                   "the whole frame",
        "styling": "the product's natural texture as it actually behaves — no invented "
                   "swirls or shapes the material could not form",
        "lighting": "raking side light that exposes every ridge and sheen",
        "camera": "100mm macro lens, f/4, extreme close-up, razor-thin focal plane",
        "movement": "macro slider — tiny precise moves only, plus slow focus racking. "
                    "At this magnification any large camera move reads as a blur",
        "cast": "",
        "mood": "tactile, sensory, quality-proving",
        "shots": [
            "The product's surface in extreme detail, catching the light as it turns",
            "A single water droplet meeting the surface in slow motion, "
            "beading and running off downward",
            "Pull back slightly to reveal the whole product in frame",
        ],
    },

    # ── 🎁 โปรโมชัน / เทศกาล ──────────────────────────────────────────────────
    "promo": {
        "goal": "🏷️ ปิดการขาย — เร่งการตัดสินใจด้วยราคา",
        "signals": ["ลด", "ราคา", "โปร", "แถม", "229", "350"],
        "label": "🏷️ โปรโมชัน / ลดราคา",
        "group": "🎁 โปรโมชัน / เทศกาล",
        "setting": "a bold graphic promotional backdrop with strong colour blocking and "
                   "clear empty space reserved for price text",
        "styling": "the product elevated on a simple podium, confetti or geometric accents",
        "lighting": "bright punchy commercial lighting, high contrast, vivid",
        "camera": "50mm lens, f/5.6, straight-on centred hero angle",
        "cast": "",
        "mood": "urgent, loud, impossible to scroll past",
        "shots": [
            "Product dropping onto the podium with a bounce",
            "Quick push-in as accents burst around it",
            "Product standing centred on the podium with clear space for the "
            "price overlay",
        ],
    },
    "gift": {
        "goal": "🎁 จับเทศกาล — ขยายโอกาสขายเป็นของฝาก",
        "signals": ["ของขวัญ", "เทศกาล", "เซ็ต", "แถม"],
        "label": "🎁 เซ็ตของขวัญ / เทศกาล",
        "group": "🎁 โปรโมชัน / เทศกาล",
        "setting": "a festive gifting scene with an elegant open gift box and ribbon",
        "styling": "satin ribbon, tissue paper, seasonal ornaments kept tasteful",
        "lighting": "warm celebratory light with soft sparkle highlights and gentle bokeh",
        "camera": "50mm lens, f/2.0, slightly overhead gifting angle",
        "cast": "a Thai person opening the gift, fully visible in frame with a "
                "delighted natural expression, seated at the table",
        "mood": "generous, celebratory, giftable",
        "shots": [
            "They untie the ribbon on the gift box, face and hands both in frame",
            "The box opens to reveal the product nestled inside, their reaction visible",
            "They hold the finished gift set up and smile, sparkle bokeh behind",
        ],
    },
}

DEFAULT_SCENE = "studio"


def scene_choices() -> list[str]:
    """Preset keys ordered by group, for a picker."""
    order = {g: i for i, g in enumerate(GROUPS)}
    return sorted(PRESETS, key=lambda k: (order.get(PRESETS[k]["group"], 99),
                                          PRESETS[k]["label"]))


def label_for(key: str) -> str:
    return PRESETS.get(key, PRESETS[DEFAULT_SCENE])["label"]


def group_for(key: str) -> str:
    return PRESETS.get(key, PRESETS[DEFAULT_SCENE])["group"]


def get(key: str) -> dict:
    return PRESETS.get(key) or PRESETS[DEFAULT_SCENE]


def has_people(key: str) -> bool:
    return bool(get(key).get("cast"))


def goal_for(key: str) -> str:
    """What this scene is trying to achieve, in one line."""
    return get(key).get("goal", "")


# ── Relevance scoring ───────────────────────────────────────────────────────────

def score_scenes(brand_text: str) -> dict[str, int]:
    """Score each scene 0-5 on how well it fits this brand's own material.

    This is a *fit* score, not a performance prediction: it counts how often the
    angle a scene takes shows up in the brand brief and the content already
    written for it (via Mandala AI). A scene about oily skin scores high for a
    brand whose personas are built around oily, acne-prone skin — it says nothing
    about how any post will perform.

    With no brand text there is nothing to measure against, so everything comes
    back 0 and callers should hide the score rather than show a fake one.
    """
    if not brand_text:
        return {k: 0 for k in PRESETS}

    low = brand_text.lower()
    raw = {k: sum(low.count(s.lower()) for s in p.get("signals", []))
           for k, p in PRESETS.items()}

    top = max(raw.values()) if raw else 0
    if top <= 0:
        return {k: 0 for k in PRESETS}

    # Log scale rather than linear. A handful of terms — "สิว", "ผิวมัน" — run away
    # with the count because the personas are written around them, and on a linear
    # scale that pinned three scenes at 5 and flattened every other one to 1,
    # which tells the user nothing. Compressing the top spreads the middle out.
    import math
    denom = math.log1p(top)
    return {
        k: (0 if v == 0 else max(1, min(5, round(1 + 4 * math.log1p(v) / denom))))
        for k, v in raw.items()
    }

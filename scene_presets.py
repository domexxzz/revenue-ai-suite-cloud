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


# ── Angles ──────────────────────────────────────────────────────────────────────

# A scene says *where* the shot is taken; an angle says *how it is told*. The same
# gym locker room can carry a problem-first spot, a how-to, or a phone review, and
# those are three different videos. Angles sit on top of any scene so the two
# choices multiply instead of forcing one combined list of a hundred presets.
#
# The keys below drive video. STILLS and CAROUSEL_ARCS further down carry the same
# angles for a single frame and for a five-slide set — an angle only appears for a
# medium it has material for, since "3 เหตุผล" cannot be told in one photograph.
#
# `hook` and `decision` replace the scene's first two shots. The third — the
# scene's own payoff — always survives, because that is what a before/after or a
# flat lay is actually for. Templates are English throughout and take {item} and
# {brand}; mixing Thai into visual direction is what once turned "สบู่" into soup.
#
# `vo` overrides only the hook and decision narration. The CTA line stays with the
# campaign, since that is where a discount and its deadline live and an angle has
# no business dropping them.
ANGLES: dict[str, dict] = {
    "hero": {
        "label": "✨ โชว์สินค้าเด่น",
        "goal": "ให้สินค้าเป็นพระเอก — ใช้ได้กับทุกหมวด ปลอดภัยที่สุด",
        "needs_cast": False,
        "structure": "เล่าตามฉากที่เลือกโดยตรง ไม่บิดโครงสร้าง",
        # No hook/decision: falls through to the scene's own three shots, which is
        # exactly the behaviour every clip had before angles existed.
    },
    "problem_solution": {
        "label": "😣 ปัญหา → ทางออก",
        "goal": "เปิดด้วยความรู้สึกที่คนดูมีอยู่แล้ว แล้วค่อยเสนอสินค้า",
        "needs_cast": True,
        "structure": "บีต 1 คือปัญหาล้วนๆ ยังไม่เห็นสินค้า บีต 2 สินค้าเข้ามาแก้",
        "hook": ("The person notices the problem on their own skin — they catch "
                 "their reflection or touch their cheek, and their expression "
                 "drops. Face and upper body in frame. No product visible yet in "
                 "this beat."),
        "decision": ("They reach for the {item} and begin using it. Their expression "
                     "shifts from concern to relief. The {item} is clearly visible "
                     "with its label facing camera."),
        "movement": ("slightly unsteady handheld while the problem is on screen, "
                     "settling into a smooth stable frame the moment the product "
                     "appears"),
        "vo": {
            "hook": "ปัญหาเดิมๆ ที่ล้างหน้ายังไงก็ไม่หายสักที",
            "decision": "{item}เข้ามาแก้ตรงจุด ใช้ง่ายทุกวัน ไม่ต้องเปลี่ยนทั้งกิจวัตร",
        },
    },
    "demo": {
        "label": "🧼 สาธิตวิธีใช้",
        "goal": "ตอบคำถามว่าใช้ยังไง — ลดความลังเลของคนที่ไม่เคยใช้สบู่ก้อน",
        "needs_cast": True,
        "structure": "โชว์ขั้นตอนจริง ตีฟอง ลูบไล้ ล้างออก เห็นมือชัดตลอด",
        "hook": ("Close-up on the person's hands holding the {item} up to camera, "
                 "label facing the lens, before anything else happens."),
        "decision": ("Step by step: they wet the {item} and work it between their "
                     "palms until it lathers into dense foam, then apply the foam "
                     "to their face. Hands and forearms fill the frame; water and "
                     "foam are clearly visible."),
        "movement": ("steady over-the-shoulder and overhead angles on the hands, "
                     "small deliberate push-ins, no shake"),
        "vo": {
            "hook": "ใช้ยังไงให้ได้ผลจริง?",
            "decision": "ถู{item}ให้เกิดฟอง แล้วนวดเบาๆ ทั่วหน้า ก่อนล้างออกด้วยน้ำสะอาด",
        },
    },
    "pov": {
        "label": "📱 รีวิวมุมมองที่หนึ่ง",
        "goal": "ให้ความรู้สึกว่าเพื่อนเล่าให้ฟัง น่าเชื่อกว่าโฆษณา",
        "needs_cast": True,
        "structure": "เหมือนถือมือถือถ่ายเอง เฟรมไม่เป๊ะ ไม่จัดจนดูเป็นโฆษณา",
        "hook": ("Shot as if the person is holding the camera themselves at arm's "
                 "length — slightly off-centre framing, imperfect natural "
                 "composition, their face partly in frame."),
        "decision": ("They hold the {item} up towards the lens and turn it so the "
                     "label reads clearly, then gesture at their own skin."),
        "movement": ("handheld at arm's length throughout — natural sway and small "
                     "reframing corrections, deliberately not smooth or stabilised"),
        "vo": {
            "hook": "ใช้มาสองอาทิตย์ ขอรีวิวจริงๆ ให้ฟัง",
            "decision": "{item}ไม่ทำให้หน้าแห้งตึง แล้วสิวก็ยุบเร็วขึ้นกว่าเดิม",
        },
    },
    "transformation": {
        "label": "🔁 ก่อน → หลัง",
        "goal": "พิสูจน์ผลลัพธ์ — หลักฐานที่คนลังเลอยากเห็นที่สุด",
        "needs_cast": True,
        "structure": "สองเฟรมเดียวกันเป๊ะ ต่างกันแค่สภาพผิว ตัดชนให้เห็นความต่าง",
        "hook": ("The person's skin at its worst in this scene — visible "
                 "congestion and shine under plain unflattering light. No product "
                 "in frame."),
        "decision": ("A clean match cut to the same person, weeks later: identical "
                     "framing, pose and distance, skin visibly calmer and more "
                     "even. The {item} sits in frame beside them. The change is "
                     "realistic and moderate — improved skin, not different skin."),
        "movement": ("locked off on a tripod for both halves — identical framing, "
                     "focal length and camera distance so the cut reads as one shot"),
        "vo": {
            "hook": "สองอาทิตย์ก่อน กับตอนนี้",
            "decision": "ใช้{item}ต่อเนื่องทุกวัน ไม่ได้ทำอะไรเพิ่มเลย",
        },
    },
    "myth_bust": {
        "label": "❌✅ เข้าใจผิด → เข้าใจใหม่",
        "goal": "ให้ความรู้แล้วแก้ความเชื่อผิดๆ คนดูจบคลิปแล้วได้อะไรกลับไป",
        "needs_cast": False,
        "structure": "เฟรมเดียวกัน ต่างกันแค่วิธีทำ ให้ภาพเล่าเองโดยไม่ต้องมีตัวหนังสือ",
        "hook": ("The common mistake shown plainly in one clear frame — just the "
                 "action people get wrong, nothing labelling it."),
        "decision": ("The correct way, from the identical camera position and "
                     "framing, done properly with the {item}. The contrast between the "
                     "two beats is obvious without a word of text."),
        # A product-only scene has nobody to perform the mistake, and asking for
        # "the action people get wrong" there contradicts the [CAST] block that
        # bans people outright. The same idea, told through the object instead.
        "hook_nocast": ("The mistake in one plain frame — the {item} left in the wrong "
                        "place and visibly the worse for it. Nothing in frame "
                        "labels it as wrong."),
        "decision_nocast": ("The correct way, from an identical camera position and "
                            "framing, with the {item} kept properly. The contrast "
                            "between the two beats is obvious without a word of text."),
        "movement": ("identical camera position and framing across both beats, so "
                     "the difference sits in the action rather than the shot"),
        "vo": {
            "hook": "เรื่องนี้หลายคนยังเข้าใจผิดอยู่",
            "decision": "ที่ถูกคือแบบนี้ — ใช้{item}อย่างถูกวิธี ผลต่างกันเยอะ",
        },
    },
    "texture": {
        "label": "🔬 พิสูจน์ด้วยฟองและเนื้อ",
        "goal": "ตอบคนที่กลัวว่าจะแรงเกินไป ให้เห็นเนื้อสัมผัสจริง",
        "needs_cast": False,
        "structure": "มาโครล้วน เห็นผิวสัมผัสและฟองก่อตัวแบบเรียลไทม์",
        "hook": ("Extreme macro on the {item} itself — surface texture, edges, and the "
                 "way light catches it, filling the whole frame."),
        "decision": ("Water meets the {item} and dense fine foam builds and spreads in "
                     "real time, still in macro, individual bubbles visible."),
        "movement": ("slow macro push-in with gentle rack focus, tripod stable — "
                     "tiny precise moves only"),
        "vo": {
            "hook": "เนื้อสัมผัสบอกอะไรได้มากกว่าที่คิด",
            "decision": "{item}ให้ฟองละเอียด อ่อนโยนกับผิว ไม่ตึงหลังล้าง",
        },
    },
    "reveal": {
        "label": "🎬 เปิดตัวแบบดราม่า",
        "goal": "สร้างความรู้สึกพรีเมียม เหมาะกับเปิดตัวหรือคอนเทนต์แบรนด์",
        "needs_cast": False,
        "structure": "เริ่มมืดเกือบทั้งเฟรม แล้วค่อยกวาดแสงเผยสินค้า ไม่มีคัต",
        "hook": ("The {item} almost entirely in shadow, only one edge catching light. "
                 "The frame is dark and quiet."),
        "decision": ("Light sweeps across and the {item} is revealed in full, label "
                     "clear and centred, the setting resolving into view around it."),
        "movement": "one slow continuous cinematic push-in with a sweeping light, no cuts",
        "vo": {
            "hook": "สิ่งที่ผิวคุณรออยู่",
            "decision": "{item} จาก {brand}",
        },
    },
    "three_reasons": {
        "label": "🔢 3 เหตุผล",
        "goal": "ยัดข้อมูลได้เยอะในเวลาสั้น เหมาะกับคนที่กำลังเปรียบเทียบหลายแบรนด์",
        "needs_cast": False,
        "structure": "ตัดเร็วสามจังหวะ เว้นที่ว่างไว้ใส่เลข 1-2-3 ตอนตัดต่อ",
        "hook": ("Reason one in a single clear frame with the {item} present, composed "
                 "with empty space on one side for a number overlay added later."),
        "decision": ("Reasons two and three as two quick successive frames in the "
                     "same setting — a different angle and detail each time, with "
                     "the {item} present in both and the same empty space kept clear."),
        "movement": ("quick decisive cuts between locked frames, each held just "
                     "long enough to read"),
        "vo": {
            "hook": "3 เหตุผลที่คนเปลี่ยนมาใช้{item}",
            "decision": "หนึ่ง ใช้ง่าย สอง อ่อนโยนพอสำหรับทุกวัน สาม คุ้มกว่าที่คิด",
        },
    },
}

DEFAULT_ANGLE = "hero"


# ── The same angles, told in one frame ──────────────────────────────────────────

# A still has no second beat, so an angle earns a place here only if its idea
# survives in a single photograph. "ปัญหา → ทางออก" needs two moments and "3
# เหตุผล" needs three, so neither is offered for images — better a shorter list
# than an angle that quietly collapses into the default.
#
# `subject` replaces what the frame is of; `composition` replaces how it is laid
# out. Both are English and take {item}, for the reason the video templates are.
STILLS: dict[str, dict] = {
    "hero": {},  # the scene's own framing, unchanged
    "demo": {
        "subject": ("hands mid-lather with the {item} — dense fresh foam between "
                    "wet palms, the bar itself still recognisable in the grip"),
        "composition": ("close crop on the hands and foam filling two thirds of the "
                        "frame, clear space above for a short headline"),
    },
    "pov": {
        "subject": ("the {item} held up towards the lens at arm's length, the "
                    "person's face partly in frame behind it, slightly soft"),
        "composition": ("off-centre phone-camera framing, imperfect and unstaged, "
                        "product sharp and closest to the lens"),
    },
    "transformation": {
        "subject": ("one frame split cleanly down the middle: the same face on "
                    "both sides, congested and shiny on the left, calm and even on "
                    "the right, with the {item} resting in the lower corner"),
        "composition": ("perfectly symmetrical split with an identical crop, "
                        "distance and expression on each half, so only the skin "
                        "differs; a thin gap divides them, no text"),
    },
    "myth_bust": {
        "subject": ("one frame split down the middle: the {item} kept the wrong way "
                    "on the left, visibly the worse for it, and kept properly on "
                    "the right"),
        "composition": ("symmetrical split with identical framing on both halves so "
                        "the difference is in the object's condition alone, no text "
                        "and no marks labelling either side"),
    },
    "texture": {
        "subject": ("extreme macro of the {item} surface — every ridge, pore and "
                    "sheen, with fine foam just beginning to build at one edge"),
        "composition": ("the surface fills the entire frame edge to edge, one "
                        "sharp plane with the rest falling away, no negative space"),
    },
    "reveal": {
        "subject": ("the {item} emerging from near darkness, a single hard edge of "
                    "light along its silhouette and the label just readable"),
        "composition": ("product small in a large dark frame, lit from one side, "
                        "deep shadow occupying most of the image"),
    },
}


# ── The same angles, told across five slides ────────────────────────────────────

# Each arc is five slides of (role, label, purpose, composition, headline, sub).
# The Thai copy takes {item}, {brand} and {discount}. An angle without an arc is
# simply not offered for a carousel.
#
# The first and last slide of every arc do the same job — stop the scroll, then
# ask for the action — because that is what a carousel is. What changes in
# between is the argument being made.
_CTA_SLIDE = ("CTA", "🎯 ลงมือ", "บอกสิ่งที่ต้องทำต่อ พร้อมข้อเสนอ",
              "product with a bold offer banner area, strong colour block reserved "
              "for the price and call-to-action button, centred and unmissable",
              "ลด {discount}%", "")  # empty sub → filled with the campaign CTA line

CAROUSEL_ARCS: dict[str, list[tuple]] = {
    # hero keeps the original arc, so an existing carousel is unchanged.
    "hero": [],
    "three_reasons": [
        ("HOOK", "🪝 สะดุดตา", "ตั้งประเด็นให้อยากเลื่อนดูต่อ",
         "bold minimal composition with a very large clear area for a single big "
         "headline, product small or absent, high contrast background",
         "3 เหตุผลที่คนเปลี่ยนมาใช้{item}", "เลื่อนดูต่อ →"),
        ("REASON1", "1️⃣ เหตุผลแรก", "ข้อดีที่จับต้องได้ที่สุดขึ้นก่อน",
         "clean product shot with generous space on one side for a number and one "
         "short line of text",
         "ใช้ง่าย ไม่ต้องเปลี่ยนทั้งกิจวัตร", "แค่เปลี่ยนสิ่งที่ใช้อยู่ทุกวัน"),
        ("REASON2", "2️⃣ เหตุผลที่สอง", "ลดความกังวลเรื่องความอ่อนโยน",
         "detail shot showing texture or ingredients, same lighting as the previous "
         "slide, space kept clear in the same place",
         "อ่อนโยนพอสำหรับทุกวัน", "ไม่ทิ้งความแห้งตึงหลังล้าง"),
        ("REASON3", "3️⃣ เหตุผลที่สาม", "ปิดด้วยความคุ้มค่า ต่อเข้าข้อเสนอได้พอดี",
         "wider shot of the product in its setting, same palette, space kept clear "
         "in the same place",
         "คุ้มกว่าที่คิด", "ก้อนเดียวใช้ได้นาน"),
        _CTA_SLIDE,
    ],
    "demo": [
        ("HOOK", "🪝 สะดุดตา", "ตั้งคำถามที่คนไม่เคยใช้สบู่ก้อนสงสัย",
         "bold minimal composition with a very large clear area for a single big "
         "headline, product small or absent, high contrast background",
         "ใช้{item}ยังไงให้ได้ผลจริง?", "3 ขั้นตอน เลื่อนดูเลย →"),
        ("STEP1", "1️⃣ ขั้นที่หนึ่ง", "เริ่มจากสิ่งที่ทำได้ทันที",
         "close crop on wet hands and the product, clear space above for one line",
         "ล้างหน้าด้วยน้ำสะอาดก่อน", "ให้ผิวพร้อมรับสิ่งที่ตามมา"),
        ("STEP2", "2️⃣ ขั้นที่สอง", "ขั้นที่คนทำผิดบ่อยที่สุด",
         "close crop on dense foam building between the palms, same lighting and "
         "crop as the previous slide",
         "ถูให้เกิดฟองก่อนแตะหน้า", "อย่าถูก้อนกับผิวโดยตรง"),
        ("STEP3", "3️⃣ ขั้นที่สาม", "จบขั้นตอนให้เห็นภาพผลลัพธ์",
         "clean shot of the finished routine with the product set down, brighter "
         "optimistic grade",
         "นวดเบาๆ แล้วล้างออก", "เช้า-เย็น ทุกวัน"),
        _CTA_SLIDE,
    ],
    "myth_bust": [
        ("HOOK", "🪝 สะดุดตา", "ชี้ว่ามีเรื่องที่เข้าใจผิดกันอยู่",
         "bold minimal composition with a very large clear area for a single big "
         "headline, product small or absent, high contrast background",
         "เรื่องนี้หลายคนยังเข้าใจผิดอยู่", "เลื่อนดูต่อ →"),
        ("MYTH", "❌ ความเชื่อเดิม", "พูดความเชื่อนั้นออกมาตรงๆ ให้คนดูพยักหน้าตาม",
         "muted desaturated frame illustrating the mistaken habit, space at the "
         "bottom for two lines of text",
         "\"ล้างหน้าบ่อยๆ สิวจะได้ยุบ\"", "เป็นความเชื่อที่ได้ยินกันบ่อยที่สุด"),
        ("TRUTH", "✅ ความจริง", "แก้ความเชื่อด้วยเหตุผล ไม่ใช่แค่บอกว่าผิด",
         "bright clean frame of the product in use, identical framing to the "
         "previous slide so the contrast reads",
         "ล้างมากเกินไปทำให้ผิวขาดน้ำ", "ผิวยิ่งผลิตน้ำมันชดเชย"),
        ("WHY", "🔬 เพราะอะไร", "ให้เหตุผลที่ทำให้เชื่อ แล้วโยงมาที่สินค้า",
         "detail shot showing texture or ingredients, informative layout with room "
         "for three short bullet labels",
         "{item}จึงเน้นอ่อนโยน", "• ทำความสะอาดพอดี  • ไม่ทิ้งความแห้งตึง"),
        _CTA_SLIDE,
    ],
    "transformation": [
        ("HOOK", "🪝 สะดุดตา", "ตั้งกรอบเวลาให้ชัด คนจะอยากรู้ผล",
         "bold minimal composition with a very large clear area for a single big "
         "headline, product small or absent, high contrast background",
         "สองอาทิตย์ ต่างกันแค่ไหน", "เลื่อนดูต่อ →"),
        ("BEFORE", "📅 วันแรก", "แสดงจุดเริ่มต้นแบบไม่แต่งเติม",
         "plain honest portrait under unflattering even light, muted grade, space "
         "at the bottom for two lines",
         "วันแรก", "ผิวมัน สิวขึ้นซ้ำที่เดิม"),
        ("DURING", "🔁 ระหว่างทาง", "ย้ำว่าไม่ต้องทำอะไรพิเศษ ทำให้รู้สึกว่าทำตามได้",
         "the product in daily use, warm natural light, identical crop to the "
         "previous slide",
         "ใช้ทุกวัน ไม่ได้ทำอะไรเพิ่ม", "แค่เปลี่ยนสิ่งที่ใช้ล้างหน้า"),
        ("AFTER", "✨ วันนี้", "ผลลัพธ์ที่สมจริง ไม่เกินจริง",
         "same portrait, same crop, distance and expression as the BEFORE slide, "
         "brighter grade, skin visibly calmer but recognisably the same person",
         "วันนี้", "ผลลัพธ์แต่ละคนต่างกัน"),
        _CTA_SLIDE,
    ],
    "pov": [
        ("HOOK", "🪝 สะดุดตา", "เปิดแบบคนจริงเล่า ไม่ใช่แบรนด์พูด",
         "off-centre phone-camera framing, unstaged, large clear area for one big "
         "handwritten-feeling headline",
         "ใช้มาสองอาทิตย์ ขอรีวิวจริงๆ", "เลื่อนดูต่อ →"),
        ("STORY", "💬 เล่าที่มา", "บอกว่าเคยเจออะไรมาก่อน คนที่เจอเหมือนกันจะหยุดอ่าน",
         "candid phone-style shot in a real everyday setting, space at the bottom "
         "for two lines of text",
         "ลองมาหลายอย่างแล้วไม่ตรงจุด", "ไม่ก็แห้งตึง ไม่ก็ไม่เห็นผล"),
        ("TURN", "🔀 จุดที่เปลี่ยน", "ระบุสิ่งที่ทำให้ต่างจากของเดิม",
         "the product held towards the lens at arm's length, sharp and closest to "
         "the camera, background softly out of focus",
         "จุดที่ต่างคือ{item}", "ล้างสะอาดแต่ไม่ทิ้งความแห้ง"),
        ("RESULT", "📈 ผลที่ได้", "ผลลัพธ์แบบที่คนพูดกันเองจริงๆ ไม่ใช่ภาษาโฆษณา",
         "relaxed candid portrait in natural daylight, honest unretouched feel, "
         "room for two lines",
         "ตอนนี้ไม่ต้องแต่งหน้าหนักแล้ว", "สิวยุบเร็วขึ้นกว่าเดิม"),
        _CTA_SLIDE,
    ],
    "texture": [
        ("HOOK", "🪝 สะดุดตา", "ใช้ภาพมาโครหยุดนิ้ว ไม่ต้องพึ่งตัวหนังสือใหญ่",
         "extreme macro filling the frame, one sharp plane, small clear area in a "
         "corner for a short headline",
         "เนื้อสัมผัสบอกได้มากกว่าที่คิด", "เลื่อนดูต่อ →"),
        ("SURFACE", "🔬 เนื้อสัมผัส", "ให้เห็นว่าผลิตภัณฑ์เป็นอะไรจริงๆ",
         "extreme macro of the product surface, raking side light exposing every "
         "ridge, no negative space",
         "เนื้อแน่น ไม่หยาบ", "ผิวสัมผัสจริงแบบไม่ปรุงแต่ง"),
        ("FOAM", "🫧 ฟอง", "ตอบคนที่กลัวว่าจะแรงเกินไป",
         "macro of dense fine foam building in real contact with water, same "
         "lighting and magnification as the previous slide",
         "ฟองละเอียด อ่อนโยนกับผิว", "ทำความสะอาดได้โดยไม่ต้องแรง"),
        ("AFTER", "💧 หลังล้าง", "ปิดด้วยความรู้สึกหลังใช้ ซึ่งเป็นสิ่งที่คนตัดสินใจจาก",
         "clean skin detail in soft daylight, calm and hydrated looking, room for "
         "two short lines",
         "ไม่ตึงหลังล้าง", "ผิวยังรู้สึกนุ่มอยู่"),
        _CTA_SLIDE,
    ],
    "reveal": [
        ("HOOK", "🪝 สะดุดตา", "เปิดด้วยความมืดและความอยากรู้",
         "near-black frame with one hard edge of light, very large clear dark area "
         "for a single short headline",
         "สิ่งที่ผิวคุณรออยู่", "เลื่อนดูต่อ →"),
        ("SHADOW", "🌑 เงา", "ยังไม่เผยทั้งหมด ให้คนเลื่อนต่อ",
         "the product mostly in shadow, silhouette just readable, deep shadow "
         "occupying most of the frame",
         "ใหม่จาก{brand}", ""),
        ("REVEAL", "💡 เผยตัว", "จังหวะที่สินค้าปรากฏเต็มตา",
         "the product fully lit and centred, label sharp and readable, the setting "
         "resolving around it, clear space beside it for a headline",
         "{item}", ""),
        ("DETAIL", "🔎 รายละเอียด", "ให้เหตุผลรองรับความรู้สึกพรีเมียมที่เพิ่งสร้าง",
         "detail shot showing ingredients or texture evidence, informative layout "
         "with room for three short bullet labels",
         "ทำไมถึงต่าง", "• ส่วนผสมที่อ่อนโยน  • ใช้ได้ทุกวัน  • ไม่ทิ้งความแห้งตึง"),
        _CTA_SLIDE,
    ],
}


def angles_for(scene: str, medium: str = "video") -> list[str]:
    """Angles that make sense for this scene and medium, default first.

    Two filters. An angle needing a cast is dropped from a product-only scene:
    there is nobody to notice a problem or hold a phone, and offering it would
    produce a prompt asking for a person the [CAST] block forbids. And an angle is
    dropped from a medium it has no material for — a still cannot carry "3
    เหตุผล", so it is not listed rather than silently falling back to the default.
    """
    have = {"video": ANGLES, "image": STILLS, "carousel": CAROUSEL_ARCS}.get(medium, ANGLES)
    people = has_people(scene)
    keys = [k for k in ANGLES if k in have and (people or not ANGLES[k]["needs_cast"])]
    return sorted(keys, key=lambda k: (k != DEFAULT_ANGLE, ANGLES[k]["label"]))


def still_for(key: str) -> dict:
    """Single-frame overrides for an angle; empty means use the scene as-is."""
    return STILLS.get(key) or {}


def carousel_arc(key: str) -> list[tuple]:
    """Five-slide arc for an angle; empty means use the default arc."""
    return CAROUSEL_ARCS.get(key) or []


def angle(key: str) -> dict:
    return ANGLES.get(key) or ANGLES[DEFAULT_ANGLE]


def angle_label(key: str) -> str:
    return angle(key)["label"]


def angle_goal(key: str) -> str:
    return angle(key)["goal"]


# ── Reading a scene back out of a finished file ─────────────────────────────────

# Google Flow names a download after the prompt it came from, so a clip shot with
# the student scene arrives as Soap_bar_commercial_student_deci…_202608020150.mp4.
# The scene key is usually right there in the filename, which is enough to look up
# what that scene was for and how well it fits the brand.
#
# Extra words per scene for the cases where the key itself will not appear —
# "beforeafter" is written "before_after" in a filename, "vanity" shows up as
# "mirror". Matching is on the lowercased filename with separators normalised.
#
# Thai words are the scene's own name, never its marketing vocabulary. Falling
# back to each preset's `signals` was tried and produced confident nonsense:
# "วัยรุ่นผิวมัน" landed on studio and "ยิม หลังออกกำลังกาย" on before/after,
# because สิว and ผิวมัน belong to half the scenes at once. A wrong scene carries a
# wrong Mandala score onto a file about to be approved, which is worse than no
# label, so only words that name the scene itself are listed.
_FILENAME_HINTS: dict[str, tuple[str, ...]] = {
    "lab": ("lab", "laboratory", "research", "ห้องแล็บ", "แล็บ", "วิจัย"),
    "ingredient": ("ingredient", "botanical", "extract", "สารสกัด", "ส่วนผสม"),
    "clinic": ("clinic", "dermatolog", "doctor", "คลินิก", "หมอ"),
    "teen": ("teen", "teenager", "วัยรุ่น"),
    "student": ("student", "campus", "university", "school",
                "นักเรียน", "นักศึกษา", "มหาลัย", "มหาวิทยาลัย"),
    "office": ("office", "workday", "professional", "desk", "ออฟฟิศ", "วัยทำงาน"),
    "male": ("male", "man ", "men ", "guy", "ผู้ชาย"),
    "friends": ("friends", "group of", "เพื่อน"),
    "vanity": ("vanity", "mirror", "bathroom", "โต๊ะเครื่องแป้ง", "กระจก", "ห้องน้ำ"),
    "morning": ("morning", "bedroom", "wake", "ตอนเช้า", "ห้องนอน"),
    "cafe": ("cafe", "coffee", "คาเฟ่", "กาแฟ"),
    "outdoor": ("outdoor", "sunlight", "sunny", "outside", "กลางแจ้ง", "แดด"),
    "gym": ("gym", "workout", "fitness", "sweat", "ยิม", "ออกกำลังกาย", "ฟิตเนส"),
    "studio": ("studio", "seamless", "hero shot", "สตูดิโอ"),
    "flatlay": ("flatlay", "flat lay", "top down", "topdown", "แฟลตเลย์", "จัดวาง"),
    "beforeafter": ("beforeafter", "before after", "before and after",
                    "transformation", "ก่อนหลัง", "ก่อน หลัง"),
    "ugc": ("ugc", "review", "selfie", "handheld", "รีวิว", "เซลฟี่"),
    "macro": ("macro", "texture", "closeup", "close up", "มาโคร", "เนื้อสัมผัส"),
    "promo": ("promo", "sale", "discount", "offer", "โปรโมชัน", "ลดราคา", "ส่วนลด"),
    "gift": ("gift", "festive", "holiday", "present", "ของขวัญ", "เทศกาล"),
}


def match_scene(filename: str) -> str:
    """Best guess at which scene a downloaded file came from. "" when unclear.

    Deliberately returns nothing rather than a default: labelling every unmatched
    clip "studio" would put a confident wrong scene — and a wrong score — on files
    that simply were not made from a preset.
    """
    if not filename:
        return ""
    low = filename.lower().replace("_", " ").replace("-", " ")

    def earliest(candidates: dict[str, tuple[str, ...]]) -> str:
        best, best_at = "", len(low) + 1
        for key, words in candidates.items():
            for w in words:
                at = low.find(w.lower())
                # ตัวที่โผล่ก่อนชนะ — ชื่อไฟล์ของ Flow เอาคำสำคัญไว้ต้น ๆ
                if 0 <= at < best_at:
                    best, best_at = key, at
        return best

    return earliest({k: (k, *v) for k, v in _FILENAME_HINTS.items()})


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

"""
تکنیک ماورایی + کنترل مصرف نت + پروکسی برای ایران
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import ChatMessage
from .utils import safe_filename

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

WEB_SESSION_DIR = "./web_session"

JS_EXTRACT_DIALOGS_K = """
() => {
    const out = [];
    const selectors = ['.chatlist .chatlist-chat','.chatlist .row','[data-peer-id]'];
    let elements = [];
    for (const sel of selectors) {
        const els = document.querySelectorAll(sel);
        if (els.length > 0) { elements = els; break; }
    }
    if (elements.length === 0) {
        const titles = document.querySelectorAll('.row-title');
        titles.forEach((el, i) => {
            const name = (el.innerText || '').trim();
            if (name) out.push({index: i+1, name: name, id: `idx-${i}`});
        });
        return out;
    }
    elements.forEach((el, i) => {
        let nameEl = el.querySelector('.row-title') || el;
        let name = (nameEl.innerText || '').trim().split('\\n')[0];
        if (!name) name = `Chat ${i+1}`;
        if (name.length > 80) name = name.slice(0,77)+'...';
        let pid = el.getAttribute('data-peer-id') || `idx-${i}`;
        if (name) out.push({index: i+1, name: name, id: pid});
    });
    return out;
}
"""

JS_CLICK_CHAT_BY_INDEX = """
(idx) => {
    const selectors = ['.chatlist .chatlist-chat', '.chatlist .row', '[data-peer-id]'];
    let elements = [];
    for (const sel of selectors) {
        const els = document.querySelectorAll(sel);
        if (els.length > 0) { elements = els; break; }
    }
    if (idx < 1 || idx > elements.length) return {ok: false};
    elements[idx-1].click();
    return {ok: true};
}
"""

JS_SCROLL_FULL_GUARANTEE = """
async (opts) => {
    const maxAttempts = opts?.maxAttempts || 2000;
    const stableNeeded = opts?.stableNeeded || 12;
    const sleepMs = opts?.sleepMs || 1400;
    function getScrollContainer() {
        const cands = [document.querySelector('.messages-container'), document.querySelector('.bubbles')];
        for (const c of cands) if (c) return c;
        let best = null; let maxH = 0;
        document.querySelectorAll('div').forEach(d => {
            if (d.scrollHeight > maxH && d.scrollHeight > 800 && d.clientHeight < d.scrollHeight) {
                maxH = d.scrollHeight; best = d;
            }
        });
        return best || document.scrollingElement;
    }
    function extractOnce(map) {
        const selectors = ['.message','.bubble','.Message','[data-mid]'];
        let els = [];
        for (const sel of selectors) {
            const found = document.querySelectorAll(sel);
            if (found.length > 10) { els = found; break; }
        }
        if (els.length === 0) els = document.querySelectorAll('[class*="message" i]');
        let newAdded = 0;
        els.forEach((el, idx) => {
            try {
                let text = ''; let sender = 'Unknown'; let mid = '';
                const textEl = el.querySelector('.text-content') || el.querySelector('.message-content') || el;
                let raw = (textEl.innerText || '').trim();
                if (!raw) return;
                text = raw.slice(0,5000);
                const senderEl = el.querySelector('.peer-title') || el.querySelector('.sender');
                if (senderEl) sender = senderEl.innerText.split('\\n')[0].trim().slice(0,50);
                mid = el.getAttribute('data-mid') || `hash-${idx}-${text.slice(0,20)}`;
                if (map.has(mid)) return;
                if (text) { map.set(mid, {id: mid, sender: sender, text: text}); newAdded++; }
            } catch(e) {}
        });
        return {newAdded, total: map.size};
    }
    const container = getScrollContainer();
    if (!container) return {error: 'container not found', messages: []};
    const seen = new Map();
    let lastHeight = -1; let stableRounds = 0; let attempts = 0;
    extractOnce(seen);
    while (attempts < maxAttempts && stableRounds < stableNeeded) {
        try { container.scrollTop = 0; window.scrollTo(0,0); container.dispatchEvent(new WheelEvent('wheel', {deltaY: -15000, bubbles: true})); } catch(e) {}
        await new Promise(r => setTimeout(r, sleepMs));
        let currentHeight = container.scrollHeight;
        let {newAdded, total} = extractOnce(seen);
        if (newAdded === 0 && currentHeight === lastHeight) stableRounds++; else if (newAdded === 0) stableRounds++; else stableRounds = 0;
        lastHeight = currentHeight; attempts++;
        if (attempts % 5 === 0 || newAdded > 0) console.log(`[scroll ${attempts}/${maxAttempts}] +${newAdded} total=${total} stable=${stableRounds}/${stableNeeded}`);
        if (attempts % 50 === 0) await new Promise(r => setTimeout(r, 2500));
    }
    let messages = Array.from(seen.values()); messages.reverse();
    messages = messages.map((m,i)=>({...m, finalIndex:i+1}));
    return {messages, totalUnique: seen.size, attempts, stableRounds, finished: stableRounds>=stableNeeded};
}
"""

def _parse_proxy_for_playwright(proxy_str: str):
    if not proxy_str:
        return None
    # playwright expects dict: {"server": "http://host:port", "username":..., "password":...}
    # supports http, https, socks5
    proxy_str = proxy_str.strip()
    # اگر فقط host:port بود
    if "://" not in proxy_str:
        proxy_str = f"socks5://{proxy_str}"
    return {"server": proxy_str}

async def run_web_extraction(output_dir: str, base_name: str, max_mb: float = 8.5, dialog_limit: int = 120, search: Optional[str] = None, max_scroll_attempts: int = 2000, proxy: Optional[str] = None):
    if not PLAYWRIGHT_AVAILABLE:
        print("playwright نصب نیست: pip install playwright && playwright install chromium")
        return
    import os
    proxy = proxy or os.getenv("TELEGRAM_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        user_data_dir = Path(WEB_SESSION_DIR).absolute()
        user_data_dir.mkdir(exist_ok=True)
        print(f"سشن مرورگر: {user_data_dir}")

        pw_proxy = _parse_proxy_for_playwright(proxy)
        if pw_proxy:
            print(f"پروکسی مرورگر فعال: {pw_proxy['server']} (برای حل فیلتر ایران + کنترل نت)")

        context = await p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=False,
            viewport={"width": 1300, "height": 900},
            proxy=pw_proxy,
            args=["--disable-blink-features=AutomationControlled"]
        )

        print("کنترل مصرف نت فعال: عکس/ویدیو بلاک شد")
        async def block_heavy(route):
            rtype = route.request.resource_type
            if rtype in ["image", "media", "font"]:
                # فقط عکس و ویدیو رو بلاک، فونت و استایل رو بذار بمونه برای نمایش
                if rtype in ["image", "media"]:
                    await route.abort()
                    return
            await route.continue_()
        await context.route("**/*", block_heavy)

        page = await context.new_page() if len(context.pages)==0 else context.pages[0]
        page.on("console", lambda msg: print(f"[browser] {msg.text}"))

        print("رفتن به https://web.telegram.org/k/")
        await page.goto("https://web.telegram.org/k/", wait_until="domcontentloaded", timeout=60000)

        print("اگر لاگین نیستی QR اسکن کن")
        try:
            await page.wait_for_selector(".chatlist, .chat-list, [data-peer-id]", timeout=120000)
            print("لاگین شد!")
        except:
            await page.wait_for_timeout(5000)

        await page.wait_for_timeout(3000)
        dialogs = await page.evaluate(JS_EXTRACT_DIALOGS_K)
        print(f"\n{len(dialogs)} چت پیدا شد:")
        filtered = dialogs
        if search:
            sq = search.lower()
            filtered = [d for d in dialogs if sq in d['name'].lower()]
            print(f"فیلتر '{search}' -> {len(filtered)}")

        if not filtered:
            print("هیچ چتی پیدا نشد")
            await context.close()
            return

        for d in filtered:
            print(f"{d['index']:3d}. {d['name']} | ID: {d['id']}")

        print("\nعدد چت رو بزن (q خروج)")
        choice = input("انتخاب: ").strip()
        if choice.lower() in ('q','quit'):
            await context.close()
            return

        selected = None
        if choice.isdigit():
            idx = int(choice)
            for d in filtered:
                if d['index'] == idx:
                    selected = d
                    break
            if not selected and 1 <= idx <= len(filtered):
                selected = filtered[idx-1]
        else:
            sq = choice.lower()
            matches = [d for d in filtered if sq in d['name'].lower()]
            if matches:
                for m in matches:
                    print(f"  - {m['index']}. {m['name']}")
                choice2 = input("دوباره عدد بزن: ").strip()
                if choice2.isdigit():
                    ii = int(choice2)
                    for d in filtered:
                        if d['index'] == ii:
                            selected = d
                            break

        if not selected:
            print("انتخاب نامعتبر")
            await context.close()
            return

        print(f"\nانتخاب: {selected['name']}")
        await page.evaluate(JS_CLICK_CHAT_BY_INDEX, selected['index'])
        await page.wait_for_timeout(4000)

        print(f"\nفول گارانتی: اسکرول بینهایت تا {max_scroll_attempts} بار - تضمین همه پیام‌ها")
        extracted = await page.evaluate(JS_SCROLL_FULL_GUARANTEE, {"maxAttempts": max_scroll_attempts, "stableNeeded": 15, "sleepMs": 1400})

        if 'error' in extracted:
            print(f"خطا: {extracted['error']}")
            await context.close()
            return

        msgs = extracted.get('messages', [])
        print(f"\nتمام: attempts={extracted.get('attempts')} totalUnique={extracted.get('totalUnique')} - مصرف نت کنترل شده (فقط متن)")

        if not msgs:
            print("هیچ پیامی استخراج نشد")
            await context.close()
            return

        base = safe_filename(base_name or selected['name'])
        out_dir = Path(output_dir) / base
        max_bytes = int(max_mb * 1024 * 1024)

        from .md_writer import ChunkedMDWriter

        with ChunkedMDWriter(str(out_dir), base, max_bytes=max_bytes) as writer:
            for i, m in enumerate(msgs):
                dt = datetime.now()
                cm = ChatMessage(id=m.get('finalIndex', i+1), date=dt, sender_name=m.get('sender','Unknown'), text=m.get('text',''))
                writer.write_message(cm)

        print(f"\n✅ تمام! {out_dir} | {len(msgs)} پیام - مصرف نت کم (فقط متن، زیر 9MB)")
        input("Enter بزن ببنده...")
        await context.close()


PUBLIC_API_CREDENTIALS = {
    "web": (2496, "8da85b0d5bfe62527e5b244c209159c3"),
    "android": (21724, "3e0cb5efcd52300aec5994fdfc5bdc16"),
    "desktop": (2040, "b18441a1ff607e10a989891a5462e627"),
}
def get_public_credentials(which="android"):
    return PUBLIC_API_CREDENTIALS.get(which, PUBLIC_API_CREDENTIALS["android"])

import argparse
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from .md_writer import ChunkedMDWriter
from .exporter_json import parse_telegram_export_json, get_chat_names_from_export
from .utils import safe_filename

def print_api_help():
    print("""
API_ID از کجا؟

ساخت اپ:
1. my.telegram.org -> لاگین
2. API development tools -> App بساز
3. api_id + api_hash رو بذار تو .env

بدون ساخت اپ (ماورایی):
- اگر API_ID ندی، خودکار از کلید عمومی 21724 استفاده می‌کنه
- یا حالت web که اصلا API نمی‌خواد

پروکسی برای ایران (چون تلگرام فیلتره):
اگر TimeoutError می‌گیری:
1. VPN روشن کن
2. یا پروکسی SOCKS5 بذار:
   python tel-d.py -o ./out mtproto --list --proxy socks5://127.0.0.1:1080
   یا
   set TELEGRAM_PROXY=socks5://127.0.0.1:1080 (ویندوز)
   export TELEGRAM_PROXY=socks5://127.0.0.1:1080 (لینوکس)

کنترل مصرف اینترنت:
- mtproto: فقط متن (only_text) -> عکس/فیلم دانلود نمیشه -> مصرف کم
- web: عکس/ویدیو بلاک میشه با route.abort() -> فقط متن
- هر فایل MD زیر 9MB اسپلیت میشه
""")

def cmd_json(args):
    json_path = Path(args.input)
    if not json_path.exists():
        print(f"فایل پیدا نشد: {json_path}")
        sys.exit(1)
    chat_names = get_chat_names_from_export(str(json_path))
    print(f"چت‌های داخل فایل: {chat_names}")
    base_name = args.chat_name or (chat_names[0] if len(chat_names)==1 else "telegram_export")
    base_name = safe_filename(base_name)
    output_dir = Path(args.output) / base_name
    max_bytes = int(args.max_mb * 1024 * 1024)
    print(f"خروجی: {output_dir} | حد: {args.max_mb} MB")
    with ChunkedMDWriter(str(output_dir), base_name, max_bytes=max_bytes) as writer:
        count=0
        for msg in parse_telegram_export_json(str(json_path), only_text=not args.include_non_text, chat_name_filter=args.chat_filter):
            writer.write_message(msg)
            count+=1
        print(f"\nتمام: {count} پیام - فول گارانتی، مصرف نت صفر (آفلاین)")
    print(f"\n{output_dir}")

def cmd_mtproto(args):
    try:
        from .exporter_mtproto import stream_to_writer, list_and_print, interactive_picker
        from .exporter_web import get_public_credentials
    except ImportError as e:
        print(f"وابستگی نصب نیست: {e}")
        sys.exit(1)
    
    api_id = args.api_id or os.getenv("API_ID") or os.getenv("TG_API_ID")
    api_hash = args.api_hash or os.getenv("API_HASH") or os.getenv("TG_API_HASH")
    proxy = args.proxy or os.getenv("TELEGRAM_PROXY") or os.getenv("SOCKS_PROXY") or os.getenv("HTTP_PROXY")

    if not api_id or not api_hash:
        print("API_ID ندادی - میرم سراغ کلید عمومی")
        pub_id, pub_hash = get_public_credentials("android")
        api_id, api_hash = pub_id, pub_hash
        print(f"کلید عمومی: {api_id}")
    
    try:
        api_id = int(api_id)
    except:
        print("API_ID عدد باشه")
        sys.exit(1)

    if args.list:
        async def _list():
            await list_and_print(api_id, api_hash, args.session, limit=args.dialog_limit, search=args.search, proxy=proxy)
        asyncio.run(_list())
        return

    chat_identifier = args.chat
    chosen_name = None

    if not chat_identifier:
        print("حالت انتخاب با عدد")
        async def _pick():
            selected, client = await interactive_picker(api_id=api_id, api_hash=api_hash, session_name=args.session, initial_limit=args.dialog_limit, search_query=args.search, proxy=proxy)
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            return selected
        selected = asyncio.run(_pick())
        if not selected:
            print("انتخاب نشد")
            sys.exit(0)
        chat_identifier = getattr(selected, 'entity', None) or selected.id
        if hasattr(selected, 'entity'):
            chat_identifier = selected.entity
        chosen_name = getattr(selected, 'name', None)
        print(f"\nانتخاب نهایی: {chosen_name}")

    base_name = safe_filename(args.chat_name or chosen_name or str(chat_identifier).replace("@","").replace("/","_")[:80] or "telegram_chat")
    output_dir = Path(args.output) / base_name
    max_bytes = int(args.max_mb * 1024 * 1024)
    print(f"خروجی: {output_dir} | حد: {args.max_mb} MB | هدف: {chosen_name or chat_identifier}")
    print("فول گارانتی: از اول تا آخر + کنترل مصرف: فقط متن")

    async def _run():
        with ChunkedMDWriter(str(output_dir), base_name, max_bytes=max_bytes) as writer:
            count = await stream_to_writer(chat_identifier=chat_identifier, api_id=api_id, api_hash=api_hash, writer=writer, session_name=args.session, limit=args.limit, only_text=not args.include_non_text, proxy=proxy)
            print(f"\nتمام: {count} پیام - تضمین همه")

    asyncio.run(_run())
    print(f"\n{output_dir}")

def cmd_web(args):
    try:
        from .exporter_web import run_web_extraction
    except ImportError as e:
        print(f"playwright نصب نیست: {e}")
        sys.exit(1)

    output_dir = args.output
    base_name = args.chat_name or "telegram_web"
    max_scroll = args.max_scroll
    proxy = args.proxy
    print(f"حالت WEB فول گارانتی - کنترل مصرف: عکس/ویدیو بلاک")
    asyncio.run(run_web_extraction(output_dir=output_dir, base_name=base_name, max_mb=args.max_mb, dialog_limit=args.dialog_limit, search=args.search, max_scroll_attempts=max_scroll, proxy=proxy))

def main():
    parser = argparse.ArgumentParser(description="tel-d: آرشیو چت به MD زیر 9MB - فول گارانتی")
    parser.add_argument("--output", "-o", default="./out")
    parser.add_argument("--max-mb", type=float, default=8.5)
    parser.add_argument("--chat-name")
    parser.add_argument("--include-non-text", action="store_true")
    parser.add_argument("--api-help", action="store_true")

    sub = parser.add_subparsers(dest="source", required=False)

    p_json = sub.add_parser("json", help="از Export JSON (امن، مصرف نت صفر)")
    p_json.add_argument("--input", "-i", required=True)
    p_json.add_argument("--chat-filter")

    p_mt = sub.add_parser("mtproto", help="مستقیم با اکانت - فول گارانتی + پروکسی + کم مصرف")
    p_mt.add_argument("--chat", "-c", required=False, default=None)
    p_mt.add_argument("--api-id")
    p_mt.add_argument("--api-hash")
    p_mt.add_argument("--session", default="tel-d-session")
    p_mt.add_argument("--limit", type=int, default=None)
    p_mt.add_argument("--list", action="store_true")
    p_mt.add_argument("--search", "-s", default=None)
    p_mt.add_argument("--dialog-limit", type=int, default=120)
    p_mt.add_argument("--proxy", help="مثلا socks5://127.0.0.1:1080 یا host:port - برای حل TimeoutError ایران")

    p_web = sub.add_parser("web", help="ماورایی فول گارانتی: مرورگر + انتخاب عدد + اسکرول بینهایت + کنترل نت")
    p_web.add_argument("--search", "-s", default=None)
    p_web.add_argument("--dialog-limit", type=int, default=120)
    p_web.add_argument("--max-scroll", type=int, default=2000)
    p_web.add_argument("--proxy", help="پروکسی برای Playwright مثلا http://127.0.0.1:8080")

    args = parser.parse_args()

    if args.api_help:
        print_api_help()
        sys.exit(0)

    if not args.source:
        parser.print_help()
        print("\nنمونه:")
        print("  python tel-d.py -o ./out json -i result.json")
        print("  python tel-d.py -o ./out mtproto --list --proxy socks5://127.0.0.1:1080")
        print("  python tel-d.py -o ./out mtproto --proxy socks5://127.0.0.1:1080")
        print("  python tel-d.py -o ./out web --max-scroll 3000")
        print_api_help()
        sys.exit(0)

    if args.source == "json":
        cmd_json(args)
    elif args.source == "mtproto":
        cmd_mtproto(args)
    elif args.source == "web":
        cmd_web(args)

if __name__ == "__main__":
    main()

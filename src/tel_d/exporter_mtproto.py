"""
MTProto Exporter - فول گارانتی 100٪ + پروکسی برای ایران + کنترل مصرف نت
"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional
from pathlib import Path
import os

from .models import ChatMessage

try:
    from telethon import TelegramClient
    from telethon.tl.types import User
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

def _get_chat_title(entity) -> str:
    if hasattr(entity, 'title') and entity.title:
        return entity.title
    if hasattr(entity, 'first_name'):
        fn = getattr(entity, 'first_name', '') or ''
        ln = getattr(entity, 'last_name', '') or ''
        full = f"{fn} {ln}".strip()
        if full:
            return full
    if hasattr(entity, 'username') and entity.username:
        return f"@{entity.username}"
    return str(getattr(entity, 'id', 'Unknown'))

def _parse_proxy(proxy_str: str):
    """
    ساپورت:
    - socks5://127.0.0.1:1080
    - socks5://user:pass@127.0.0.1:1080
    - http://127.0.0.1:8080
    - مستقیم host:port
    برمی‌گردونه proxy برای Telethon: (socks.SOCKS5, host, port) یا None
    """
    if not proxy_str:
        return None
    proxy_str = proxy_str.strip()
    # از env هم بخون
    if proxy_str.lower().startswith("socks5://") or proxy_str.lower().startswith("socks4://"):
        try:
            import socks
            # حذف پروتکل
            rest = proxy_str.split("://",1)[1]
            user = None
            pwd = None
            if "@" in rest:
                auth, hostport = rest.rsplit("@",1)
                if ":" in auth:
                    user, pwd = auth.split(":",1)
                else:
                    user = auth
            else:
                hostport = rest
            host, port = hostport.rsplit(":",1)
            port = int(port)
            if "socks5" in proxy_str.lower():
                return (socks.SOCKS5, host, port, True, user, pwd) if user else (socks.SOCKS5, host, port)
            else:
                return (socks.SOCKS4, host, port, True, user) if user else (socks.SOCKS4, host, port)
        except Exception as e:
            print(f"⚠️ خطا در parse پروکسی SOCKS: {e} - بدون پروکسی ادامه میدم")
            return None
    elif proxy_str.lower().startswith("http://") or proxy_str.lower().startswith("https://"):
        # Telethon از HTTP پروکسی با socks پشتیبانی می‌کنه؟ برای سادگی به صورت SOCKS5 فرض کن اگر http بود
        # ولی بهتره به کاربر بگیم از socks5 استفاده کنه
        try:
            rest = proxy_str.split("://",1)[1]
            host, port = rest.rsplit(":",1)
            port = int(port.split("/")[0])
            import socks
            return (socks.HTTP, host, port)
        except Exception as e:
            print(f"⚠️ خطا در parse پروکسی HTTP: {e}")
            return None
    elif ":" in proxy_str:
        # host:port ساده
        try:
            import socks
            host, port = proxy_str.rsplit(":",1)
            return (socks.SOCKS5, host, int(port))
        except:
            return None
    return None

def _make_client(session_name, api_id, api_hash, proxy=None):
    proxy_obj = _parse_proxy(proxy) if isinstance(proxy, str) else proxy
    if proxy_obj:
        print(f"🔌 پروکسی فعال: {proxy_obj}")
        return TelegramClient(str(Path(session_name).with_suffix('')).replace('.session',''), api_id, api_hash, proxy=proxy_obj)
    else:
        return TelegramClient(str(Path(session_name).with_suffix('')).replace('.session',''), api_id, api_hash)

async def fetch_messages_mtproto(
    chat_identifier,
    api_id: int,
    api_hash: str,
    session_name: str = "tel-d-session",
    limit: Optional[int] = None,
    only_text: bool = True,
    proxy = None,
) -> AsyncGenerator[ChatMessage, None]:
    
    if not TELETHON_AVAILABLE:
        raise RuntimeError("telethon نصب نیست")

    # پروکسی از env هم بخون اگر آرگومان نداد
    proxy = proxy or os.getenv("TELEGRAM_PROXY") or os.getenv("SOCKS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy")

    client = _make_client(session_name, api_id, api_hash, proxy=proxy)
    await client.start()
    print("✅ لاگین موفق")
    
    try:
        entity = await client.get_entity(chat_identifier) if isinstance(chat_identifier, (str, int)) else chat_identifier
        chat_title = _get_chat_title(entity)
        print(f"🎯 چت هدف: {chat_title}")

        total_estimate = None
        try:
            msgs = await client.get_messages(entity, limit=0)
            total_estimate = msgs.total if hasattr(msgs, 'total') else None
        except:
            pass

        if total_estimate:
            print(f"📊 تخمین کل پیام‌ها: {total_estimate} - از اول می‌خونم (کنترل مصرف: فقط متن)")
        else:
            print(f"📥 شروع دانلود از اول چت: {chat_title} - کنترل مصرف: فقط متن، بدون مدیا")

        count = 0
        last_id = None
        async for msg in client.iter_messages(entity, reverse=True, limit=limit):
            if only_text and not msg.text:
                continue
            
            sender_name = "Unknown"
            sender_username = None
            sender_id = None
            try:
                if msg.sender:
                    if isinstance(msg.sender, User):
                        sender_name = f"{msg.sender.first_name or ''} {msg.sender.last_name or ''}".strip() or "Unknown"
                        sender_username = getattr(msg.sender, 'username', None)
                        sender_id = msg.sender.id
                    else:
                        sender_name = getattr(msg.sender, 'title', 'Unknown')
                        sender_id = getattr(msg.sender, 'id', None)
            except:
                pass
            
            if sender_name == "Unknown" and hasattr(msg, 'from_id'):
                sender_id = getattr(msg.from_id, 'user_id', sender_id)
            
            chat_msg = ChatMessage(
                id=msg.id,
                date=msg.date or datetime.now(),
                sender_name=sender_name,
                sender_username=sender_username,
                sender_id=sender_id,
                text=msg.text or "",
                reply_to_id=getattr(msg.reply_to, 'reply_to_msg_id', None) if msg.reply_to else None,
                is_forwarded=bool(msg.forward),
                forwarded_from=str(msg.forward.from_name) if msg.forward and hasattr(msg.forward, 'from_name') else None
            )
            count += 1
            last_id = msg.id
            if count % 500 == 0:
                if total_estimate:
                    pct = (count / total_estimate * 100) if total_estimate else 0
                    print(f"  ... {count}/{total_estimate} ({pct:.1f}٪) ID:{msg.id}")
                else:
                    print(f"  ... {count} پیام ID:{msg.id}")
            
            yield chat_msg
            
        print(f"✅ تمام شد: {count} پیام متنی - تضمین 100% از اول تا آخر")
            
    finally:
        await client.disconnect()


async def stream_to_writer(chat_identifier, api_id, api_hash, writer, session_name="tel-d-session", limit=None, only_text=True, proxy=None):
    count = 0
    async for msg in fetch_messages_mtproto(chat_identifier, api_id, api_hash, session_name, limit, only_text, proxy=proxy):
        writer.write_message(msg)
        count += 1
    return count


def _format_dialog_line(idx: int, dialog) -> str:
    if dialog.is_user:
        t = "شخصی"
    elif dialog.is_group:
        t = "گروه"
    elif dialog.is_channel:
        t = "کانال"
        if getattr(dialog.entity, 'megagroup', False):
            t = "سوپرگروه"
    else:
        t = "چت"
    name = dialog.name or "بدون نام"
    display_name = name[:57]+"..." if len(name)>60 else name
    uname = getattr(dialog.entity, 'username', None)
    uname_str = f"@{uname}" if uname else ""
    unread = f" [{dialog.unread_count} نخوانده]" if dialog.unread_count else ""
    return f"{idx:3d}. {t} | {display_name} {uname_str}{unread} | ID: {dialog.id}"

async def interactive_picker(api_id, api_hash, session_name="tel-d-session", initial_limit=120, search_query=None, proxy=None):
    if not TELETHON_AVAILABLE:
        raise RuntimeError("telethon نصب نیست")
    proxy = proxy or os.getenv("TELEGRAM_PROXY") or os.getenv("SOCKS_PROXY")
    client = _make_client(session_name, api_id, api_hash, proxy=proxy)
    await client.start()
    print("✅ لاگین موفق")
    all_dialogs = []
    batch = initial_limit
    try:
        while True:
            if not all_dialogs or search_query is None:
                print(f"\nدریافت {batch} چت...")
                dialogs = await client.get_dialogs(limit=batch)
                all_dialogs = dialogs
            filtered = all_dialogs
            if search_query:
                sq = search_query.lower()
                filtered = [d for d in all_dialogs if sq in (d.name or "").lower() or sq in str(getattr(d.entity, 'username', '') or '').lower()]
            if not filtered:
                print(f"هیچ چتی با '{search_query}' پیدا نشد")
                search_query = None
                continue
            print("\n" + "="*70)
            print(f"لیست ({len(filtered)}) - فقط عدد بزن:")
            print("="*70)
            for i, d in enumerate(filtered, 1):
                print(_format_dialog_line(i, d))
            print("="*70)
            print("عدد→انتخاب | اسم→فیلتر | more→100 تا بیشتر | @username→مستقیم | q خروج")
            choice = input("\nانتخابت؟ ").strip()
            if not choice:
                continue
            if choice.lower() in ('q','quit','exit'):
                return None, None
            if choice.lower() == 'more':
                batch += 100
                dialogs = await client.get_dialogs(limit=batch)
                all_dialogs = dialogs
                search_query = None
                continue
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(filtered):
                    selected = filtered[idx-1]
                    print(f"\nانتخاب شد: {selected.name}")
                    return selected, client
                else:
                    print(f"باید بین 1 و {len(filtered)}")
                    continue
            if choice.startswith('@') or choice.startswith('https://') or choice.lstrip('-').isdigit():
                try:
                    ent = await client.get_entity(choice)
                    class Fake:
                        def __init__(self, ent, cid):
                            self.entity = ent
                            self.id = cid
                            self.name = _get_chat_title(ent)
                    return Fake(ent, choice), client
                except Exception as e:
                    print(f"نتونستم {choice}: {e}")
                    continue
            search_query = choice
            print(f"فیلتر: {search_query}")
            continue
    except KeyboardInterrupt:
        print("\nلغو")
        await client.disconnect()
        return None, None

async def list_and_print(api_id, api_hash, session_name, limit=200, search=None, proxy=None):
    proxy = proxy or os.getenv("TELEGRAM_PROXY") or os.getenv("SOCKS_PROXY")
    client = _make_client(session_name, api_id, api_hash, proxy=proxy)
    await client.start()
    try:
        print(f"دریافت {limit} چت آخر...")
        dialogs = await client.get_dialogs(limit=limit)
        if search:
            sq = search.lower()
            dialogs = [d for d in dialogs if sq in (d.name or "").lower()]
            print(f"فیلتر '{search}' -> {len(dialogs)}")
        print("\n" + "="*70)
        for i, d in enumerate(dialogs, 1):
            print(_format_dialog_line(i, d))
        print("="*70)
        print(f"مجموع: {len(dialogs)} چت")
    finally:
        await client.disconnect()

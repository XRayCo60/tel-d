import json
from pathlib import Path
from datetime import datetime
from typing import Generator, List, Optional
from .models import ChatMessage
from .utils import extract_text_from_export

def parse_telegram_export_json(json_path: str, 
                               only_text: bool = True,
                               chat_name_filter: Optional[str] = None) -> Generator[ChatMessage, None, None]:
    """
    result.json خروجی Telegram Desktop رو میخونه.
    ساختارش:
    {
      "name": "...",
      "type": "...",
      "id": 123,
      "messages": [ {id, date, from, text, reply_to_message_id, forwarded_from, ...}, ... ]
    }
    یا اگر Export چند چت باشه، لیست چت ها نیست، بلکه معمولا تک فایل برای تک چت.
    
    اگر فایل result.json اصلی که شامل چند چت نیست - تک چته.
    ما سازگار با هر دو حالت میسازیم.
    """
    json_path = Path(json_path)
    print(f"📂 خواندن JSON: {json_path} ({json_path.stat().st_size / 1024 / 1024:.2f} MB)")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # حالت 1: فایل مستقیم یک چت
    if isinstance(data, dict) and "messages" in data:
        chats = [data]
    elif isinstance(data, dict) and "chats" in data:
        # بعضی اکسپورت های قدیمی
        chats = data["chats"].get("list", [])
    elif isinstance(data, list):
        chats = data
    else:
        raise ValueError("فرمت JSON ناشناخته - باید خروجی Telegram Desktop باشد")

    for chat in chats:
        chat_name = chat.get("name", "Unknown")
        if chat_name_filter and chat_name_filter not in chat_name:
            continue
        
        print(f"🔍 چت پیدا شد: {chat_name} | پیام‌ها: {len(chat.get('messages', []))}")
        messages = chat.get("messages", [])
        
        for raw in messages:
            # سرویس مسیج ها رو میخوایم رد کنیم اگر only_text باشه؟
            if raw.get("type") == "service" and only_text:
                continue
            
            text_raw = raw.get("text", "")
            text = extract_text_from_export(text_raw)
            
            # اگر فقط متنی میخوایم و text خالیه و caption هم نداره رد کن
            # بعضی پیام ها photo با caption دارن - caption هم text حساب میشه
            # در export، caption هم ممکنه توی text باشد؟ ولی چک میکنیم file و...
            if only_text and not text.strip():
                # ممکنه پول یا ... باشه، رد کن
                continue
            
            # تاریخ: مثل "2023-01-01T12:00:00"
            date_str = raw.get("date", "")
            try:
                # فرمت Telegram: 2023-01-01T00:00:00
                dt = datetime.fromisoformat(date_str)
            except:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
                except:
                    dt = datetime.now()
            
            msg = ChatMessage(
                id=raw.get("id", 0),
                date=dt,
                sender_name=raw.get("from", "Unknown"),
                sender_username=None,  # در export یوزرنیم مستقیم نیست
                sender_id=raw.get("from_id"),
                text=text,
                reply_to_id=raw.get("reply_to_message_id"),
                is_forwarded="forwarded_from" in raw,
                forwarded_from=raw.get("forwarded_from")
            )
            yield msg


def get_chat_names_from_export(json_path: str) -> List[str]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "messages" in data:
        return [data.get("name", "Unknown")]
    if "chats" in data:
        return [c.get("name", "Unknown") for c in data["chats"].get("list", [])]
    if isinstance(data, list):
        return [c.get("name", "Unknown") for c in data]
    return []

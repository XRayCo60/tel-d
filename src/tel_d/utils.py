from typing import Union, List
import re

def extract_text_from_export(text_field: Union[str, List, dict]) -> str:
    """
    تلگرام دسکتاپ result.json فیلد text رو گاهی لیست میده مثلا:
    ["سلام ", {"type":"link","text":"..."}, " چطوری"]
    اینجا صافش میکنیم و به متن ساده + لینک مارکدانی تبدیل میکنیم
    """
    if not text_field:
        return ""
    if isinstance(text_field, str):
        return text_field
    if isinstance(text_field, dict):
        return text_field.get("text", "")
    
    # list
    parts = []
    for item in text_field:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            t = item.get("text", "")
            typ = item.get("type", "")
            if typ == "link" or typ == "text_link":
                href = item.get("href", t)
                # اگر href داشت لینک مارکدان بساز
                if href and href != t:
                    parts.append(f"[{t}]({href})")
                else:
                    parts.append(t)
            elif typ in ("bold", "italic", "code", "pre"):
                # ساده نگه میداریم
                parts.append(t)
            elif typ == "mention" or typ == "mention_name":
                parts.append(t)
            else:
                parts.append(t)
    return "".join(parts)

def safe_filename(name: str) -> str:
    # حذف کاراکترهای غیرمجاز
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = name.strip()
    return name[:100] if len(name) > 100 else name

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024*1024:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/1024/1024:.2f} MB"

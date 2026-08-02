import os
from pathlib import Path
from typing import List
from .models import ChatMessage
from .utils import safe_filename, format_file_size

DEFAULT_MAX_BYTES = int(8.5 * 1024 * 1024)  # 8.5MB حاشیه امن برای زیر 9MB

class ChunkedMDWriter:
    def __init__(self, output_dir: str, base_name: str, max_bytes: int = DEFAULT_MAX_BYTES):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_name = safe_filename(base_name)
        self.max_bytes = max_bytes
        
        self.current_index = 1
        self.current_file = None
        self.current_path = None
        self.current_bytes = 0
        self.files_created: List[Path] = []
        self.total_messages = 0
        
        self._open_new_file()
    
    def _open_new_file(self):
        if self.current_file:
            self.current_file.close()
            print(f"✅ فایل بسته شد: {self.current_path} ({format_file_size(self.current_bytes)})")
        
        filename = f"{self.base_name}_{self.current_index:03d}.md"
        self.current_path = self.output_dir / filename
        self.current_file = open(self.current_path, "w", encoding="utf-8")
        self.current_bytes = 0
        self.files_created.append(self.current_path)
        
        # هدر فایل
        header = f"""# {self.base_name} - بخش {self.current_index:03d}

> این فایل بخشی از آرشیو چت `{self.base_name}` است.
> ترتیب: قدیمی به جدید (از اول به آخر)
> محدوده: این فایل شامل بخشی از پیام‌هاست.

---
        
"""
        self.current_file.write(header)
        self.current_bytes += len(header.encode('utf-8'))
        print(f"📄 فایل جدید: {self.current_path}")

    def write_message(self, msg: ChatMessage):
        block = msg.to_markdown_block()
        block_bytes = len(block.encode('utf-8'))
        
        # اگر حتی با این پیام از حد بگذره، برو فایل بعدی (مگر اینکه فایل خالی باشه)
        if self.current_bytes + block_bytes > self.max_bytes and self.current_bytes > 200:
            self.current_index += 1
            self._open_new_file()
        
        self.current_file.write(block)
        self.current_bytes += block_bytes
        self.total_messages += 1
        
        # لاگ هر 1000 پیام
        if self.total_messages % 1000 == 0:
            print(f"  ... {self.total_messages} پیام نوشته شد | فایل فعلی: {format_file_size(self.current_bytes)}")

    def write_messages(self, messages: List[ChatMessage]):
        # مرتب سازی قطعی بر اساس date و id
        messages_sorted = sorted(messages, key=lambda m: (m.date, m.id))
        for msg in messages_sorted:
            self.write_message(msg)

    def close(self):
        if self.current_file:
            footer = f"""
---
> پایان بخش {self.current_index:03d} | مجموع {self.total_messages} پیام تا اینجا
"""
            self.current_file.write(footer)
            self.current_file.close()
            print(f"✅ فایل نهایی بسته شد: {self.current_path} ({format_file_size(self.current_bytes)})")
            self.current_file = None
        
        # ساخت فایل ایندکس
        self._write_index()

    def _write_index(self):
        index_path = self.output_dir / f"{self.base_name}_INDEX.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(f"# ایندکس آرشیو: {self.base_name}\n\n")
            f.write(f"مجموع پیام‌ها: **{self.total_messages}**\n")
            f.write(f"تعداد فایل‌ها: **{len(self.files_created)}**\n")
            f.write(f"حد هر فایل: **{format_file_size(self.max_bytes)}** (برای ماندن زیر 9MB)\n\n")
            f.write("## لیست فایل‌ها (به ترتیب قدیمی -> جدید)\n\n")
            for i, p in enumerate(self.files_created, 1):
                size = p.stat().st_size if p.exists() else 0
                f.write(f"{i}. `{p.name}` - {format_file_size(size)}\n")
            f.write("\n---\n")
            f.write("نکته: فایل‌ها را به ترتیب شماره بخوانید: 001 از اول چت است و آخرین شماره انتهای چت.\n")
        print(f"📚 ایندکس ساخته شد: {index_path}")
        return index_path

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

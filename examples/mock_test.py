"""
تست سریع writer بدون نیاز به تلگرام
میسازه 30k پیام فیک فارسی برای چک کردن 9MB split
اجرا از روت پروژه: python examples/mock_test.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from datetime import datetime, timedelta
import random
from tel_d.models import ChatMessage
from tel_d.md_writer import ChunkedMDWriter

names = ["علی", "سارا", "من", "رضا", "مامان"]
texts = [
    "سلام چطوری؟ چه خبر؟ امروز چی کار کردی؟",
    "داشتم فکر میکردم بریم بیرون یه چیزی بخوریم",
    "این پروژه tel-d خیلی باحال شد، دمت گرم",
    "یادت میاد اون روز بارون میومد و ما رفتیم کافی شاپ نزدیک میدون؟ همون روز که کیکم سفارش دادیم و قهوه‌ات ریخت روی میز و همه خندیدیم؟ هنوز عکسشو دارم",
    "لورم ایپسوم متن ساختگی فارسی برای تست حجم فایل هست که باید ببینیم چقدر میشه",
    "😂 😂 😂",
    "باشه فردا ساعت 5 میبینمت. جای همیشگی.",
]

output_dir = ROOT / "out" / "mock_chat"
base = "mock_persian_chat"

print(f"🎯 خروجی: {output_dir}")
with ChunkedMDWriter(str(output_dir), base, max_bytes=int(8.5*1024*1024)) as w:
    start = datetime(2020, 1, 1, 12, 0, 0)
    for i in range(1, 30000):
        msg = ChatMessage(
            id=i,
            date=start + timedelta(minutes=i*7),
            sender_name=random.choice(names),
            sender_username="testuser" if random.random() > 0.5 else None,
            text=random.choice(texts) + f" (پیام شماره {i})",
            reply_to_id=random.choice([None, i-1]) if i>1 and random.random()>0.8 else None
        )
        w.write_message(msg)

print("✅ تست تموم شد")
print(f"📁 فایل‌ها:")
for f in sorted(output_dir.glob("*.md")):
    size_mb = f.stat().st_size / 1024 / 1024
    print(f"  - {f.name}: {size_mb:.2f} MB {'✅ زیر 9MB' if size_mb < 9 else '❌ بیشتر از 9MB!'}")

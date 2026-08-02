from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ChatMessage:
    id: int
    date: datetime
    sender_name: str
    sender_username: Optional[str] = None
    sender_id: Optional[int] = None
    text: str = ""
    reply_to_id: Optional[int] = None
    is_forwarded: bool = False
    forwarded_from: Optional[str] = None
    
    def to_markdown_block(self) -> str:
        """تبدیل به بلوک ساختار یافته مارکدان"""
        date_str = self.date.strftime("%Y-%m-%d %H:%M:%S")
        # username
        sender_tag = self.sender_name
        if self.sender_username:
            sender_tag += f" (@{self.sender_username})"
        
        header = f"### [{date_str}] {sender_tag} | ID: {self.id}"
        lines = [header]
        
        if self.reply_to_id:
            lines.append(f"> ↩️ ریپلای به: `{self.reply_to_id}`")
        if self.is_forwarded and self.forwarded_from:
            lines.append(f"> 🔁 فوروارد از: {self.forwarded_from}")
        
        lines.append("")
        # text - escape potential breaking but keep readable
        if self.text:
            # preserve line breaks
            lines.append(self.text.strip())
        else:
            lines.append("*[بدون متن]*")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def approx_bytes(self) -> int:
        return len(self.to_markdown_block().encode('utf-8'))

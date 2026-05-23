def convert_to_katakana(text: str) -> str:
    """ひらがなをカタカナに変換する共通ユーティリティ"""
    if not text:
        return text
    return "".join(chr(ord(c) + 96) if 0x3041 <= ord(c) <= 0x3096 else c for c in text)

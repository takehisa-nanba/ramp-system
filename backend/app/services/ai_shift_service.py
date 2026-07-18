import os
import json
from typing import List, Dict
from pydantic import BaseModel, Field

class ShiftOverwrite(BaseModel):
    supporter_id: int
    date: str
    action: str = Field(description="UPDATE, DELETE, KEEP or CREATE")
    start_time: str | None = Field(default=None, description="HH:MM format")
    end_time: str | None = Field(default=None, description="HH:MM format")
    break_minutes: int | None = Field(default=0)

class ShiftOverwriteList(BaseModel):
    overwrites: list[ShiftOverwrite]

class AiShiftService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                self.client = genai.Client(api_key=self.api_key)
                self.types = types
            except ImportError:
                print("WARNING: google-genai is not installed properly.")
            
    def adjust_shifts(self, current_shifts: List[Dict], patterns: List[Dict], instruction: str) -> List[Dict]:
        if not self.client:
            print("WARNING: GEMINI_API_KEY is not set or google-genai missing. Using dummy fallback (No changes).")
            # Fallback: if no AI, we just return empty list and let the normal generation handle it.
            return []
            
        prompt = f"""
あなたは福祉施設のシフト調整AIアシスタントです。
以下の「現在の未確定シフト一覧」と「最新のシフトパターン」、および「ユーザーからの指示」をもとに、
既存シフトをどのように変更すべきか（UPDATE/DELETE/KEEP/CREATE）を判定し、構造化データで出力してください。

# ユーザーからの指示
{instruction}

# 現在の未確定シフト一覧 (JSON)
{json.dumps(current_shifts, ensure_ascii=False)}

# 最新のシフトパターン (JSON)
{json.dumps(patterns, ensure_ascii=False)}

# ルール
- ユーザーからの指示が【最優先】です。
- 指示が空白の場合、または言及されていない日・人については、自動的に「最新のシフトパターン」に合わせるアクションを出力してください（パターンと違う時間はUPDATE、パターンにない日はDELETEなど）。
- 既にパターン通りのシフトになっている場合は出力しなくても構いません。
"""
        try:
            # Note: We use gemini-1.5-flash as the actual model endpoint, 
            # even though we refer to it conceptually as the latest generation.
            response = self.client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=self.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ShiftOverwriteList,
                    temperature=0.0
                ),
            )
            data = json.loads(response.text)
            return data.get("overwrites", [])
        except Exception as e:
            print("Failed to parse AI response:", e)
            return []

import json
import re

from jarvis.llm.base import LLMProvider, Message

_EXTRACT_PROMPT = """你是一个记忆提取器。从用户消息中提取长期有效的信息。
只提取未来有价值的信息。不要保存：临时任务、一次性问题、当前天气、当前时间。
优先提取：姓名、职业、城市、常用设备、技术栈、兴趣、长期项目、偏好。

返回JSON（如果没有新的记忆，返回{{}}）：
{{
  "user_name": "",
  "occupation": "",
  "location": "",
  "company": "",
  "devices": [],
  "projects": [],
  "interests": [],
  "preferences": {{}}
}}

用户消息：{user_text}
助手回复：{assistant_text}"""


class MemoryExtractor:
    """Uses LLM to extract structured long-term info from conversation."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def extract(self, user_text: str, assistant_text: str) -> dict:
        """Extract memory fields from a conversation exchange. Returns a dict."""
        prompt = _EXTRACT_PROMPT.format(
            user_text=user_text,
            assistant_text=assistant_text,
        )
        try:
            response = self._llm.chat(
                messages=[Message(role="user", content=prompt)],
                temperature=0.3,
                max_tokens=512,
            )
        except Exception as e:
            print(f"[Memory] Extract failed: {e}")
            return {}

        return self._parse_json(response.content)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Parse JSON from LLM output, handling markdown code fences."""
        raw = raw.strip()
        # Remove ```json ... ``` fences
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
        # Try to find a JSON object
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            raw = m.group(0)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"[Memory] JSON parse failed, raw: {raw[:200]}")
            return {}

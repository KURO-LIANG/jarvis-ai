from datetime import datetime, timezone

from jarvis.memory.models import UserMemory
from jarvis.memory.storage import FileStorage


class SummaryMemory:
    """Long-term user memory, persisted as JSON."""

    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage
        self._memory = UserMemory()

    # ─── load / save ──────────────────────────────────────

    def load(self) -> None:
        data = self._storage.load()
        if data:
            self._memory = UserMemory(
                user_name=data.get("user_name"),
                location=data.get("location"),
                company=data.get("company"),
                occupation=data.get("occupation"),
                interests=data.get("interests", []),
                devices=data.get("devices", []),
                projects=data.get("projects", []),
                preferences=data.get("preferences", {}),
                notes=data.get("notes", []),
                updated_at=data.get("updated_at", ""),
            )

    def save(self) -> None:
        self._memory.updated_at = datetime.now(timezone.utc).isoformat()
        self._storage.save(self.to_dict())

    # ─── merge ────────────────────────────────────────────

    def merge(self, new_info: dict) -> bool:
        """Merge extracted info into memory. Returns True if anything changed."""
        changed = False

        # String fields — overwrite if non-empty
        for field in ("user_name", "location", "company", "occupation"):
            value = new_info.get(field, "").strip() if isinstance(new_info.get(field), str) else ""
            if value and getattr(self._memory, field) != value:
                setattr(self._memory, field, value)
                changed = True

        # List fields — deduplicated merge
        for field in ("interests", "devices", "projects", "notes"):
            new_list = new_info.get(field, [])
            if not isinstance(new_list, list):
                new_list = []
            if new_list:
                existing = list(getattr(self._memory, field))
                merged = list(dict.fromkeys(existing + new_list))  # dedup, preserve order
                if merged != existing:
                    setattr(self._memory, field, merged)
                    changed = True

        # Dict field — shallow merge
        new_prefs = new_info.get("preferences", {})
        if isinstance(new_prefs, dict) and new_prefs:
            existing_prefs = dict(self._memory.preferences)
            existing_prefs.update(new_prefs)
            if existing_prefs != self._memory.preferences:
                self._memory.preferences = existing_prefs
                changed = True

        if changed:
            self.save()
        return changed

    # ─── prompt generation ────────────────────────────────

    def build_prompt(self) -> str:
        """Generate a context block for the system prompt. Empty if no memory."""
        if self.is_empty():
            return ""

        lines = ["=== USER MEMORY ==="]
        m = self._memory

        if m.user_name:
            lines.append(f"用户姓名：{m.user_name}")
        if m.occupation:
            lines.append(f"职业：{m.occupation}")
        if m.company:
            lines.append(f"公司：{m.company}")
        if m.location:
            lines.append(f"位置：{m.location}")
        if m.devices:
            lines.append(f"设备：{', '.join(m.devices)}")
        if m.projects:
            lines.append(f"项目：{', '.join(m.projects)}")
        if m.interests:
            lines.append(f"兴趣：{', '.join(m.interests)}")
        if m.preferences:
            for k, v in m.preferences.items():
                lines.append(f"偏好·{k}：{v}")
        if m.notes:
            for note in m.notes:
                lines.append(f"备注：{note}")

        lines.append("=== END MEMORY ===\n")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        m = self._memory
        return not any([
            m.user_name, m.location, m.company, m.occupation,
            m.interests, m.devices, m.projects, m.preferences, m.notes,
        ])

    def to_dict(self) -> dict:
        m = self._memory
        return {
            "user_name": m.user_name,
            "location": m.location,
            "company": m.company,
            "occupation": m.occupation,
            "interests": m.interests,
            "devices": m.devices,
            "projects": m.projects,
            "preferences": m.preferences,
            "notes": m.notes,
            "updated_at": m.updated_at,
        }

import re


def parse_channel_input(text: str) -> tuple[str, str]:
    text = text.strip()
    if text.startswith("@"):
        return text, text
    m = re.match(r"https?://t\.me/([a-zA-Z0-9_]+)$", text)
    if m:
        username = m.group(1)
        return f"https://t.me/{username}", f"@{username}"
    return text, text


def format_timedelta(delta):
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"

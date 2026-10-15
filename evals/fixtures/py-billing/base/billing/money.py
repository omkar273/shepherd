def fmt_cents(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"

def format_number(n: int) -> str:
    suffixes: dict[int, str] = {1_000_000_000: "B", 1_000_000: "M", 1_000: "k"}

    for threshold, suffix in suffixes.items():
        if n >= threshold:
            return f"{n / threshold:.1f}{suffix}"

    return str(n)

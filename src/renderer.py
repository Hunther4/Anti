"""
Renderer — Markdown rendering and UI formatting for Anti-Agent.

Pure functions, no agent state dependencies.
"""

import re
from src.logger import Colors


def print_header(name="ANTI-AGENT"):
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 60)
    print(f"   {name.upper()}: AUTONOMOUS EVOLVING SYSTEM")
    print("=" * 60)
    print(f"{Colors.END}")


def render_markdown(text: str) -> str:
    """
    Renders basic markdown elements into ANSI escape sequences.
    Returns the rendered string ready for terminal display.
    """
    if not text:
        return ""

    lines = text.split("\n")
    rendered_lines = []
    in_code_block = False

    for line in lines:
        # Code block toggle
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            if in_code_block:
                lang = line.replace("```", "").strip().upper() or "CODE"
                rendered_lines.append(f"{Colors.GRAY}┌─── {lang} ──────────────────────────────────────{Colors.END}")
            else:
                rendered_lines.append(f"{Colors.GRAY}└──────────────────────────────────────────────────{Colors.END}")
            continue

        if in_code_block:
            rendered_lines.append(f"{Colors.WHITE}{line}{Colors.END}")
            continue

        # Horizontal Rules
        if line.strip() in ("---", "***", "___"):
            rendered_lines.append(f"{Colors.CYAN}⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼{Colors.END}")
            continue

        # Headers
        if line.startswith("# "):
            header_text = line[2:].strip()
            rendered_lines.append(f"\n{Colors.CYAN}{Colors.BOLD}█ {header_text.upper()}{Colors.END}")
            rendered_lines.append(f"{Colors.CYAN}⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼⎼{Colors.END}")
            continue

        if line.startswith("## "):
            header_text = line[3:].strip()
            rendered_lines.append(f"\n{Colors.BLUE}{Colors.BOLD}■ {header_text.upper()}{Colors.END}")
            continue

        if line.startswith("### "):
            header_text = line[4:].strip()
            rendered_lines.append(f"\n{Colors.MAGENTA}{Colors.BOLD}➔ {header_text}{Colors.END}")
            continue

        # Lists
        stripped = line.lstrip()
        indent_len = len(line) - len(stripped)

        is_bullet = False
        content = stripped
        if stripped.startswith("* ") or stripped.startswith("- "):
            is_bullet = True
            content = stripped[2:]
        elif stripped.startswith("*") and not stripped.startswith("**"):
            is_bullet = True
            content = stripped[1:]

        if is_bullet:
            indent = " " * indent_len
            bullet_char = "•" if indent_len == 0 else "◦"
            bullet_color = Colors.CYAN if indent_len == 0 else Colors.BLUE
            line = f"{indent}{bullet_color}{bullet_char}{Colors.END} {content}"

        # Bold & Italic
        line = re.sub(r"\*\*(.*?)\*\*", f"{Colors.BOLD}\\1{Colors.END}", line)
        line = re.sub(r"\*(.*?)\*", f"{Colors.BLUE}\\1{Colors.END}", line)
        line = re.sub(r"_(.*?)_", f"{Colors.BLUE}\\1{Colors.END}", line)

        rendered_lines.append(line)

    return "\n".join(rendered_lines)


def display_banner(console, is_local: bool):
    """Displays a clean, minimal Anti-Agent startup banner."""
    color = "green" if is_local else "blue"
    console.print(f"\n[{color} bold]>>> ANTI-AGENT CORE v1.6 Quantum[/]")
    console.print(f"[{color}]Mode: {'Local' if is_local else 'Cloud'} | Status: Operational[/]\n")

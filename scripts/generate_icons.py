#!/usr/bin/env python3
"""Generate service icons matching the favicon color scheme."""

import os

# Color scheme from favicon
COLORS = {
    "primary": "#1a5a4a",  # Dark teal
    "secondary": "#2d7a6a",  # Medium teal
    "accent": "#4ade9a",  # Light green accent
    "light": "#8fdfcf",  # Light teal
    "dark": "#0d2e26",  # Very dark green
    "white": "#ffffff",
}

# Icon definitions: name -> (svg_content, description)
ICONS = {
    # Main app icons
    "icon": ("app", "Main application icon"),
    "logo": ("app", "Logo"),
    # Services
    "exchange": ("exchange", "Exchange/Trading"),
    "analysis": ("analysis", "Technical Analysis"),
    "ai": ("ai", "AI Analysis"),
    "alerts": ("alerts", "Alerts & Notifications"),
    "backfill": ("backfill", "Data Backfill"),
    "backtest": ("backtest", "Backtesting"),
    "briefing": ("briefing", "Daily Briefings"),
    "candlestick": ("candlestick", "Candlestick Charts"),
    "export": ("export", "Data Export"),
    "goals": ("goals", "Financial Goals"),
    "health": ("health", "Health Check"),
    "investor": ("investor", "Investor Mode"),
    "mcp": ("mcp", "MCP API"),
    "portfolio": ("portfolio", "Portfolio"),
    "sensors": ("sensors", "HA Sensors"),
    "signals": ("signals", "Trading Signals"),
    "streaming": ("streaming", "Real-time Streaming"),
    "summary": ("summary", "Market Summary"),
    "bybit": ("bybit", "Bybit Integration"),
}


def svg_template(content: str, size: int = 64) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['secondary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['primary']};stop-opacity:1" />
    </linearGradient>
    <linearGradient id="grad2" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{COLORS['accent']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['light']};stop-opacity:1" />
    </linearGradient>
  </defs>
  <!-- Background circle -->
  <circle cx="32" cy="32" r="30" fill="url(#grad1)" stroke="{COLORS['light']}" stroke-width="1"/>
  {content}
</svg>"""


# SVG icon contents (long lines are intentional for SVG paths)
# ruff: noqa: E501
SVG_CONTENTS = {
    "app": """
  <!-- Bitcoin B with magnifier -->
  <text x="32" y="40" text-anchor="middle" font-family="Arial Black" font-size="28" font-weight="bold" fill="{accent}">₿</text>
  <circle cx="44" cy="22" r="8" fill="none" stroke="{light}" stroke-width="2"/>
  <line x1="50" y1="28" x2="56" y2="34" stroke="{light}" stroke-width="2" stroke-linecap="round"/>
""",
    "exchange": """
  <!-- Exchange arrows -->
  <path d="M20 26 L44 26 M38 20 L44 26 L38 32" stroke="{accent}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M44 38 L20 38 M26 32 L20 38 L26 44" stroke="{light}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
""",
    "analysis": """
  <!-- Chart with magnifier -->
  <polyline points="16,44 24,36 32,40 40,28 48,32" stroke="{accent}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="42" cy="24" r="7" fill="none" stroke="{light}" stroke-width="2"/>
  <line x1="47" y1="29" x2="52" y2="34" stroke="{light}" stroke-width="2" stroke-linecap="round"/>
""",
    "ai": """
  <!-- Brain/AI icon -->
  <circle cx="32" cy="28" r="12" fill="none" stroke="{accent}" stroke-width="2"/>
  <path d="M26 28 Q32 20 38 28 Q32 36 26 28" fill="{light}" opacity="0.8"/>
  <circle cx="28" cy="26" r="2" fill="{accent}"/>
  <circle cx="36" cy="26" r="2" fill="{accent}"/>
  <path d="M24 42 L32 36 L40 42" stroke="{light}" stroke-width="2" fill="none" stroke-linecap="round"/>
""",
    "alerts": """
  <!-- Bell icon -->
  <path d="M32 16 L32 20" stroke="{light}" stroke-width="2" stroke-linecap="round"/>
  <path d="M22 36 L22 28 Q22 20 32 20 Q42 20 42 28 L42 36 L46 40 L18 40 L22 36" fill="{accent}" stroke="{light}" stroke-width="1"/>
  <circle cx="32" cy="44" r="4" fill="{light}"/>
""",
    "backfill": """
  <!-- Database with arrow -->
  <ellipse cx="32" cy="22" rx="14" ry="6" fill="{accent}" stroke="{light}" stroke-width="1"/>
  <path d="M18 22 L18 38 Q18 44 32 44 Q46 44 46 38 L46 22" fill="none" stroke="{light}" stroke-width="2"/>
  <path d="M32 28 L32 40 M26 34 L32 40 L38 34" stroke="{white}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
""",
    "backtest": """
  <!-- Clock with chart -->
  <circle cx="32" cy="32" r="14" fill="none" stroke="{accent}" stroke-width="2"/>
  <path d="M32 24 L32 32 L38 36" stroke="{light}" stroke-width="2" stroke-linecap="round"/>
  <polyline points="20,46 28,42 36,48 44,44" stroke="{accent}" stroke-width="2" fill="none" stroke-linecap="round"/>
""",
    "briefing": """
  <!-- Document/newspaper -->
  <rect x="18" y="16" width="28" height="32" rx="2" fill="{accent}" stroke="{light}" stroke-width="1"/>
  <line x1="22" y1="24" x2="42" y2="24" stroke="{dark}" stroke-width="2"/>
  <line x1="22" y1="30" x2="38" y2="30" stroke="{dark}" stroke-width="1.5"/>
  <line x1="22" y1="36" x2="40" y2="36" stroke="{dark}" stroke-width="1.5"/>
  <line x1="22" y1="42" x2="34" y2="42" stroke="{dark}" stroke-width="1.5"/>
""",
    "candlestick": """
  <!-- Candlestick chart -->
  <line x1="20" y1="20" x2="20" y2="44" stroke="{light}" stroke-width="1"/>
  <rect x="17" y="26" width="6" height="10" fill="{accent}"/>
  <line x1="32" y1="18" x2="32" y2="46" stroke="{light}" stroke-width="1"/>
  <rect x="29" y="22" width="6" height="14" fill="{light}"/>
  <line x1="44" y1="22" x2="44" y2="42" stroke="{light}" stroke-width="1"/>
  <rect x="41" y="28" width="6" height="8" fill="{accent}"/>
""",
    "export": """
  <!-- Export/download arrow -->
  <rect x="20" y="20" width="24" height="28" rx="2" fill="none" stroke="{accent}" stroke-width="2"/>
  <path d="M32 26 L32 40 M26 34 L32 40 L38 34" stroke="{light}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <line x1="24" y1="44" x2="40" y2="44" stroke="{accent}" stroke-width="2"/>
""",
    "goals": """
  <!-- Target/goal -->
  <circle cx="32" cy="32" r="14" fill="none" stroke="{accent}" stroke-width="2"/>
  <circle cx="32" cy="32" r="9" fill="none" stroke="{light}" stroke-width="2"/>
  <circle cx="32" cy="32" r="4" fill="{accent}"/>
  <path d="M46 18 L38 26" stroke="{light}" stroke-width="2" stroke-linecap="round"/>
  <path d="M44 16 L48 16 L48 20" stroke="{light}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
""",
    "health": """
  <!-- Heart/health -->
  <path d="M32 44 L20 32 Q14 24 22 20 Q30 16 32 26 Q34 16 42 20 Q50 24 44 32 L32 44" fill="{accent}" stroke="{light}" stroke-width="1"/>
  <path d="M24 30 L28 30 L30 26 L34 34 L36 30 L40 30" stroke="{white}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
""",
    "investor": """
  <!-- Person with chart -->
  <circle cx="32" cy="22" r="8" fill="{accent}"/>
  <path d="M20 48 Q20 36 32 36 Q44 36 44 48" fill="{accent}"/>
  <polyline points="18,44 26,38 34,42 42,34 50,38" stroke="{light}" stroke-width="2" fill="none" stroke-linecap="round"/>
""",
    "mcp": """
  <!-- API/connection -->
  <circle cx="22" cy="24" r="6" fill="{accent}" stroke="{light}" stroke-width="1"/>
  <circle cx="42" cy="24" r="6" fill="{accent}" stroke="{light}" stroke-width="1"/>
  <circle cx="32" cy="42" r="6" fill="{accent}" stroke="{light}" stroke-width="1"/>
  <line x1="26" y1="28" x2="30" y2="38" stroke="{light}" stroke-width="2"/>
  <line x1="38" y1="28" x2="34" y2="38" stroke="{light}" stroke-width="2"/>
  <line x1="28" y1="24" x2="36" y2="24" stroke="{light}" stroke-width="2"/>
""",
    "portfolio": """
  <!-- Pie chart -->
  <circle cx="32" cy="32" r="14" fill="{accent}"/>
  <path d="M32 32 L32 18 A14 14 0 0 1 44 38 Z" fill="{light}"/>
  <path d="M32 32 L44 38 A14 14 0 0 1 24 42 Z" fill="{secondary}"/>
  <circle cx="32" cy="32" r="5" fill="{dark}"/>
""",
    "sensors": """
  <!-- Sensor/gauge -->
  <path d="M18 40 A16 16 0 1 1 46 40" fill="none" stroke="{accent}" stroke-width="3"/>
  <circle cx="32" cy="32" r="4" fill="{light}"/>
  <line x1="32" y1="32" x2="40" y2="24" stroke="{light}" stroke-width="2" stroke-linecap="round"/>
  <circle cx="22" cy="44" r="2" fill="{accent}"/>
  <circle cx="32" cy="46" r="2" fill="{light}"/>
  <circle cx="42" cy="44" r="2" fill="{accent}"/>
""",
    "signals": """
  <!-- Signal waves -->
  <circle cx="24" cy="32" r="4" fill="{accent}"/>
  <path d="M30 32 Q34 24 38 32 Q42 40 46 32" stroke="{light}" stroke-width="2" fill="none"/>
  <path d="M34 32 Q38 26 42 32 Q46 38 50 32" stroke="{accent}" stroke-width="2" fill="none"/>
  <path d="M26 32 Q30 38 34 32" stroke="{light}" stroke-width="2" fill="none"/>
""",
    "streaming": """
  <!-- Live/streaming -->
  <circle cx="32" cy="32" r="6" fill="{accent}"/>
  <circle cx="32" cy="32" r="11" fill="none" stroke="{light}" stroke-width="2" opacity="0.8"/>
  <circle cx="32" cy="32" r="16" fill="none" stroke="{accent}" stroke-width="2" opacity="0.6"/>
  <circle cx="32" cy="32" r="21" fill="none" stroke="{light}" stroke-width="2" opacity="0.4"/>
""",
    "summary": """
  <!-- Dashboard/summary -->
  <rect x="18" y="18" width="12" height="10" rx="1" fill="{accent}"/>
  <rect x="34" y="18" width="12" height="10" rx="1" fill="{light}"/>
  <rect x="18" y="32" width="12" height="14" rx="1" fill="{light}"/>
  <rect x="34" y="32" width="12" height="14" rx="1" fill="{accent}"/>
""",
    "bybit": """
  <!-- Bybit-style logo -->
  <path d="M20 24 L32 18 L44 24 L44 40 L32 46 L20 40 Z" fill="none" stroke="{accent}" stroke-width="2"/>
  <path d="M26 28 L32 24 L38 28 L38 36 L32 40 L26 36 Z" fill="{light}"/>
  <text x="32" y="35" text-anchor="middle" font-family="Arial" font-size="8" font-weight="bold" fill="{dark}">B</text>
""",
}


def generate_svg(icon_type: str) -> str:
    """Generate SVG content for an icon type."""
    content = SVG_CONTENTS.get(icon_type, SVG_CONTENTS["app"])
    content = content.format(**COLORS)
    return svg_template(content)


def main():
    output_dir = "img"
    os.makedirs(output_dir, exist_ok=True)

    print("Generating service icons...")
    print(f"Output directory: {output_dir}/")
    print("-" * 40)

    for name, (icon_type, description) in ICONS.items():
        svg_content = generate_svg(icon_type)
        filepath = os.path.join(output_dir, f"{name}.svg")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content)

        print(f"✅ {name}.svg - {description}")

    print("-" * 40)
    print(f"Generated {len(ICONS)} icons")
    print("\nTo convert to PNG, use:")
    print("  pip install cairosvg")
    print("  python -c \"import cairosvg; cairosvg.svg2png(url='icon.svg', write_to='icon.png', output_width=128)\"")


if __name__ == "__main__":
    main()

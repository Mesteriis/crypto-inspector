#!/usr/bin/env python3
"""
Generate static HTML documentation from dashboard YAML examples.

This script:
1. Reads all YAML files from dashboards/ directory
2. Generates beautiful HTML documentation with code examples
3. Creates card previews with syntax highlighting
4. Outputs to docs/ folder for GitHub Pages
"""

import html
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DASHBOARDS_DIR = PROJECT_ROOT / "dashboards"
DOCS_DIR = PROJECT_ROOT / "docs"
CARDS_DIR = DASHBOARDS_DIR / "cards"
VIEWS_DIR = DASHBOARDS_DIR / "views"


# Card type icons and colors
CARD_ICONS = {
    "custom:apexcharts-card": ("📊", "#FF6384"),
    "custom:mushroom-template-card": ("🍄", "#9966FF"),
    "custom:mushroom-entity-card": ("🍄", "#9966FF"),
    "entities": ("📋", "#36A2EB"),
    "glance": ("👁️", "#4BC0C0"),
    "vertical-stack": ("📚", "#FFCE56"),
    "horizontal-stack": ("📑", "#FF9F40"),
    "markdown": ("📝", "#C9CBCF"),
    "conditional": ("❓", "#7C4DFF"),
    "grid": ("🔲", "#00BCD4"),
}

# CSS styles
CSS_STYLES = """
:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --text-primary: #c9d1d9;
    --text-secondary: #8b949e;
    --accent: #58a6ff;
    --accent-hover: #79c0ff;
    --border: #30363d;
    --success: #3fb950;
    --warning: #d29922;
    --error: #f85149;
}

* { box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    margin: 0;
    padding: 0;
    line-height: 1.6;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

header {
    background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
    border-bottom: 1px solid var(--border);
    padding: 40px 20px;
    text-align: center;
}

header h1 {
    margin: 0 0 10px 0;
    font-size: 2.5rem;
    background: linear-gradient(90deg, #58a6ff, #a371f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

header p {
    color: var(--text-secondary);
    font-size: 1.1rem;
    margin: 0;
}

.badges {
    margin-top: 20px;
}

.badges img {
    margin: 0 5px;
}

nav {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    padding: 15px 20px;
    position: sticky;
    top: 0;
    z-index: 100;
}

nav ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
}

nav a {
    color: var(--text-primary);
    text-decoration: none;
    padding: 8px 16px;
    border-radius: 6px;
    background: var(--bg-tertiary);
    transition: all 0.2s;
}

nav a:hover {
    background: var(--accent);
    color: white;
}

section {
    margin: 40px 0;
}

section h2 {
    border-bottom: 2px solid var(--border);
    padding-bottom: 10px;
    margin-bottom: 20px;
    font-size: 1.8rem;
}

.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 20px;
}

.card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
}

.card-header {
    padding: 16px 20px;
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
}

.card-icon {
    font-size: 1.5rem;
}

.card-title {
    font-weight: 600;
    font-size: 1.1rem;
}

.card-type {
    margin-left: auto;
    font-size: 0.8rem;
    color: var(--text-secondary);
    background: var(--bg-primary);
    padding: 4px 10px;
    border-radius: 12px;
}

.card-preview {
    padding: 20px;
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.card-code {
    max-height: 300px;
    overflow: auto;
}

.card-code pre {
    margin: 0;
    padding: 16px;
    background: var(--bg-primary);
    border-radius: 0 0 12px 12px;
    font-size: 0.85rem;
    line-height: 1.5;
    overflow-x: auto;
}

.card-code code {
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
    color: var(--text-primary);
}

.copy-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.2s;
}

.copy-btn:hover {
    background: var(--accent);
    color: white;
}

.code-container {
    position: relative;
}

/* Preview mockups */
.preview-gauge {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: conic-gradient(from 225deg, #dc3545 0deg, #ffc107 90deg, #28a745 180deg, transparent 180deg);
    margin: 0 auto;
    position: relative;
}

.preview-gauge::after {
    content: '50';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 1.5rem;
    font-weight: bold;
}

.preview-mushroom {
    background: var(--bg-tertiary);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.preview-mushroom-icon {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
}

.preview-mushroom-text h4 { margin: 0; font-size: 1rem; }
.preview-mushroom-text p { margin: 0; color: var(--text-secondary); font-size: 0.85rem; }

.preview-entities {
    background: var(--bg-tertiary);
    border-radius: 12px;
    overflow: hidden;
}

.preview-entity-row {
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
}

.preview-entity-row:last-child { border-bottom: none; }
.preview-entity-name { color: var(--text-secondary); }
.preview-entity-value { font-weight: 600; }

.feature-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin: 30px 0;
}

.feature {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
}

.feature h3 {
    margin: 0 0 10px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}

.feature p { color: var(--text-secondary); margin: 0; }

.install-steps {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
}

.install-steps ol {
    margin: 0;
    padding-left: 20px;
}

.install-steps li { margin: 10px 0; }
.install-steps code {
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 4px;
}

footer {
    text-align: center;
    padding: 40px 20px;
    border-top: 1px solid var(--border);
    color: var(--text-secondary);
}

footer a { color: var(--accent); }

@media (max-width: 768px) {
    .cards-grid { grid-template-columns: 1fr; }
    header h1 { font-size: 1.8rem; }
    nav ul { flex-direction: column; align-items: center; }
}

/* YAML syntax highlighting */
.yaml-key { color: #79c0ff; }
.yaml-string { color: #a5d6ff; }
.yaml-number { color: #7ee787; }
.yaml-bool { color: #ff7b72; }
.yaml-comment { color: #8b949e; font-style: italic; }
"""

# JavaScript
JS_SCRIPT = """
function copyToClipboard(btn, cardId) {
    const codeEl = document.getElementById(cardId);
    // Get raw text from data attribute if available, otherwise use textContent
    const rawYaml = codeEl.getAttribute('data-raw') || codeEl.textContent;
    navigator.clipboard.writeText(rawYaml).then(() => {
        btn.textContent = '✓ Copied!';
        setTimeout(() => btn.textContent = '📋 Copy', 2000);
    });
}
"""


def highlight_yaml(text: str) -> str:
    """Simple YAML syntax highlighting."""
    # First escape HTML entities
    text = html.escape(text)

    lines = []
    for line in text.split("\n"):
        # Comments
        if line.strip().startswith("#"):
            line = f'<span class="yaml-comment">{line}</span>'
        else:
            # Keys (word followed by colon)
            line = re.sub(r"^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*):", r'\1<span class="yaml-key">\2</span>:', line)
            # Strings in quotes (already escaped by html.escape)
            line = re.sub(r"&quot;([^&]*)&quot;", r'<span class="yaml-string">&quot;\1&quot;</span>', line)
            line = re.sub(r"&#x27;([^&]*)&#x27;", r'<span class="yaml-string">&#x27;\1&#x27;</span>', line)
            # Numbers at end of line
            line = re.sub(r": (\d+)$", r': <span class="yaml-number">\1</span>', line)
            line = re.sub(r": (\d+\.\d+)$", r': <span class="yaml-number">\1</span>', line)
            # Booleans
            line = re.sub(r": (true|false)$", r': <span class="yaml-bool">\1</span>', line)
        lines.append(line)
    return "\n".join(lines)


def get_card_preview(card_type: str, card_data: dict) -> str:
    """Generate HTML preview mockup for a card type."""
    if "apexcharts" in card_type and card_data.get("chart_type") == "radialBar":
        return """
        <div class="preview-gauge"></div>
        <p style="text-align:center; color: var(--text-secondary); margin-top: 10px;">Fear & Greed Gauge</p>
        """

    if "mushroom" in card_type:
        primary = card_data.get("primary", "Card Title")
        secondary = (
            card_data.get("secondary", "Secondary info")[:50] + "..."
            if len(str(card_data.get("secondary", ""))) > 50
            else card_data.get("secondary", "Secondary info")
        )
        return f"""
        <div class="preview-mushroom">
            <div class="preview-mushroom-icon">🍄</div>
            <div class="preview-mushroom-text">
                <h4>{primary if isinstance(primary, str) else 'Dynamic'}</h4>
                <p>{secondary if isinstance(secondary, str) else 'Jinja template'}</p>
            </div>
        </div>
        """

    if card_type == "entities":
        entities = card_data.get("entities", [])[:4]
        rows = ""
        for e in entities:
            name = e.get("name", e.get("entity", "").split(".")[-1]) if isinstance(e, dict) else str(e).split(".")[-1]
            rows += f"""
            <div class="preview-entity-row">
                <span class="preview-entity-name">{name}</span>
                <span class="preview-entity-value">—</span>
            </div>
            """
        return f'<div class="preview-entities">{rows}</div>'

    if card_type == "glance":
        return """
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div><div style="font-size: 2rem;">📈</div><div>1.5</div><small>Sharpe</small></div>
            <div><div style="font-size: 2rem;">📉</div><div>-12%</div><small>Max DD</small></div>
            <div><div style="font-size: 2rem;">⚠️</div><div>5%</div><small>VaR</small></div>
        </div>
        """

    return '<p style="text-align: center; color: var(--text-secondary);">Preview not available</p>'


def parse_cards_file(filepath: Path) -> list:
    """Parse YAML file and extract card definitions."""
    cards = []
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    try:
        data = yaml.safe_load(content)
        if data:
            for name, card_def in data.items():
                if isinstance(card_def, dict) and not name.startswith("_"):
                    cards.append(
                        {
                            "name": name,
                            "data": card_def,
                            "yaml": yaml.dump(
                                {name: card_def}, default_flow_style=False, allow_unicode=True, sort_keys=False
                            ),
                        }
                    )
    except yaml.YAMLError:
        pass

    return cards


def parse_view_file(filepath: Path) -> dict:
    """Parse dashboard view YAML file."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    try:
        data = yaml.safe_load(content)
        return {
            "title": data.get("title", filepath.stem),
            "icon": data.get("icon", "mdi:view-dashboard"),
            "description": content.split("\n")[1].strip("# ") if content.startswith("#") else "",
            "yaml": content,
            "data": data,
        }
    except yaml.YAMLError:
        return None


def generate_card_html(card: dict, index: int) -> str:
    """Generate HTML for a single card."""
    card_type = card["data"].get("type", "unknown")
    icon, color = CARD_ICONS.get(card_type, ("📦", "#888"))
    card_id = f"card-{index}"

    # Format name
    name = card["name"].replace("_", " ").title()

    preview = get_card_preview(card_type, card["data"])
    raw_yaml = card["yaml"]
    highlighted_yaml = highlight_yaml(raw_yaml)
    # Escape raw YAML for data attribute
    raw_yaml_escaped = html.escape(raw_yaml)

    return f"""
    <div class="card">
        <div class="card-header">
            <span class="card-icon">{icon}</span>
            <span class="card-title">{name}</span>
            <span class="card-type" style="background: {color}22; color: {color};">{card_type}</span>
        </div>
        <div class="card-preview">
            {preview}
        </div>
        <div class="card-code">
            <div class="code-container">
                <button class="copy-btn" onclick="copyToClipboard(this, '{card_id}')">📋 Copy</button>
                <pre><code id="{card_id}" data-raw="{raw_yaml_escaped}">{highlighted_yaml}</code></pre>
            </div>
        </div>
    </div>
    """


def generate_view_section(view: dict, index: int) -> str:
    """Generate HTML section for a dashboard view."""
    view_id = f"view-{index}"
    raw_yaml = view["yaml"]
    highlighted_yaml = highlight_yaml(raw_yaml)
    raw_yaml_escaped = html.escape(raw_yaml)

    return f"""
    <div class="card" style="grid-column: 1 / -1;">
        <div class="card-header">
            <span class="card-icon">📱</span>
            <span class="card-title">{view['title']}</span>
            <span class="card-type">Dashboard View</span>
        </div>
        <div class="card-preview">
            <p>{view['description']}</p>
        </div>
        <div class="card-code">
            <div class="code-container">
                <button class="copy-btn" onclick="copyToClipboard(this, '{view_id}')">📋 Copy</button>
                <pre><code id="{view_id}" data-raw="{raw_yaml_escaped}">{highlighted_yaml}</code></pre>
            </div>
        </div>
    </div>
    """


def generate_html() -> str:
    """Generate complete HTML documentation."""
    # Parse all cards
    cards = []
    if CARDS_DIR.exists():
        for yaml_file in CARDS_DIR.glob("*.yaml"):
            cards.extend(parse_cards_file(yaml_file))

    # Parse all views
    views = []
    if VIEWS_DIR.exists():
        for yaml_file in VIEWS_DIR.glob("*.yaml"):
            view = parse_view_file(yaml_file)
            if view:
                views.append(view)

    # Parse main dashboard files
    dashboards = []
    for yaml_file in DASHBOARDS_DIR.glob("*.yaml"):
        with open(yaml_file, encoding="utf-8") as f:
            content = f.read()
        dashboards.append({"name": yaml_file.stem.replace("_", " ").title(), "yaml": content})

    # Generate card HTML
    cards_html = "\n".join(generate_card_html(c, i) for i, c in enumerate(cards))
    views_html = "\n".join(generate_view_section(v, i) for i, v in enumerate(views))

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Inspect - Dashboard Cards Gallery</title>
    <meta name="description" content="Beautiful Home Assistant dashboard cards for cryptocurrency monitoring. Copy-paste ready YAML configurations.">
    <link rel="icon" type="image/png" href="https://raw.githubusercontent.com/Mesteriis/crypto-inspector/main/icons/icon-192.png">
    <style>{CSS_STYLES}</style>
</head>
<body>
    <header>
        <h1>🚀 Crypto Inspect Cards</h1>
        <p>Beautiful Home Assistant dashboard cards for cryptocurrency monitoring</p>
        <div class="badges">
            <img src="https://img.shields.io/github/v/release/Mesteriis/crypto-inspector?style=flat-square&color=blue" alt="Version">
            <img src="https://img.shields.io/github/license/Mesteriis/crypto-inspector?style=flat-square" alt="License">
            <img src="https://img.shields.io/badge/Home%20Assistant-2024.1+-blue?style=flat-square&logo=home-assistant" alt="Home Assistant">
        </div>
    </header>

    <nav>
        <ul>
            <li><a href="#installation">📦 Installation</a></li>
            <li><a href="#cards">🎴 Cards</a></li>
            <li><a href="#views">📱 Views</a></li>
            <li><a href="#features">✨ Features</a></li>
            <li><a href="https://github.com/Mesteriis/crypto-inspector">GitHub</a></li>
        </ul>
    </nav>

    <div class="container">
        <section id="installation">
            <h2>📦 Installation</h2>
            <div class="install-steps">
                <ol>
                    <li>Install the <strong>Crypto Inspect</strong> add-on in Home Assistant</li>
                    <li>Install required HACS cards:
                        <ul>
                            <li><code>custom:apexcharts-card</code> - for charts and gauges</li>
                            <li><code>custom:mushroom-cards</code> - for beautiful entity cards</li>
                        </ul>
                    </li>
                    <li>Copy any card YAML below to your Lovelace dashboard</li>
                    <li>Customize colors and entities as needed</li>
                </ol>
            </div>
        </section>

        <section id="features">
            <h2>✨ Features</h2>
            <div class="feature-list">
                <div class="feature">
                    <h3>📊 Technical Analysis</h3>
                    <p>RSI, MACD, Support/Resistance levels, Multi-timeframe trends</p>
                </div>
                <div class="feature">
                    <h3>😱 Fear & Greed Index</h3>
                    <p>Real-time market sentiment with beautiful gauge visualization</p>
                </div>
                <div class="feature">
                    <h3>🛡️ Risk Management</h3>
                    <p>Portfolio risk metrics, Sharpe ratio, VaR, Max Drawdown</p>
                </div>
                <div class="feature">
                    <h3>🤖 AI Analysis</h3>
                    <p>AI-powered market insights with Ollama or OpenAI</p>
                </div>
                <div class="feature">
                    <h3>📈 DCA Strategies</h3>
                    <p>Dollar-cost averaging recommendations and backtest results</p>
                </div>
                <div class="feature">
                    <h3>🔔 Smart Alerts</h3>
                    <p>Price alerts, whale movements, technical signals</p>
                </div>
            </div>
        </section>

        <section id="cards">
            <h2>🎴 Card Examples</h2>
            <p>Click "Copy" to copy the YAML configuration to your clipboard.</p>
            <div class="cards-grid">
                {cards_html}
            </div>
        </section>

        <section id="views">
            <h2>📱 Complete Dashboard Views</h2>
            <p>Ready-to-use dashboard views for different use cases.</p>
            <div class="cards-grid">
                {views_html}
            </div>
        </section>
    </div>

    <footer>
        <p>Generated on {now} |
        <a href="https://github.com/Mesteriis/crypto-inspector">GitHub</a> |
        Made with ❤️ for Home Assistant</p>
    </footer>

    <script>{JS_SCRIPT}</script>
</body>
</html>
"""


def main():
    """Main entry point."""
    print("🔧 Generating documentation...")

    # Create docs directory
    DOCS_DIR.mkdir(exist_ok=True)

    # Generate HTML
    html_content = generate_html()

    # Write index.html
    index_path = DOCS_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Generated {index_path}")

    # Copy icons if they exist
    icons_src = PROJECT_ROOT / "icons"
    icons_dst = DOCS_DIR / "icons"
    if icons_src.exists():
        if icons_dst.exists():
            shutil.rmtree(icons_dst)
        shutil.copytree(icons_src, icons_dst)
        print(f"✅ Copied icons to {icons_dst}")

    # Create .nojekyll for GitHub Pages
    nojekyll = DOCS_DIR / ".nojekyll"
    nojekyll.touch()

    print("🎉 Documentation generated successfully!")
    print(f"📁 Output: {DOCS_DIR}")


if __name__ == "__main__":
    main()

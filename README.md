# 🔍 LinkedIn Mentions Scraper

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Stability: Stable](https://img.shields.io/badge/stability-stable-green.svg)](#)

A high-performance, automated intelligence tool designed to discover and categorize LinkedIn mentions using advanced search discovery and anti-bot evasion techniques. Ideal for tracking brand mentions, executive visibility, and industry trends.

---

## 🌟 Key Features

*   **🎯 High-Precision Discovery**: Utilizes Google Search's advanced indexing to surface LinkedIn posts, pulses, and activities from the last 6 months.
*   **🛡️ Anti-Bot Evasion**: Powered by `SeleniumBase` UC mode, featuring:
    *   Randomized User-Agent cycling.
    *   Human-like behavioral jitter (scrolling & interaction).
    *   CDP (Chrome DevTools Protocol) stealth bypasses.
*   **🧠 Intelligent Categorization**:
    *   **Regex Engine**: High-speed keyword identification.
    *   **Fuzzy Fallback**: `RapidFuzz` logic to capture mentions with OCR artifacts or spelling variations.
*   **📊 Comprehensive Reporting**: Generates clean **CSV** for data pipelines and a professionally styled **HTML** dashboard for stakeholders.

---

## 🛠️ Quick Start

### 📋 Prerequisites

- **Python 3.10+**
- **Google Chrome** (Latest version recommended)

### 📥 Installation

1.  **Clone & Navigate**:
    ```bash
    git clone https://github.com/your-username/linkedin-posts-scraper.git
    cd linkedin-posts-scraper
    ```

2.  **Environment Setup** (Recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### 🚀 Usage

Execute the main intelligence script:
```bash
python google_mentions_scraper.py
```

Results are automatically saved to the project root:
- `google_mentions.csv`: Raw, sortable datasets.
- `google_mentions.html`: Interactive visual report.

---

## 🏗️ Technical Architecture

For an in-depth dive into the scraping engine, data normalization, and anti-detection strategies, please refer to the **[ARCHITECTURE.md](./ARCHITECTURE.md)**.

---

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
*Developed for professional brand monitoring and data analysis.*

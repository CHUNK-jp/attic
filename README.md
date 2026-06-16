# 🏠 Attic

**Search Your Digital Life, Locally.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Powered by Ollama](https://img.shields.io/badge/Powered%20by-Ollama-black?style=flat)](https://ollama.com/)
[![No Cloud](https://img.shields.io/badge/Cloud-None-lightgrey?style=flat)](#)

> A privacy-first personal search engine for your local files.  
> Natural language queries. 100% offline. No cloud. No subscription.

![Attic Demo](docs/demo.gif)

## 🚀 Quick Start

\`\`\`bash
ollama pull nomic-embed-text
pip install -r requirements.txt
python3 attic.py index ~/Documents
python3 attic.py search "Q1 budget report"
\`\`\`

## 📖 Usage

| Command | Description |
|---|---|
| `index <folder>` | Scan and index all files in a folder |
| `search <query>` | Search with natural language |
| `status` | Show index statistics |
| `clear` | Delete the entire index |

## 📁 Supported File Types

PDF, DOCX, TXT, Markdown, Python, JS, TS, JSON, YAML, CSV and more.

## 🧠 How It Works

\`\`\`
Files → Text extraction → Chunking → Ollama embeddings → ChromaDB
Query ──────────────────────────── Ollama embeddings → Similarity search
\`\`\`

## 📄 License

MIT — free to use, modify, and distribute.

---
*Built by [CHUNK-jp](https://github.com/CHUNK-jp) · No cloud. No subscription. Just your files.*

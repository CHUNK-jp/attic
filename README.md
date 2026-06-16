# 🏠 Attic

**Search Your Digital Life, Locally.**

ローカルLLMを使って自分のファイルを自然言語で検索できるツール。
クラウドなし。サブスクなし。データはすべて自分のマシンに留まる。

---

## セットアップ

### 1. Ollamaをインストール・起動

```bash
# https://ollama.com からインストール後:
ollama serve
ollama pull nomic-embed-text
```

### 2. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

---

## 使い方

### フォルダをインデックス化

```bash
python attic.py index ~/Documents
python attic.py index ~/Desktop --reset   # インデックスをリセットして再スキャン
```

### 自然言語で検索

```bash
python attic.py search "去年の確定申告の資料"
python attic.py search "Q1 budget report"
python attic.py search "田中さんへの提案書"
python attic.py search "Pythonのasync処理のメモ"
```

### 件数を増やす

```bash
python attic.py search "会議の議事録" -n 10
```

### インデックスの状態確認

```bash
python attic.py status
```

### インデックスを削除

```bash
python attic.py clear
```

---

## 対応ファイル形式

| 種別 | 拡張子 |
|------|--------|
| ドキュメント | `.pdf`, `.docx`, `.txt`, `.md`, `.rst` |
| コード | `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.sh` |
| Web | `.html`, `.css` |
| データ | `.json`, `.yaml`, `.yml`, `.csv`, `.toml` |

---

## 仕組み

```
ファイル → テキスト抽出 → チャンク分割 → Ollama埋め込み → ChromaDB保存
                                                                    ↑
クエリ ────────────────────────────────── Ollama埋め込み → 類似検索
```

- **埋め込みモデル**: `nomic-embed-text`（Ollama経由でローカル動作）
- **ベクトルDB**: ChromaDB（`~/.attic/db/` に保存）
- **テキスト抽出**: pypdf（PDF）、python-docx（Word）、UTF-8読み込み（その他）

---

## ヒント

- 初回インデックスはファイル数に応じて数分かかります
- 2回目以降は変更ファイルのみ更新するので高速です
- `--ext .log` などで追加の拡張子を指定できます

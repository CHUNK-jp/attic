#!/usr/bin/env python3
"""
Attic — Search Your Digital Life, Locally
==========================================
A privacy-first personal file search engine powered by local LLM embeddings.
No cloud. No subscription. Your data stays on your machine.

Usage:
  python attic.py index ~/Documents
  python attic.py search "last month's budget spreadsheet"
  python attic.py status
"""

import hashlib
import sys
from pathlib import Path

import click
import chromadb
import ollama
import pypdf
import docx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

console = Console()

# ── Constants ────────────────────────────────────────────────────────────────

ATTIC_DIR = Path.home() / ".attic"
DB_PATH = ATTIC_DIR / "db"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 400       # words per chunk
CHUNK_OVERLAP = 40     # overlapping words between chunks

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".txt", ".md", ".markdown",
    ".rst", ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".json", ".yaml", ".yml",
    ".csv", ".toml", ".ini", ".conf", ".sh",
}

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    ATTIC_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_PATH))
    return client.get_or_create_collection(
        "attic_index",
        metadata={"hnsw:space": "cosine"},
    )


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            reader = pypdf.PdfReader(str(file_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        elif suffix == ".docx":
            doc = docx.Document(str(file_path))
            return "\n".join(p.text for p in doc.paragraphs)
        else:
            return file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def chunk_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + CHUNK_SIZE])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def check_ollama() -> bool:
    try:
        ollama.embeddings(model=EMBED_MODEL, prompt="test")
        return True
    except Exception:
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """🏠  Attic — Search your digital life, locally.\n
    \b
    Quick start:
      python attic.py index ~/Documents
      python attic.py search "Q1 budget report"
    """
    pass


@cli.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--reset", is_flag=True, help="Clear existing index before indexing.")
@click.option("--ext", multiple=True, help="Extra file extensions to include (e.g. --ext .log).")
def index(folder: str, reset: bool, ext: tuple):
    """Scan and index all files in FOLDER."""

    console.print("\n[bold cyan]🏠 Attic[/bold cyan] — indexing started\n")

    # Ollama check
    console.print("[dim]Checking Ollama connection...[/dim]")
    if not check_ollama():
        console.print(
            "[bold red]✗ Cannot reach Ollama.[/bold red]\n"
            "  Make sure Ollama is running: [bold]ollama serve[/bold]\n"
            f"  And pull the embedding model: [bold]ollama pull {EMBED_MODEL}[/bold]"
        )
        sys.exit(1)
    console.print(f"[green]✓ Ollama connected[/green] (model: {EMBED_MODEL})\n")

    supported = SUPPORTED_EXTENSIONS | {e if e.startswith(".") else f".{e}" for e in ext}

    collection = get_collection()

    if reset:
        client = chromadb.PersistentClient(path=str(DB_PATH))
        client.delete_collection("attic_index")
        collection = get_collection()
        console.print("[yellow]Existing index cleared.[/yellow]\n")

    folder_path = Path(folder).expanduser().resolve()
    files = [
        f for f in folder_path.rglob("*")
        if f.is_file() and f.suffix.lower() in supported
    ]

    console.print(f"Found [bold]{len(files)}[/bold] files in [cyan]{folder_path}[/cyan]\n")

    indexed = skipped = errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing...", total=len(files))

        for file_path in files:
            progress.update(task, description=f"[dim]{file_path.name[:50]}[/dim]")

            file_id = hashlib.md5(str(file_path).encode()).hexdigest()
            mtime = str(file_path.stat().st_mtime)

            # Skip unchanged files
            existing = collection.get(where={"file_id": file_id}, include=["metadatas"])
            if existing["ids"] and existing["metadatas"][0].get("mtime") == mtime:
                skipped += 1
                progress.advance(task)
                continue

            # Remove stale chunks for this file
            if existing["ids"]:
                collection.delete(where={"file_id": file_id})

            text = extract_text(file_path)
            if not text.strip():
                progress.advance(task)
                continue

            chunks = chunk_text(text)
            ok = True
            for i, chunk in enumerate(chunks):
                try:
                    embedding = embed(chunk)
                    collection.upsert(
                        ids=[f"{file_id}_{i}"],
                        embeddings=[embedding],
                        documents=[chunk],
                        metadatas=[{
                            "file_path": str(file_path),
                            "file_name": file_path.name,
                            "file_id": file_id,
                            "mtime": mtime,
                            "chunk_index": i,
                        }],
                    )
                except Exception as e:
                    errors += 1
                    ok = False
                    break

            if ok:
                indexed += 1
            progress.advance(task)

    console.print(
        f"\n[bold green]✓ Done![/bold green]  "
        f"Indexed: [green]{indexed}[/green]  "
        f"Skipped (unchanged): [dim]{skipped}[/dim]  "
        f"Errors: [red]{errors}[/red]\n"
    )


@cli.command()
@click.argument("query")
@click.option("-n", default=5, show_default=True, help="Number of results.")
def search(query: str, n: int):
    """Search indexed files with a natural language QUERY."""

    collection = get_collection()
    total = collection.count()

    if total == 0:
        console.print(
            "[yellow]No files indexed yet.[/yellow]\n"
            "Run:  [bold]python attic.py index <folder>[/bold]"
        )
        return

    console.print(f"\n[dim]Searching {total:,} chunks...[/dim]")

    try:
        q_embedding = embed(query)
    except Exception:
        console.print(
            "[bold red]✗ Cannot reach Ollama.[/bold red]\n"
            "  Make sure it's running: [bold]ollama serve[/bold]"
        )
        sys.exit(1)

    # Fetch 3× results, then deduplicate to best match per file
    raw = collection.query(
        query_embeddings=[q_embedding],
        n_results=min(n * 4, total),
        include=["documents", "metadatas", "distances"],
    )

    best: dict[str, dict] = {}
    for doc, meta, dist in zip(
        raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
    ):
        fp = meta["file_path"]
        score = 1.0 - float(dist)
        if fp not in best or best[fp]["score"] < score:
            best[fp] = {"doc": doc, "meta": meta, "score": score}

    results = sorted(best.values(), key=lambda x: -x["score"])[:n]

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(
        title=f'\n🔍  Results for: "{query}"',
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("Score", style="bold green", width=7, no_wrap=True)
    table.add_column("File", style="bold cyan", width=28, no_wrap=True)
    table.add_column("Snippet", width=55)
    table.add_column("Folder", style="dim", width=35)

    for r in results:
        fp = Path(r["meta"]["file_path"])
        snippet = r["doc"][:220].replace("\n", " ").strip()
        if len(r["doc"]) > 220:
            snippet += "…"
        table.add_row(
            f"{r['score']:.0%}",
            fp.name,
            snippet,
            str(fp.parent),
        )

    console.print(table)
    console.print()


@cli.command()
def status():
    """Show index statistics."""
    collection = get_collection()
    total_chunks = collection.count()

    console.print("\n[bold cyan]🏠 Attic — Index Status[/bold cyan]\n")

    if total_chunks == 0:
        console.print("  [yellow]No files indexed yet.[/yellow]")
        console.print("  Run:  [bold]python attic.py index <folder>[/bold]\n")
        return

    all_meta = collection.get(include=["metadatas"])
    file_paths = [m["file_path"] for m in all_meta["metadatas"]]
    unique_files = len(set(file_paths))

    # Extension breakdown
    ext_counts: dict[str, int] = {}
    for p in file_paths:
        ext = Path(p).suffix.lower() or "(none)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    console.print(f"  Files indexed : [bold green]{unique_files:,}[/bold green]")
    console.print(f"  Total chunks  : [bold green]{total_chunks:,}[/bold green]")
    console.print(f"  DB location   : [dim]{DB_PATH}[/dim]")
    console.print(f"  Embed model   : [dim]{EMBED_MODEL}[/dim]\n")

    # Top extensions
    top_ext = sorted(ext_counts.items(), key=lambda x: -x[1])[:8]
    table = Table(title="Top file types", show_header=True, header_style="bold")
    table.add_column("Extension", style="cyan")
    table.add_column("Chunks", justify="right", style="green")
    for ext, count in top_ext:
        table.add_row(ext, str(count))
    console.print(table)
    console.print()


@cli.command()
def clear():
    """Remove the entire Attic index."""
    if not click.confirm("⚠️  This will delete the entire index. Continue?"):
        console.print("[dim]Cancelled.[/dim]")
        return
    try:
        client = chromadb.PersistentClient(path=str(DB_PATH))
        client.delete_collection("attic_index")
        console.print("[green]✓ Index cleared.[/green]")
    except Exception:
        console.print("[dim]Index was already empty.[/dim]")


if __name__ == "__main__":
    cli()

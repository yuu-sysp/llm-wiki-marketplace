#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM-Wiki lint — ドリフト検出スクリプト（配布プラグイン版）.

検出項目:
  1. 赤リンク       : [[リンク]] 先ファイルが存在しない（lint-ignore.txt で許容可）
  2. 孤立ページ     : どこからも [[リンク]] されていない content ファイル
  3. 空ファイル     : 0byte の .md
  4. frontmatter欠落: 先頭が --- でない / 必須キー欠落
  5. inbox残存/空スタブ: 未処理ファイル・中身なしスタブ（当日は想定内）
  6. inbox未変換    : 非 md ファイル・フォルダ（convert_inbox.py 待ち。ingest は *.md しか見ない）

vault ルートは argv[1] → 環境変数の順で解決（_vault.resolve_vault）。
  例: python lint.py "D:/資料/LLM-Wiki"
終了コード: 問題ゼロなら 0、1件以上あれば 1（CI 連携用）
"""
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault import print_unresolved_hint, resolve_vault  # noqa: E402

TODAY = datetime.now().strftime("%Y-%m-%d")
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")

# Windows コンソール(cp932)でも UTF-8 出力（em-dash 等でのクラッシュ防止）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 各フォルダ直下のフラット運用（サブフォルダは走査しない＝index にも lint にも載らない）。
CONTENT_DIRS = ["concepts", "pages", "notes", "qa"]     # リンク対象になるフォルダ
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
REQUIRED_FM = ("type", "created")                        # 拡張frontmatterの最小必須


def link_target(raw: str) -> str:
    """[[name|alias]] / [[name#heading]] -> name"""
    return raw.split("|")[0].split("#")[0].strip()


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="cp932", errors="replace")


def has_fm_key(block: str, key: str) -> bool:
    """行頭一致で判定する。部分一致だと `doctype:` が `type:` を満たしてしまう。"""
    return re.search(rf"^\s*{re.escape(key)}\s*:", block, re.M) is not None


def frontmatter_block(text: str) -> str:
    """先頭 --- ... --- の中身を返す。無ければ None。"""
    if not text.lstrip().startswith("---"):
        return None
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else None


def is_stub(text: str) -> bool:
    """frontmatter・見出し・project行・HTMLコメント・空行のみなら中身なしスタブ。"""
    body = text
    if body.lstrip().startswith("---"):
        parts = body.split("---", 2)
        if len(parts) == 3:
            body = parts[2]
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    lines = [ln for ln in body.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")
             and not ln.strip().startswith("project:")]
    return len(lines) == 0


def main() -> int:
    root = resolve_vault()
    if root is None:
        print_unresolved_hint("lint.py")
        return 2
    if not root.is_dir():
        print(f"ERROR: vault が存在しません: {root}")
        return 2

    def content_files():
        for d in CONTENT_DIRS:
            p = root / d
            if p.is_dir():
                yield from p.glob("*.md")

    def load_ignore() -> set:
        f = root / "meta" / "lint-ignore.txt"
        if not f.exists():
            return set()
        out = set()
        for ln in read(f).splitlines():
            s = ln.strip()
            if s and not s.startswith("#"):
                out.add(s)
        return out

    valid = {p.stem for p in content_files()}
    ignore = load_ignore()
    referenced = set()
    broken = []          # 要対応
    broken_known = []    # 既知・無視

    idx = root / "meta" / "index.md"
    scan = list(content_files()) + ([idx] if idx.exists() else [])

    for f in scan:
        # index.md は index.py が全ページを機械的に列挙して作る。これを被リンク集合に
        # 混ぜると全ページが必ず「参照済み」になり、孤立ページ検出が恒久的に 0 件になる。
        # 赤リンク（index が指す先が実在しない）は見たいので、走査自体からは外さない。
        from_index = (f == idx)
        for m in LINK_RE.finditer(read(f)):
            tgt = link_target(m.group(1))
            if not tgt:
                continue
            if not from_index:
                referenced.add(tgt)
            if tgt not in valid:
                rec = (f.relative_to(root).as_posix(), tgt)
                (broken_known if tgt in ignore else broken).append(rec)

    orphans = sorted(p.relative_to(root).as_posix()
                     for p in content_files() if p.stem not in referenced)

    empties = sorted(p.relative_to(root).as_posix()
                     for p in root.rglob("*.md")
                     if ".obsidian" not in p.parts and p.stat().st_size == 0)

    fm_bad = []
    for p in content_files():
        block = frontmatter_block(read(p))
        rel = p.relative_to(root).as_posix()
        if block is None:
            fm_bad.append((rel, "先頭が --- でない / frontmatter欠落"))
            continue
        missing = [k for k in REQUIRED_FM if not has_fm_key(block, k)]
        if missing:
            fm_bad.append((rel, "欠落: " + " ".join(k + ":" for k in missing)))

    inbox = root / "inbox"
    inbox_files = sorted(inbox.glob("*.md")) if inbox.is_dir() else []

    # ingest が見るのは *.md だけなので、非 md は放置すると黙って取り込まれない。
    # convert_inbox.py に渡すべき残骸として明示的に検出する。
    # フォルダも同様に対象外（convert_inbox.py も inbox 直下のファイルしか見ない）なので、
    # 黙って沈まないよう末尾 / を付けて併せて報告する。
    def inbox_unconverted():
        if not inbox.is_dir():
            return []
        out = []
        for p in inbox.iterdir():
            if p.name.startswith("."):
                continue
            if p.is_dir():
                out.append(p.name + "/")
            elif p.suffix.lower() != ".md":
                out.append(p.name)
        return sorted(out)

    inbox_raw = inbox_unconverted()

    def _is_stub(f):
        return f.stat().st_size == 0 or is_stub(read(f))

    def _before_today(f):
        m = DATE_RE.match(f.name)
        return bool(m) and m.group(1) < TODAY

    inbox_stub_old = [f.name for f in inbox_files if _is_stub(f) and _before_today(f)]
    inbox_stub_today = [f.name for f in inbox_files if _is_stub(f) and not _before_today(f)]
    inbox_real = [f.name for f in inbox_files if not _is_stub(f)]

    def section(title, items, fmt):
        print(f"\n## {title}: {len(items)}")
        for it in items:
            print("  - " + fmt(it))

    print("=" * 60)
    print(f"LLM-Wiki lint  (root: {root})")
    print(f"content pages: {len(valid)}")
    print("=" * 60)

    section("赤リンク（要対応）", broken, lambda x: f"{x[1]}  ← {x[0]}")
    section("既知の赤リンク（無視リスト・将来ページ化予定）", broken_known,
            lambda x: f"{x[1]}  ← {x[0]}")
    section("孤立ページ（被リンクなし）", orphans, str)
    section("空ファイル(0byte)", empties, str)
    section("frontmatter 問題", fm_bad, lambda x: f"{x[0]}  … {x[1]}")
    section("inbox 未変換（非md・末尾 / はフォルダ。convert_inbox.py を実行）", inbox_raw, str)
    section("inbox 未処理（中身あり）", inbox_real, str)
    section("inbox 空スタブ・過去日（要対応）", inbox_stub_old, str)
    section("inbox 空スタブ・当日（想定内・Stopフックが翌日掃除）", inbox_stub_today, str)

    total = (len(broken) + len(orphans) + len(empties)
             + len(fm_bad) + len(inbox_real) + len(inbox_stub_old) + len(inbox_raw))
    print("\n" + "=" * 60)
    print("OK: 問題は見つかりませんでした ✔" if total == 0
          else f"検出合計: {total} 件 — 上記を修正してください")
    print("=" * 60)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meta/index.md と meta/keywords.md を各ページから自動生成する.

現行の「手書き index」のドリフト（赤リンク・記載漏れ）を根治するための生成器。

- `meta/index.md`    : frontmatter の genre / summary を読み、genre 別に一覧化する。
                       手書きの1行説明は summary に一元化する。
- `meta/keywords.md` : frontmatter の tags と本文見出しを「語 → ページ」へ反転した索引。
                       index.md に載るのはページ名と summary だけなので、別名・略語・
                       エラーメッセージからページへ辿れない。query の grep 頼みを減らす。

どちらも手書き禁止・毎回全書き換え（差分マージしない＝ドリフトしようがない）。

vault ルートは argv[1] → 環境変数の順で解決。
  例: python index.py "D:/資料/LLM-Wiki"
"""
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault import print_unresolved_hint, resolve_vault  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TODAY = datetime.now().strftime("%Y-%m-%d")
CONTENT_DIRS = ["concepts", "pages", "notes", "qa"]

GENERATED_BY = (
    "> このファイルは lint スキル（`/llm-wiki:lint`）が `scripts/index.py` で"
    "自動生成します。**手で編集しないでください。**"
)

# --- keywords.md のチューニング定数 -------------------------------------------
# 1つの語にぶら下げるページ数の上限。`wpf`（56ページ）のような大分類は全件並べても
# 絞り込めず、ファイルが膨らむだけ。超過分は件数だけ示して index.md / genre 側に送る。
KEYWORD_MAX_PAGES = 4
# 短すぎる語は grep のノイズになるだけなので落とす。
KEYWORD_MIN_LEN = 2

HEADING_RE = re.compile(r"^#{2,}\s+(.+?)\s*$", re.M)
# 見出し先頭の採番（`1. ` `2) ` `第3章 `）を落とす
ENUM_PREFIX_RE = re.compile(r"^(?:第?\d+[.)、章節]\s*)+")
# 見出しから拾うのは「識別子らしい語」だけに絞る。
# 実データ（186ページ）で全見出し 460 語を採ると 36KB になるが、中身は「確認方法」
# 「例外」「関連画面」といった節ラベルばかりで検索語として役に立たない。一方
# `TENMST` `ProcessTmjbfil` `runtimeconfig.json` のような識別子は、ページ名にも
# tags にも出ないのに検索されるため拾う価値がある。判定は「英数字で始まり、
# 日本語が2文字以下」— 節ラベルはほぼ日本語主体なのでこれで分離できる。
IDENT_HEAD_RE = re.compile(r"^[0-9A-Za-z]")
JP_RE = re.compile(r"[ぁ-んァ-ヶ一-龥]")
IDENT_MAX_JP = 2


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="cp932", errors="replace")


def split_frontmatter(text: str):
    """(frontmatterブロック, 本文) を返す。frontmatter が無ければ ("", text)。"""
    if not text.lstrip().startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    return parts[1], parts[2]


def parse_frontmatter(block: str) -> dict:
    """簡易 key: value パース（外部YAML非依存）。"""
    out = {}
    for ln in block.splitlines():
        m = re.match(r"\s*([A-Za-z_]+)\s*:\s*(.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def parse_tags(block: str) -> list:
    """tags を取り出す。インライン `[a, b]` とブロック `- a` の両方を受ける。

    規約はインライン形式だが、Obsidian 側で編集するとブロック形式になることがある。
    片方しか読めないと「タグを書いたのに索引に出ない」という無言の欠落になる。
    """
    m = re.search(r"^\s*tags\s*:\s*(.*)$", block, re.M)
    if not m:
        return []

    def split_items(s):
        return [t.strip().strip('"').strip("'") for t in s.split(",") if t.strip()]

    inline = m.group(1).strip()
    if inline.startswith("["):
        return split_items(inline.strip("[]"))
    if inline:                                   # `tags: a, b` のような素の羅列
        return split_items(inline)

    out = []                                     # ブロック形式: 次行から `- x`
    for ln in block[m.end():].splitlines():
        if not ln.strip():
            continue
        item = re.match(r"\s*-\s+(.*)$", ln)
        if not item:
            break                                # 次のキーに入ったので終了
        out.append(item.group(1).strip().strip('"').strip("'"))
    return out


def clean_heading(raw: str) -> str:
    """見出しを索引語に均す。markdown 装飾・採番・末尾の日付註記を落とす。"""
    s = re.sub(r"`([^`]*)`", r"\1", raw)          # `code` -> code
    s = re.sub(r"\*\*?([^*]*)\*\*?", r"\1", s)    # **強調** -> 強調
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)     # [[link]] -> link
    s = ENUM_PREFIX_RE.sub("", s)
    s = re.sub(r"\s*（[^）]*\d{4}-\d{2}-\d{2}[^）]*）\s*$", "", s)
    return s.strip(" 　:：-—")


def is_identifier(term: str) -> bool:
    """識別子らしい語か（テーブル名・クラス名・ファイル名・エラーコード等）。"""
    return (len(term) >= KEYWORD_MIN_LEN
            and bool(IDENT_HEAD_RE.match(term))
            and len(JP_RE.findall(term)) <= IDENT_MAX_JP)


def collect(vault: Path):
    """全ページを1回だけ読み、index 用と keywords 用の材料をまとめて集める。"""
    groups = {}          # genre -> [(ページ名, summary)]
    tag_map = {}         # tag -> {ページ名}
    head_map = {}        # 見出し語 -> {ページ名}
    total = 0

    for d in CONTENT_DIRS:
        base = vault / d
        if not base.is_dir():
            continue
        for p in sorted(base.glob("*.md")):
            fm_block, body = split_frontmatter(read(p))
            fm = parse_frontmatter(fm_block)
            groups.setdefault(fm.get("genre") or "未分類", []).append(
                (p.stem, fm.get("summary") or "")
            )
            total += 1

            for t in parse_tags(fm_block):
                if len(t) >= KEYWORD_MIN_LEN:
                    tag_map.setdefault(t, set()).add(p.stem)

            for raw in HEADING_RE.findall(body):
                h = clean_heading(raw)
                if is_identifier(h) and not h.isdigit():
                    head_map.setdefault(h, set()).add(p.stem)

    return groups, tag_map, head_map, total


def keyword_lines(mapping: dict) -> list:
    """`- 語 — [[A]], [[B]]` の行に整形する。並びは名前順で安定させる。

    出現ページ数での足切りはしない。節ラベルは is_identifier で構造的に除いてあり、
    残った識別子は「多くのページに出る = よく使うテーブル名/クラス名」なので、
    頻度で落とすと最も検索されるものから消えてしまう。
    """
    lines = []
    for term in sorted(mapping):
        pages = sorted(mapping[term])
        shown = pages[:KEYWORD_MAX_PAGES]
        links = ", ".join(f"[[{n}]]" for n in shown)
        rest = len(pages) - len(shown)
        if rest > 0:
            links += f" …他 {rest} 件"
        lines.append(f"- {term} — {links}")
    return lines


def build_index(groups: dict) -> str:
    lines = [
        "# Wiki Index",
        "",
        f"最終更新: {TODAY}",
        "",
        GENERATED_BY,
        "> 1行説明は各ページ frontmatter の `summary:` を編集してください。",
        "",
    ]
    for genre in sorted(groups):
        lines += [f"## {genre}", ""]
        for name, summary in sorted(groups[genre]):
            lines.append(f"- [[{name}]]" + (f" — {summary}" if summary else ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_keywords(tag_map: dict, head_map: dict):
    tag_lines = keyword_lines(tag_map)
    head_lines = keyword_lines(head_map)
    lines = [
        "# Wiki Keywords",
        "",
        f"最終更新: {TODAY}",
        "",
        GENERATED_BY,
        "> 語を増やすには各ページ frontmatter の `tags:` と本文の見出しを編集してください。",
        "",
        "検索の入口。**語からページを引く**ための索引で、ページの一覧は `index.md` にある。",
        f"1語あたり最大 {KEYWORD_MAX_PAGES} ページまで載せる（超過分は件数のみ）。",
        "",
        "## tags（各ページが明示した語）",
        "",
    ]
    lines += tag_lines or ["_（tags が1つもありません）_"]
    lines += [
        "",
        "## 識別子（本文の見出しから機械抽出）",
        "",
        "テーブル名・クラス名・ファイル名など、ページ名にも tags にも出ないが"
        "検索されうる語。`確認方法` のような節ラベル（日本語主体の見出し）は除外している。",
        "",
    ]
    lines += head_lines or ["_（抽出できる識別子がありません）_"]
    return "\n".join(lines).rstrip() + "\n", len(tag_lines), len(head_lines)


def main() -> int:
    vault = resolve_vault()
    if vault is None:
        print_unresolved_hint("index.py")
        return 2
    if not vault.is_dir():
        print(f"ERROR: vault が存在しません: {vault}")
        return 2

    groups, tag_map, head_map, total = collect(vault)

    meta = vault / "meta"
    meta.mkdir(parents=True, exist_ok=True)

    idx = meta / "index.md"
    idx.write_text(build_index(groups), encoding="utf-8")
    print(f"index.md を再生成しました: {idx}  （{total} ページ / {len(groups)} genre）")

    kw = meta / "keywords.md"
    text, n_tag, n_head = build_keywords(tag_map, head_map)
    kw.write_text(text, encoding="utf-8")
    print(f"keywords.md を再生成しました: {kw}  （tag {n_tag} 語 / 見出し {n_head} 語）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

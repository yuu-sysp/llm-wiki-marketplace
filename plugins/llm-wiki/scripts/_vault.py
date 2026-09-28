#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vault ルート解決と inbox 判定の共通ヘルパー.

vault ルートの優先順位:
  1. コマンドライン引数 argv[1]
  2. 環境変数 CLAUDE_PLUGIN_OPTION_VAULT_ROOT（プラグイン userConfig 由来）
  3. 環境変数 LLM_WIKI_VAULT_ROOT
どれも無ければ None を返す。

inbox の「中身なしスタブか」「未処理として残っているか」の判定も、lint・Stopフック・
SessionStart の3箇所で同じでなければ報告が食い違うため、ここに1つだけ置く。
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path

DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def resolve_vault(argv_index: int = 1):
    if len(sys.argv) > argv_index and sys.argv[argv_index].strip():
        return Path(sys.argv[argv_index]).expanduser()
    for env in ("CLAUDE_PLUGIN_OPTION_VAULT_ROOT", "LLM_WIKI_VAULT_ROOT"):
        v = os.environ.get(env)
        if v and v.strip():
            return Path(v).expanduser()
    return None


def print_unresolved_hint(script: str = "スクリプト") -> None:
    """vault 未解決時の対処を出し切る.

    実運用で詰まる原因はほぼ 2 つ（userConfig が空 / Claude Code を再起動していない）。
    ここで案内しないとユーザーは「Vault が未設定」とだけ見えて手が止まる。
    """
    print("ERROR: vault ルートが解決できません（引数・userConfig・環境変数すべて空）。")
    print("  対処 1: Claude Code で /plugin → llm-wiki の vault_root に保存先を設定 → /reload-plugins")
    print("          CLI なら: claude plugin install llm-wiki@llm-wiki-marketplace "
          '--config "vault_root=<path>"')
    print("  対処 2: 設定済みなら Claude Code を完全終了して再起動")
    print("          （起動中のセッションには userConfig も環境変数も反映されない）")
    print(f'  対処 3: 単発実行なら引数で明示 : python {script} "<vault path>"')


# ---------------------------------------------------------------- inbox 判定

def read_text(p: Path) -> str:
    """日本語 vault は cp932 のファイルが混ざるので順に試す。"""
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="cp932", errors="replace")


def split_frontmatter(text: str):
    """(frontmatterブロック, 本文) を返す。frontmatter が無ければ (None, text)。

    lint（必須キー判定）・index（genre/summary/tags）・inbox 判定で同じ切り方をしないと、
    同じページが片方では frontmatter あり、片方ではなしに見える。
    """
    if not text.lstrip().startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    return parts[1], parts[2]


FENCE_RE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def strip_fences(text: str) -> str:
    """フェンスコード（``` / ~~~）を消す（行数は保つ）。

    規約はコード例を含めるよう求めるため、bash の `[[ -f x ]]` や Python の `## コメント` が
    本文に普通に出る。これをリンクや見出しとして拾うと赤リンク・索引ノイズになる。
    """
    return FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def strip_code(text: str) -> str:
    """フェンスコードとインラインコードを消す（リンク走査用）。"""
    return INLINE_CODE_RE.sub("", strip_fences(text))


def is_stub(text: str) -> bool:
    """frontmatter・見出し・project行・HTMLコメント・空行だけなら中身なしスタブ。

    Stop フックが毎日作る当日の足場がこれ。誰も追記しなければスタブのまま残る。
    """
    _, body = split_frontmatter(text)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    lines = [ln for ln in body.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")
             and not ln.strip().startswith("project:")]
    return len(lines) == 0


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def is_before_today(name: str) -> bool:
    """ファイル名の日付プレフィックスが今日より前か（プレフィックス無しは False）。"""
    m = DATE_PREFIX_RE.match(name)
    return bool(m) and m.group(1) < today()


def read_hook_cwd() -> str:
    """フックの stdin JSON から cwd を取る。取れなければ ""。

    Claude Code は stdin へ UTF-8 で書くが、Windows の CPython は stdin をロケール既定
    （日本語環境では cp932）で読む。固定しないと非 ASCII の cwd が化けて
    `2026-08-27-MGMES02隗｣隱ｬ.md` のようなファイル名になり、cp932 にできないバイト列なら
    例外で cwd 自体を失って `-unknown.md` になる。
    端末から手で実行したときは stdin を待たない（固まるため）。
    """
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return ""
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        import json
        data = json.load(sys.stdin)
        return data.get("cwd", "") if isinstance(data, dict) else ""
    except Exception:
        return ""


def ensure_today_stub(vault: Path, cwd: str):
    """当日 `inbox/{date}-{project}.md` の足場を用意し、そのパスを返す（失敗時 None）。

    SessionStart と Stop の両方から呼ぶ。Stop だけだと最初の応答が終わるまでファイルが無く、
    「既存に追記するだけ」という蓄積方針と食い違う。既存ファイルには触らない。
    """
    project = Path(cwd).name if cwd else "unknown"
    date = today()
    inbox = vault / "inbox"
    outfile = inbox / f"{date}-{project}.md"
    try:
        inbox.mkdir(parents=True, exist_ok=True)
        if not outfile.exists():
            with open(outfile, "x", encoding="utf-8") as f:     # 並行セッションとの競合は x で弾く
                f.write(f"# {date} — {project}\n\n")
                f.write(f"project: `{cwd}`\n\n")
                f.write("## 学んだこと・解決したこと\n\n")
                f.write("<!-- この下にClaude Codeが追記します -->\n\n")
    except FileExistsError:
        pass
    except Exception:
        return None
    return outfile


def pending_inbox(vault: Path) -> list:
    """未処理として残っている inbox の項目を返す。

    「未処理」= 中身のある .md ／ 非 md（未変換）／ フォルダ（対象外）。
    中身なしスタブは、追記されていない当日分なので未処理に数えない。
    返すのは (パス, 日付) のリスト。日付はファイル名の日付プレフィックス優先、
    無ければ更新時刻（自動蓄積分は追記で mtime が進むためプレフィックスを正とする）。
    """
    inbox = vault / "inbox"
    if not inbox.is_dir():
        return []

    out = []
    for p in sorted(inbox.iterdir()):
        if p.name.startswith("."):
            continue
        try:
            if p.is_file() and p.suffix.lower() == ".md":
                if p.stat().st_size == 0 or is_stub(read_text(p)):
                    continue
            m = DATE_PREFIX_RE.match(p.name)
            if m:
                day = m.group(1)
            else:
                day = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
            out.append((p, day))
        except Exception:
            continue                     # 読めない1件で全体を止めない
    return out

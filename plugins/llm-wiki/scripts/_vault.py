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


def is_stub(text: str) -> bool:
    """frontmatter・見出し・project行・HTMLコメント・空行だけなら中身なしスタブ。

    Stop フックが毎日作る当日の足場がこれ。誰も追記しなければスタブのまま残る。
    """
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

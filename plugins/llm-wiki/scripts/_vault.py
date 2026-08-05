#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vault ルート解決の共通ヘルパー.

優先順位:
  1. コマンドライン引数 argv[1]
  2. 環境変数 CLAUDE_PLUGIN_OPTION_VAULT_ROOT（プラグイン userConfig 由来）
  3. 環境変数 LLM_WIKI_VAULT_ROOT
どれも無ければ None を返す。
"""
import os
import sys
from pathlib import Path


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

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

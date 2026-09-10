#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""発行前チェック: version の整合と bump 忘れを止める.

プラグインのキャッシュは version 単位で作られるため、中身を直しても version が
据え置きだと利用者側は古いコードのまま更新されない（実際 v0.1.0 で発生した）。
publish.bat から呼び、次の 2 つを機械的に検査する。

  1. plugins/llm-wiki/.claude-plugin/plugin.json と .claude-plugin/marketplace.json の
     version が一致していること（宣言が2箇所あるためドリフトしやすい）
  2. plugins/ 配下に発行済み（origin/master）との差分があるなら version が上がっていること

終了コード: 0 = 発行してよい / 1 = 問題あり
"""
import json
import subprocess
import sys
from pathlib import Path

PLUGIN_JSON = "plugins/llm-wiki/.claude-plugin/plugin.json"
MARKET_JSON = ".claude-plugin/marketplace.json"
PLUGIN_DIR = "plugins"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def git(root: Path, *args):
    """(exit_code, stdout) を返す。git が無い/失敗しても例外にしない。"""
    try:
        r = subprocess.run(["git", "-C", str(root), *args],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        return r.returncode, (r.stdout or "")
    except Exception:
        return 1, ""


def marketplace_version(text: str) -> str:
    for p in json.loads(text).get("plugins", []):
        if p.get("name") == "llm-wiki":
            return p.get("version", "")
    return ""


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    plugin_v = json.loads((root / PLUGIN_JSON).read_text(encoding="utf-8"))["version"]
    market_v = marketplace_version((root / MARKET_JSON).read_text(encoding="utf-8"))

    if plugin_v != market_v:
        print("[NG] version が一致しません:")
        print(f"       {PLUGIN_JSON} = {plugin_v}")
        print(f"       {MARKET_JSON} = {market_v}")
        print("     両方を同じ値に揃えてから発行してください。")
        return 1

    code, published = git(root, "show", "origin/master:" + PLUGIN_JSON)
    if code != 0:
        print(f"[OK] version {plugin_v}（発行済み版と比較できないため bump 判定はスキップ）")
        return 0

    published_v = json.loads(published)["version"]
    changed = git(root, "diff", "--quiet", "origin/master", "--", PLUGIN_DIR)[0] != 0

    if changed and published_v == plugin_v:
        print(f"[NG] {PLUGIN_DIR}/ に発行済み（origin/master）との差分があるのに "
              f"version が {plugin_v} のままです。")
        print("     version 据え置きだと利用者のキャッシュが更新されず、古いコードが動き続けます。")
        print(f"     次を両方書き換えてください: {PLUGIN_JSON} / {MARKET_JSON}")
        return 1

    if changed:
        print(f"[OK] version {published_v} -> {plugin_v}")
    else:
        print(f"[OK] version {plugin_v}（plugins/ に発行済みとの差分なし）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

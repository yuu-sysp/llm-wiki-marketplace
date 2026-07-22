---
name: query
description: LLM Wiki を検索して統合回答する。index→genre→wikilink 2ホップ→grep の段階検索で関連ページを集め、出典付きで回答する。「wiki を検索」「wiki query」で起動。
---

# LLM Wiki: query（検索・統合回答）

## 検索戦略（段階的・上から順に）

1. `meta/index.md` を読み、関連しそうな genre / ページを 1〜5 件に絞る。
2. 候補ページを並行 Read。`[[リンク]]` を**最大2ホップ**まで辿る（同ホップはまとめて読む）。
3. 不足時のみ grep フォールバック（同義語・略語も試す）。
4. 出典付きで統合回答する:
   - 事実・数値は `[[ページ名]]` / `[[sources/...]]` / URL を添える
   - 矛盾は無理に一本化せず両論を示す
   - Wiki に無い知識は「未記載」と明示する
5. 参照したページを末尾に列挙する。

## 保存判断（任意）

- 新規の視点・横断的知見が出たら `save` 相当でページ化を検討（decision-rules.md）。
- 単なる既存の組合せなら保存しない。

規約は `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/conventions.md` を参照。

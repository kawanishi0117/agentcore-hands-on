# main.py
"""
AgentCore メインモジュール
ナレッジベース検索ツール付きのエージェントを構築
"""
from strands import Agent
from strands.models import BedrockModel

# ツールをインポート
from tools import (
    list_knowledge_bases,
    search_knowledge_base,
    auto_search_knowledge_base,
)


# システムプロンプト: エージェントの振る舞いを定義
SYSTEM_PROMPT = """あなたは親切な日本語アシスタントです。

## 利用可能なツール
あなたはナレッジベース検索ツールを使って、社内ドキュメントやFAQを検索できます。

### ツールの使い分け
1. **list_knowledge_bases**: どんなナレッジベースがあるか確認したいとき
2. **search_knowledge_base**: 特定のナレッジベースを検索したいとき
3. **auto_search_knowledge_base**: どのKBを使うか迷ったとき（自動選択）

## 回答のルール
- ユーザーの質問に対して、まず適切なナレッジベースを検索してください
- 検索結果を元に、わかりやすく回答してください
- 検索結果がない場合は、その旨を伝えてください
- 不明な点は正直に「わかりません」と答えてください
"""


def build_agent():
    """ツール付きエージェントを構築"""
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="ap-northeast-1",
    )
    
    # ツールを登録
    tools = [
        list_knowledge_bases,
        search_knowledge_base,
        auto_search_knowledge_base,
    ]
    
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )


def main():
    agent = build_agent()
    print("REPL開始。終了は Ctrl+C か 'exit' / 'quit'。\n")

    while True:
        user = input("you> ").strip()
        if not user:
            continue
        if user.lower() in ("exit", "quit"):
            print("bye!")
            break

        # 毎ターン agent(...) を呼ぶだけで REPL になる
        assistant = agent(user)
        print(f"bot> {assistant}\n")


if __name__ == "__main__":
    main()

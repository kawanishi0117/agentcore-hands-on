# agentcore/main.py
"""
AgentCore メインモジュール
Gateway経由でナレッジベース検索ツールを使用するエージェント（IAM認証版）

このコードはAgentCore Runtime上で動作します。
ローカルでのテストには使用できません。
"""
import os
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client_with_iam


# Gateway設定（環境変数から取得）
GATEWAY_URL = os.environ.get(
    "GATEWAY_URL",
    ""  # デプロイ時に設定
)


# システムプロンプト
SYSTEM_PROMPT = """あなたは親切な日本語アシスタントです。

## 利用可能なツール
あなたはナレッジベース検索ツールを使って、社内ドキュメントやFAQを検索できます。

### ツールの使い分け
1. **ListKnowledgeBases**: どんなナレッジベースがあるか確認したいとき
2. **SearchKnowledgeBase**: 特定のナレッジベースを検索したいとき
3. **AutoSearchKnowledgeBase**: どのKBを使うか迷ったとき（自動選択）

## 回答のルール
- ユーザーの質問に対して、まず適切なナレッジベースを検索してください
- 検索結果を元に、わかりやすく回答してください
- 検索結果がない場合は、その旨を伝えてください
- 不明な点は正直に「わかりません」と答えてください
"""


def create_iam_transport(mcp_url: str):
    """IAM認証用のHTTPトランスポートを作成"""
    # AgentCore Runtime環境では自動的にIAM認証が適用される
    return streamablehttp_client_with_iam(mcp_url)


def get_full_tools_list(client):
    """ツール一覧を取得（ページネーション対応）"""
    more_tools = True
    tools = []
    pagination_token = None
    
    while more_tools:
        tmp_tools = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp_tools)
        
        if tmp_tools.pagination_token is None:
            more_tools = False
        else:
            more_tools = True
            pagination_token = tmp_tools.pagination_token
    
    return tools


def build_agent():
    """Gateway経由でツールを使用するエージェントを構築"""
    
    if not GATEWAY_URL:
        raise ValueError(
            "GATEWAY_URL環境変数が設定されていません。\n"
            "デプロイ時に設定してください。"
        )
    
    # MCPクライアント作成（IAM認証）
    mcp_client = MCPClient(lambda: create_iam_transport(GATEWAY_URL))
    
    # ツール一覧取得
    with mcp_client:
        tools = get_full_tools_list(mcp_client)
        print(f"利用可能なツール: {[tool.tool_name for tool in tools]}")
    
    # Bedrockモデル設定
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="ap-northeast-1",
    )
    
    # エージェント作成
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    ), mcp_client


def main():
    """
    ローカルREPLモード
    
    注意: IAM認証のGatewayはAgentCore Runtime環境でのみ動作します。
    ローカルでは動作しません。
    """
    print("❌ このエージェントはAgentCore Runtime環境でのみ動作します")
    print("ローカルでのテストはできません")
    print()
    print("デプロイ方法:")
    print("  agentcore deploy --name kb-search-agent --entry-point app.py")


if __name__ == "__main__":
    main()

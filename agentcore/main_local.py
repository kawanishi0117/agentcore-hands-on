#!/usr/bin/env python3
"""
ローカルREPLモード（IAM認証Gateway版）
AWS認証情報を使ってGatewayに接続
"""
import os
import boto3
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json


# Gateway設定
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")
REGION = "ap-northeast-1"


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


class IAMAuthTransport:
    """IAM認証用のHTTPトランスポート"""
    
    def __init__(self, url: str, region: str):
        self.url = url
        self.region = region
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
    
    def sign_request(self, method: str, body: str = None):
        """リクエストに署名"""
        headers = {'Content-Type': 'application/json'}
        
        request = AWSRequest(
            method=method,
            url=self.url,
            data=body,
            headers=headers
        )
        
        SigV4Auth(self.credentials, "bedrock-agentcore", self.region).add_auth(request)
        return dict(request.headers)
    
    def post(self, data: dict):
        """POSTリクエスト"""
        import requests
        
        body = json.dumps(data)
        headers = self.sign_request("POST", body)
        
        response = requests.post(self.url, headers=headers, data=body, timeout=30)
        return response


def create_iam_transport(mcp_url: str):
    """IAM認証用のトランスポートを作成"""
    # 注意: 実際のMCPクライアントとの統合には追加の実装が必要
    # ここでは簡易版を提供
    return IAMAuthTransport(mcp_url, REGION)


def get_tools_with_iam():
    """IAM認証でツール一覧を取得"""
    transport = create_iam_transport(GATEWAY_URL)
    
    # tools/list を呼び出し
    response = transport.post({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    })
    
    if response.status_code == 200:
        result = response.json()
        if "result" in result and "tools" in result["result"]:
            return result["result"]["tools"]
    
    return []


def build_agent():
    """エージェントを構築"""
    
    if not GATEWAY_URL:
        raise ValueError(
            "GATEWAY_URL環境変数が設定されていません。\n"
            "設定方法:\n"
            "  export GATEWAY_URL='https://your-gateway-id.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp'"
        )
    
    # AWS認証情報チェック
    session = boto3.Session()
    credentials = session.get_credentials()
    if not credentials:
        raise ValueError("AWS認証情報が見つかりません。aws configure を実行してください。")
    
    print("🔑 AWS認証情報を確認...")
    print(f"✅ Access Key: {credentials.access_key[:10]}...")
    
    # ツール一覧取得
    print("🔧 ツールを読み込み中...")
    tools_data = get_tools_with_iam()
    
    if not tools_data:
        raise ValueError("ツールの取得に失敗しました。Gateway URLとIAM権限を確認してください。")
    
    tool_names = [t['name'] for t in tools_data]
    print(f"✅ 利用可能なツール: {tool_names}")
    
    # Bedrockモデル設定
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name=REGION,
    )
    
    # 注意: 完全なMCP統合にはさらなる実装が必要
    # ここでは基本的なエージェント構築のみ
    print("\n⚠️  注意: 完全なMCP統合はAgentCore Runtime環境で動作します")
    print("ローカルでの完全なテストには制限があります")
    
    return None  # 実装中


def main():
    """REPLモード"""
    print("\n" + "=" * 70)
    print("🤖 ナレッジベース検索エージェント（ローカルテスト版）")
    print("=" * 70)
    print(f"Gateway URL: {GATEWAY_URL}")
    print()
    
    try:
        agent = build_agent()
        
        if agent is None:
            print("\n完全なREPLモードはAgentCore Runtime環境で使用してください")
            print()
            print("代わりに以下のテストスクリプトを使用できます:")
            print("  python test_local_iam.py")
            return
        
        print("REPL開始。終了は Ctrl+C か 'exit' / 'quit'。")
        print()
        
        while True:
            try:
                user = input("you> ").strip()
                if not user:
                    continue
                if user.lower() in ("exit", "quit"):
                    print("bye!")
                    break
                
                # エージェント実行
                assistant = agent(user)
                print(f"bot> {assistant}\n")
                
            except KeyboardInterrupt:
                print("\nbye!")
                break
            except Exception as e:
                print(f"❌ エラー: {e}\n")
    
    except ValueError as e:
        print(f"❌ エラー: {e}")
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")


if __name__ == "__main__":
    main()

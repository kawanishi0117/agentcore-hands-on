#!/usr/bin/env python3
"""
AgentCore Gateway接続テスト（OAuth認証）
kb-search-internal-dev Gatewayが正しく設定されているか確認
"""
import requests
import json
import sys
import os


# Gateway設定
GATEWAY_URL = "https://kb-search-internal-dev-blplmqcf9d.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp"

# OAuth認証情報（環境変数から取得）
CLIENT_ID = os.environ.get("GATEWAY_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GATEWAY_CLIENT_SECRET", "")
TOKEN_URL = os.environ.get("GATEWAY_TOKEN_URL", "")


def fetch_access_token(client_id, client_secret, token_url):
    """OAuthアクセストークンを取得"""
    response = requests.post(
        token_url,
        data=f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}",
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"❌ トークン取得失敗: {response.status_code}")
        print(response.text)
        return None


def call_mcp_method(gateway_url, access_token, method, params=None):
    """MCPメソッドを呼び出し"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": f"{method}-request",
        "method": method,
        "params": params or {}
    }
    
    response = requests.post(gateway_url, headers=headers, json=payload)
    return response


def test_list_tools():
    """利用可能なツール一覧を取得"""
    print("=" * 70)
    print("📋 テスト1: ツール一覧取得（tools/list）")
    print("=" * 70)
    
    # アクセストークン取得
    print("🔑 アクセストークンを取得中...")
    access_token = fetch_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
    
    if not access_token:
        return False, None
    
    print("✅ アクセストークン取得成功")
    
    # ツール一覧取得
    response = call_mcp_method(GATEWAY_URL, access_token, "tools/list")
    
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功")
        print(f"📦 レスポンス:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # ツール名を抽出
        if "result" in result and "tools" in result["result"]:
            tools = result["result"]["tools"]
            tool_names = [t['name'] for t in tools]
            print(f"\n利用可能なツール: {tool_names}")
            return True, access_token
        
        return True, access_token
    else:
        print(f"❌ HTTPエラー: {response.status_code}")
        print(response.text)
        return False, None


def test_call_tool(access_token, tool_name, arguments):
    """ツールを呼び出し"""
    print(f"\n{'=' * 70}")
    print(f"🔧 テスト: {tool_name}")
    print("=" * 70)
    
    response = call_mcp_method(
        GATEWAY_URL,
        access_token,
        "tools/call",
        {
            "name": tool_name,
            "arguments": arguments
        }
    )
    
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功")
        print(f"📦 レスポンス:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return True
    else:
        print(f"❌ HTTPエラー: {response.status_code}")
        print(response.text)
        return False


def main():
    """メイン処理"""
    print("\n🧪 AgentCore Gateway接続テスト（OAuth認証）")
    print(f"Gateway URL: {GATEWAY_URL}")
    print()
    
    # 環境変数チェック
    if not all([CLIENT_ID, CLIENT_SECRET, TOKEN_URL]):
        print("❌ OAuth認証情報が設定されていません")
        print()
        print("以下の環境変数を設定してください:")
        print("  export GATEWAY_CLIENT_ID='your-client-id'")
        print("  export GATEWAY_CLIENT_SECRET='your-client-secret'")
        print("  export GATEWAY_TOKEN_URL='https://...'")
        print()
        print("AWSコンソールのGateway詳細ページから取得できます")
        sys.exit(1)
    
    print(f"✅ OAuth設定確認済み")
    print(f"   Client ID: {CLIENT_ID[:10]}...")
    print(f"   Token URL: {TOKEN_URL}")
    print()
    
    # テスト1: ツール一覧取得
    test1_ok, access_token = test_list_tools()
    
    if not test1_ok or not access_token:
        print("\n❌ ツール一覧取得に失敗しました")
        sys.exit(1)
    
    # テスト2: ListKnowledgeBases
    test2_ok = test_call_tool(
        access_token,
        "ListKnowledgeBases",
        {}
    )
    
    # テスト3: SearchKnowledgeBase
    test3_ok = test_call_tool(
        access_token,
        "SearchKnowledgeBase",
        {
            "kbName": "product_docs",
            "query": "認証機能",
            "maxResults": 3
        }
    )
    
    # テスト4: AutoSearchKnowledgeBase
    test4_ok = test_call_tool(
        access_token,
        "AutoSearchKnowledgeBase",
        {
            "query": "ログイン方法",
            "maxResults": 3
        }
    )
    
    # 結果サマリー
    print("\n" + "=" * 70)
    if test1_ok and test2_ok and test3_ok and test4_ok:
        print("🎉 すべてのテストが成功しました！")
        print("=" * 70)
        print()
        print("✅ Gatewayは正しく設定されています")
        print("✅ Lambda関数との接続も正常です")
        print("✅ OAuth認証も正常に動作しています")
        print()
        print("次のステップ:")
        print("  1. agentcore/tools.py を更新")
        print(f"     GATEWAY_URL = '{GATEWAY_URL}'")
        print("  2. OAuth認証情報を環境変数に設定")
        print("  3. AgentCoreエージェントを起動してテスト")
        sys.exit(0)
    else:
        print("⚠️  一部のテストが失敗しました")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()

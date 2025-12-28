#!/usr/bin/env python3
"""
AgentCore Gateway接続テスト（IAM認証・MCPプロトコル対応）
kb-search-internal-dev Gatewayが正しく設定されているか確認
"""
import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
import sys


GATEWAY_ID = "kb-search-internal-dev-blplmqcf9d"
REGION = "ap-northeast-1"


def get_gateway_mcp_url():
    """Gateway IDからMCPエンドポイントURLを構築"""
    return f"https://{GATEWAY_ID}.gateway.bedrock-agentcore.{REGION}.amazonaws.com/mcp"


def sign_request(method, url, body=None):
    """IAM認証でリクエストに署名（SigV4）"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method=method,
        url=url,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'X-MCP-Protocol-Version': '2025-11-25'  # MCPプロトコルバージョン
        }
    )
    
    # bedrock-agentcore サービスで署名
    SigV4Auth(credentials, "bedrock-agentcore", REGION).add_auth(request)
    return dict(request.headers)


def call_mcp_tool(tool_name: str, arguments: dict):
    """
    Gateway経由でMCPツールを呼び出し（IAM認証）
    
    MCPプロトコル（JSON-RPC 2.0）形式でリクエスト
    """
    url = get_gateway_mcp_url()
    
    # MCP JSON-RPC 2.0 形式
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    body = json.dumps(payload)
    headers = sign_request("POST", url, body)
    
    try:
        response = requests.post(url, headers=headers, data=body, timeout=30)
        return response
    except Exception as e:
        print(f"❌ リクエストエラー: {e}")
        return None


def test_list_tools():
    """利用可能なツール一覧を取得"""
    print("=" * 70)
    print("📋 テスト0: ツール一覧取得（tools/list）")
    print("=" * 70)
    
    url = get_gateway_mcp_url()
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    body = json.dumps(payload)
    headers = sign_request("POST", url, body)
    
    # デバッグ: ヘッダーを確認
    print(f"リクエストヘッダー:")
    for key, value in headers.items():
        if 'Authorization' not in key:  # 認証情報は表示しない
            print(f"  {key}: {value}")
    
    try:
        response = requests.post(url, headers=headers, data=body, timeout=30)
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            print(f"📦 レスポンス:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # ツール名を抽出
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                print(f"\n利用可能なツール: {[t['name'] for t in tools]}")
            
            return True
        else:
            print(f"❌ HTTPエラー: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")
        return False


def test_list_knowledge_bases():
    """ListKnowledgeBases ツールのテスト"""
    print("\n" + "=" * 70)
    print("📋 テスト1: ListKnowledgeBases")
    print("=" * 70)
    
    try:
        response = call_mcp_tool("ListKnowledgeBases", {})
        
        if not response:
            return False
        
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
            
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")
        return False


def test_search_knowledge_base():
    """SearchKnowledgeBase ツールのテスト"""
    print("\n" + "=" * 70)
    print("🔍 テスト2: SearchKnowledgeBase")
    print("=" * 70)
    
    try:
        response = call_mcp_tool(
            "SearchKnowledgeBase",
            {
                "kbName": "product_docs",
                "query": "認証機能",
                "maxResults": 3
            }
        )
        
        if not response:
            return False
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            
            # MCPレスポンスから結果を抽出
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "")
                    print(f"📦 検索結果:")
                    print(text_content[:500])
            else:
                print(f"📦 レスポンス:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            
            return True
        else:
            print(f"❌ HTTPエラー: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")
        return False


def test_auto_search():
    """AutoSearchKnowledgeBase ツールのテスト"""
    print("\n" + "=" * 70)
    print("🤖 テスト3: AutoSearchKnowledgeBase")
    print("=" * 70)
    
    try:
        response = call_mcp_tool(
            "AutoSearchKnowledgeBase",
            {
                "query": "ログイン方法",
                "maxResults": 3
            }
        )
        
        if not response:
            return False
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            print(f"📦 レスポンス:")
            print(json.dumps(result, indent=2, ensure_ascii=False)[:500])
            
            return True
        else:
            print(f"❌ HTTPエラー: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")
        return False


def main():
    """メイン処理"""
    print("\n🧪 AgentCore Gateway接続テスト（IAM認証・MCPプロトコル）")
    print(f"Gateway ID: {GATEWAY_ID}")
    print(f"Region: {REGION}")
    print(f"MCP Endpoint: {get_gateway_mcp_url()}")
    print()
    
    # AWS認証情報チェック
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            print("❌ AWS認証情報が見つかりません")
            print("AWS CLIを設定してください: aws configure")
            sys.exit(1)
        print(f"✅ AWS認証情報: {credentials.access_key[:10]}...")
    except Exception as e:
        print(f"❌ AWS認証エラー: {e}")
        sys.exit(1)
    
    print()
    
    # テスト実行
    test0_ok = test_list_tools()
    
    if test0_ok:
        test1_ok = test_list_knowledge_bases()
        
        if test1_ok:
            test2_ok = test_search_knowledge_base()
            test3_ok = test_auto_search()
            
            if test2_ok and test3_ok:
                print("\n" + "=" * 70)
                print("🎉 すべてのテストが成功しました！")
                print("=" * 70)
                print()
                print("✅ Gatewayは正しく設定されています")
                print("✅ Lambda関数との接続も正常です")
                print()
                print("次のステップ:")
                print("  1. agentcore/tools.py を更新")
                print(f"     GATEWAY_ID = '{GATEWAY_ID}'")
                print("  2. AgentCoreエージェントを起動してテスト")
                sys.exit(0)
            else:
                print("\n⚠️  一部のテストが失敗しました")
                sys.exit(1)
        else:
            print("\n⚠️  ツール呼び出しテストが失敗しました")
            sys.exit(1)
    else:
        print("\n❌ Gateway接続テストが失敗しました")
        print()
        print("確認事項:")
        print("  1. Gateway IDが正しいか")
        print(f"     現在: {GATEWAY_ID}")
        print("  2. Gatewayが作成されているか（AWSコンソール）")
        print("  3. IAMユーザーにGateway呼び出し権限があるか")
        print("     必要な権限: bedrock-agentcore:InvokeGateway")
        sys.exit(1)


if __name__ == "__main__":
    main()

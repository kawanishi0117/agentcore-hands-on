#!/usr/bin/env python3
"""
IAM認証Gateway ローカルテスト
AWS認証情報を使ってGatewayを呼び出す
"""
import os
import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


# Gateway設定
GATEWAY_URL = os.environ.get(
    "GATEWAY_URL",
    ""  # 新しいGateway URLを設定
)
REGION = "ap-northeast-1"


def sign_request(method: str, url: str, body: str = None):
    """IAM認証でリクエストに署名（SigV4）"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # MCPプロトコルバージョンを複数の方法で指定
    headers = {
        'Content-Type': 'application/json',
        'X-MCP-Protocol-Version': '2025-11-25',
        'Mcp-Protocol-Version': '2025-11-25',
        'Accept': 'application/json, text/event-stream',
    }
    
    request = AWSRequest(
        method=method,
        url=url,
        data=body,
        headers=headers
    )
    
    # bedrock-agentcore サービスで署名
    SigV4Auth(credentials, "bedrock-agentcore", REGION).add_auth(request)
    return dict(request.headers)


def call_mcp_method(method: str, params: dict = None):
    """MCPメソッドを呼び出し（IAM認証）"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    body = json.dumps(payload)
    headers = sign_request("POST", GATEWAY_URL, body)
    
    response = requests.post(GATEWAY_URL, headers=headers, data=body, timeout=30)
    return response


def test_list_tools():
    """ツール一覧を取得"""
    print("=" * 70)
    print("📋 テスト1: ツール一覧取得（tools/list）")
    print("=" * 70)
    
    response = call_mcp_method("tools/list")
    
    # デバッグ: リクエストヘッダーを確認
    print(f"リクエストヘッダー（一部）:")
    print(f"  X-MCP-Protocol-Version: 2025-11-25")
    
    print(f"ステータスコード: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功")
        
        if "result" in result and "tools" in result["result"]:
            tools = result["result"]["tools"]
            tool_names = [t['name'] for t in tools]
            print(f"利用可能なツール: {tool_names}")
            print()
            print("ツール詳細:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool.get('description', '')}")
            return True
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
    else:
        print(f"❌ HTTPエラー: {response.status_code}")
        print(response.text)
        return False


def test_call_tool(tool_name: str, arguments: dict):
    """ツールを呼び出し"""
    print(f"\n{'=' * 70}")
    print(f"🔧 テスト: {tool_name}")
    print("=" * 70)
    
    response = call_mcp_method(
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
        
        # 結果を整形表示
        if "result" in result:
            tool_result = result["result"]
            if "content" in tool_result:
                content = tool_result["content"]
                if isinstance(content, list) and len(content) > 0:
                    text = content[0].get("text", "")
                    print(f"📦 結果:")
                    print(text[:1000])  # 最初の1000文字
                else:
                    print(json.dumps(tool_result, indent=2, ensure_ascii=False)[:1000])
            else:
                print(json.dumps(tool_result, indent=2, ensure_ascii=False)[:1000])
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])
        
        return True
    else:
        print(f"❌ HTTPエラー: {response.status_code}")
        print(response.text)
        return False


def main():
    """メイン処理"""
    print("\n🧪 IAM認証Gateway ローカルテスト")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Region: {REGION}")
    print()
    
    # Gateway URL チェック
    if not GATEWAY_URL:
        print("❌ GATEWAY_URL環境変数が設定されていません")
        print()
        print("設定方法:")
        print("  export GATEWAY_URL='https://your-gateway-id.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp'")
        print()
        return
    
    # AWS認証情報チェック
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            print("❌ AWS認証情報が見つかりません")
            print("AWS CLIを設定してください: aws configure")
            return
        print(f"✅ AWS認証情報: {credentials.access_key[:10]}...")
    except Exception as e:
        print(f"❌ AWS認証エラー: {e}")
        return
    
    print()
    
    # テスト実行
    test1_ok = test_list_tools()
    
    if not test1_ok:
        print("\n❌ ツール一覧取得に失敗しました")
        print()
        print("確認事項:")
        print("  1. Gateway URLが正しいか")
        print("  2. Gatewayが作成されているか（AWSコンソール）")
        print("  3. IAMユーザーにGateway呼び出し権限があるか")
        print("     必要な権限: bedrock-agentcore:InvokeGateway")
        return
    
    # ツール呼び出しテスト
    # ツール名はtools/listの結果から取得したものを使用
    # 形式: target-{target-name}___{tool-name}
    
    # list_kbs ツール呼び出し
    test2_ok = test_call_tool("target-quick-start-234b89___list_kbs", {})
    
    # kb_search ツール呼び出し
    test3_ok = test_call_tool(
        "target-quick-start-234b89___kb_search",
        {
            "kb_name": "product_docs",
            "query": "認証機能",
            "max_results": 3
        }
    )
    
    # auto_search ツール呼び出し（存在する場合）
    test4_ok = test_call_tool(
        "target-quick-start-234b89___auto_search",
        {
            "query": "ログイン方法",
            "max_results": 3
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
        print("✅ IAM認証も正常に動作しています")
        print()
        print("次のステップ:")
        print("  1. AgentCore Runtimeにデプロイ")
        print("     agentcore deploy --name kb-search-agent --entry-point app.py")
        print("  2. または、ローカルREPLモードを実行")
        print("     python main_local.py")
    else:
        print("⚠️  一部のテストが失敗しました")
        print("=" * 70)


if __name__ == "__main__":
    main()

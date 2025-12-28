# AgentCore Runtime から Gateway 経由でツールを使用する方法

このドキュメントでは、Amazon Bedrock AgentCore Runtime 上で動作するエージェントが、AgentCore Gateway 経由で外部ツール（Lambda関数）を呼び出す方法を解説します。

## 概要

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  AgentCore Runtime  │────▶│  AgentCore Gateway  │────▶│   Lambda Function   │
│    (エージェント)     │     │    (IAM認証)        │     │  (KB検索ツール)      │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
         │                           │                           │
         │  SigV4署名付き            │  MCPプロトコル            │  Bedrock KB
         │  HTTPリクエスト           │  (JSON-RPC 2.0)          │  検索API
         ▼                           ▼                           ▼
```

## アーキテクチャ

### コンポーネント

1. **AgentCore Runtime**: Strands Agentsフレームワークで構築されたエージェントをホスト
2. **AgentCore Gateway**: IAM認証でツールへのアクセスを制御するMCPゲートウェイ
3. **Lambda Function**: 実際のツールロジック（ナレッジベース検索など）を実装

### 認証フロー

1. エージェントがGatewayにリクエストを送信
2. リクエストはSigV4で署名（`bedrock-agentcore`サービス）
3. GatewayがIAM認証を検証
4. 認証成功後、GatewayがLambda関数を呼び出し

## 実装

### 1. Lambda関数（ツール実装）

```python
# kbquery/lambda_function.py
def lambda_handler(event, context):
    """
    AgentCore Gateway からの呼び出しを処理
    
    イベント形式:
    {
        "toolName": "kb_search",
        "input": {"kb_name": "...", "query": "..."}
    }
    """
    tool_name = event.get("toolName")
    args = event.get("input", {})
    
    if tool_name == "kb_search":
        result = search_knowledge_base(args)
    elif tool_name == "list_kbs":
        result = list_knowledge_bases()
    else:
        return {"statusCode": 400, "body": "Unknown tool"}
    
    return {
        "statusCode": 200,
        "body": json.dumps(result, ensure_ascii=False)
    }
```

### 2. Gateway設定

Gatewayは以下の設定で作成:

```yaml
# Gateway設定
authorizerType: AWS_IAM
protocolConfiguration:
  mcp:
    supportedVersions:
      - "2025-11-25"
```

### 3. エージェント実装（AgentCore Runtime）

```python
# agentcore/main.py
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

GATEWAY_URL = "https://xxx.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp"
TOOL_PREFIX = "target-xxx___"  # Gatewayターゲット名

def sign_request(method: str, url: str, body: str = None) -> dict:
    """IAM認証でリクエストに署名（SigV4）"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    headers = {
        'Content-Type': 'application/json',
        'X-MCP-Protocol-Version': '2025-11-25',
        'Mcp-Protocol-Version': '2025-11-25',
        'Accept': 'application/json, text/event-stream',
    }
    
    request = AWSRequest(method=method, url=url, data=body, headers=headers)
    SigV4Auth(credentials, "bedrock-agentcore", "ap-northeast-1").add_auth(request)
    return dict(request.headers)

def call_mcp_method(method: str, params: dict = None) -> dict:
    """MCPメソッドを呼び出し"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    body = json.dumps(payload)
    headers = sign_request("POST", GATEWAY_URL, body)
    response = requests.post(GATEWAY_URL, headers=headers, data=body, timeout=30)
    return response.json()

def call_gateway_tool(tool_name: str, arguments: dict) -> str:
    """Gatewayのツールを呼び出し"""
    full_tool_name = f"{TOOL_PREFIX}{tool_name}"
    
    result = call_mcp_method("tools/call", {
        "name": full_tool_name,
        "arguments": arguments
    })
    
    # レスポンスをパース
    if "result" in result:
        content = result["result"].get("content", [])
        if content:
            text = content[0].get("text", "")
            parsed = json.loads(text)
            return parsed.get("body", text)
    
    return json.dumps(result)
```

## 重要なポイント

### 1. MCPプロトコルバージョン

Gatewayは特定のMCPプロトコルバージョンのみをサポートします。ヘッダーで明示的に指定が必要:

```python
headers = {
    'X-MCP-Protocol-Version': '2025-11-25',
    'Mcp-Protocol-Version': '2025-11-25',  # 両方指定推奨
}
```

### 2. ツール名のプレフィックス

Gatewayのツール名は `{ターゲット名}___{ツール名}` の形式:

```python
# 例: target-quick-start-234b89___kb_search
TOOL_PREFIX = "target-quick-start-234b89___"
full_tool_name = f"{TOOL_PREFIX}kb_search"
```

ツール名は `tools/list` で確認できます。

### 3. SigV4署名

AgentCore Gatewayへのリクエストは `bedrock-agentcore` サービスで署名:

```python
SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)
```

### 4. レスポンス形式

Lambda関数のレスポンスは以下の形式でラップされます:

```json
{
  "result": {
    "content": [
      {
        "text": "{\"statusCode\":200,\"body\":\"{...}\"}"
      }
    ]
  }
}
```

エージェント側でパースが必要です。

## デプロイ手順

### 1. Lambda関数のデプロイ

```bash
cd kbquery
./package.ps1  # または手動でzip作成
aws lambda update-function-code --function-name kb-search-function --zip-file fileb://function.zip
```

### 2. Gateway作成

```bash
agentcore gateway create \
  --name kb-search-gateway \
  --authorizer-type AWS_IAM
```

### 3. Gatewayターゲット追加

```bash
agentcore gateway add-target \
  --gateway-name kb-search-gateway \
  --target-name kb-search-target \
  --lambda-arn arn:aws:lambda:ap-northeast-1:xxx:function:kb-search-function
```

### 4. エージェントデプロイ

```bash
cd agentcore
agentcore launch --auto-update-on-conflict
```

### 5. テスト

```bash
agentcore invoke '{"prompt": "認証について検索して"}'
```

## トラブルシューティング

### エラー: "Unsupported MCP protocol version"

MCPプロトコルバージョンヘッダーが正しく設定されていません。

```python
# 両方のヘッダーを設定
headers = {
    'X-MCP-Protocol-Version': '2025-11-25',
    'Mcp-Protocol-Version': '2025-11-25',
}
```

### エラー: "Unknown tool"

ツール名にプレフィックスが付いていません。`tools/list` で正確なツール名を確認してください。

### エラー: "利用可能なツール: []"

Gatewayへの接続に問題があります。以下を確認:
- Gateway URLが正しいか
- IAM権限が設定されているか
- MCPプロトコルバージョンが正しいか

### ローカルテスト

ローカルでGateway接続をテストするには `test_local_iam.py` を使用:

```bash
cd agentcore
python test_local_iam.py
```

## ファイル構成

```
.
├── agentcore/
│   ├── app.py              # AgentCore Runtimeエントリーポイント
│   ├── main.py             # エージェント実装（Gateway呼び出し）
│   ├── requirements.txt    # 依存関係
│   └── test_local_iam.py   # ローカルテスト用
├── kbquery/
│   ├── lambda_function.py  # Lambda関数（ツール実装）
│   ├── kb_config.py        # ナレッジベース設定
│   └── model.smithy        # Smithyモデル定義
└── docs/
    └── AGENTCORE_GATEWAY_INTEGRATION.md  # このドキュメント
```

## 参考リンク

- [Amazon Bedrock AgentCore ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [Strands Agents](https://github.com/strands-agents/strands-agents)

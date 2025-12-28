# トラブルシューティングガイド

AgentCore Runtime + Gateway 連携で発生しやすい問題と解決方法をまとめています。

## よくある問題

### 1. "利用可能なツール: []" - ツールが取得できない

**症状**
```
Gateway URL: https://xxx.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp
利用可能なツール: []
```

**原因**
- MCPプロトコルバージョンが正しく指定されていない
- Gateway URLが間違っている
- IAM認証に失敗している

**解決方法**

1. MCPプロトコルバージョンヘッダーを両方指定:
```python
headers = {
    'X-MCP-Protocol-Version': '2025-11-25',
    'Mcp-Protocol-Version': '2025-11-25',
}
```

2. Gateway URLを確認:
```bash
agentcore gateway list
```

3. IAM権限を確認:
```bash
aws sts get-caller-identity
```

---

### 2. "Unsupported MCP protocol version: 2025-03-26"

**症状**
```
Error: Unsupported MCP protocol version: 2025-03-26
```

**原因**
- MCPライブラリのデフォルトバージョンがGatewayでサポートされていない
- Gatewayは `2025-11-25` のみサポート

**解決方法**

MCPライブラリを使わず、`requests`ライブラリで直接HTTPリクエストを送信:

```python
import requests

headers = {
    'Content-Type': 'application/json',
    'X-MCP-Protocol-Version': '2025-11-25',
    'Mcp-Protocol-Version': '2025-11-25',
}

response = requests.post(GATEWAY_URL, headers=headers, data=body)
```

---

### 3. "Unknown tool: kb_search"

**症状**
```
Error: Unknown tool: kb_search
```

**原因**
- ツール名にGatewayターゲットのプレフィックスが付いていない

**解決方法**

`tools/list` で正確なツール名を確認し、プレフィックスを追加:

```python
# tools/list の結果
# ['target-quick-start-234b89___kb_search', ...]

TOOL_PREFIX = "target-quick-start-234b89___"
full_tool_name = f"{TOOL_PREFIX}kb_search"
```

---

### 4. ImportError: cannot import name 'streamablehttp_client_with_iam'

**症状**
```
ImportError: cannot import name 'streamablehttp_client_with_iam' from 'mcp.client.streamable_http'
```

**原因**
- MCPライブラリのバージョンが古い、または該当関数が存在しない

**解決方法**

MCPライブラリを使わず、シンプルな`requests`ベースの実装に変更:

```python
# ❌ MCPライブラリを使用（問題あり）
from mcp.client.streamable_http import streamablehttp_client_with_iam

# ✅ requestsライブラリを使用（推奨）
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
```

---

### 5. TypeError: streamablehttp_client() got an unexpected keyword argument

**症状**
```
TypeError: streamablehttp_client() got an unexpected keyword argument 'http_client_factory'
```

**原因**
- MCPライブラリのAPIが変更された

**解決方法**

同上。`requests`ライブラリを使用する実装に変更。

---

### 6. Lambda関数のレスポンスがパースできない

**症状**
```
検索結果: {"statusCode":200,"body":"{...}"}
```

**原因**
- Lambda関数のレスポンスがネストされたJSON形式

**解決方法**

レスポンスを適切にパース:

```python
def call_gateway_tool(tool_name: str, arguments: dict) -> str:
    result = call_mcp_method("tools/call", {...})
    
    if "result" in result:
        content = result["result"].get("content", [])
        if content:
            text = content[0].get("text", "")
            # Lambda関数のレスポンスをパース
            parsed = json.loads(text)
            if "body" in parsed:
                return parsed["body"]
    
    return json.dumps(result)
```

---

## デバッグ方法

### CloudWatchログの確認

```bash
# 最新のログを確認
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-name}-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs]" \
  --since 30m

# リアルタイムでログを追跡
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-name}-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs]" \
  --follow
```

### ローカルテスト

`test_local_iam.py` を使用してGateway接続をテスト:

```bash
cd agentcore
python test_local_iam.py
```

期待される出力:
```
🧪 IAM認証Gateway ローカルテスト
Gateway URL: https://xxx.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp
✅ AWS認証情報: AKIAXXX...

======================================================================
📋 テスト1: ツール一覧取得（tools/list）
======================================================================
✅ 成功
利用可能なツール: ['target-xxx___list_kbs', 'target-xxx___kb_search', ...]
```

### Gateway設定の確認

```bash
# Gateway一覧
agentcore gateway list

# Gateway詳細
agentcore gateway describe --name {gateway-name}

# ターゲット一覧
agentcore gateway list-targets --gateway-name {gateway-name}
```

---

## 解決済みの問題パターン

### パターン1: MCPライブラリの互換性問題

**問題**: MCPライブラリの`streamablehttp_client_with_iam`関数が存在しない

**解決**: `requests`ライブラリ + SigV4署名で直接HTTPリクエストを送信

### パターン2: プロトコルバージョン不一致

**問題**: Gatewayがサポートするバージョンとクライアントのバージョンが異なる

**解決**: ヘッダーで明示的に`2025-11-25`を指定

### パターン3: ツール名の形式

**問題**: Gatewayのツール名は`{ターゲット名}___{ツール名}`の形式

**解決**: `tools/list`で正確なツール名を確認し、プレフィックスを追加

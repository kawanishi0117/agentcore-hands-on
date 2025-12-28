# AgentCore Runtime デプロイ手順（IAM認証Gateway版）

このエージェントはIAM認証のGatewayを使用するため、**AgentCore Runtime環境でのみ動作**します。

## 前提条件

1. **Gateway作成済み**
   - IAM認証を使用するGatewayが作成されていること
   - Gateway URLをメモしておく

2. **AgentCore CLIインストール済み**
   ```bash
   pip install bedrock-agentcore-cli
   ```

3. **AWS認証情報設定済み**
   ```bash
   aws configure
   ```

## デプロイ手順

### 1. Gateway URLを環境変数に設定

```powershell
# PowerShell
$env:GATEWAY_URL = "https://your-gateway-id.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp"
```

または、デプロイコマンドで直接指定：

```bash
agentcore deploy \
  --name kb-search-agent \
  --entry-point app.py \
  --runtime python3.10 \
  --region ap-northeast-1 \
  --env GATEWAY_URL=https://your-gateway-id.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp
```

### 2. デプロイ実行

```bash
cd agentcore

# デプロイ
agentcore deploy \
  --name kb-search-agent \
  --entry-point app.py \
  --runtime python3.10 \
  --region ap-northeast-1
```

### 3. デプロイ確認

```bash
# エージェント一覧を確認
agentcore list

# エージェント詳細を確認
agentcore describe --name kb-search-agent
```

### 4. エージェントを呼び出し

```bash
# CLIから呼び出し
agentcore invoke \
  --name kb-search-agent \
  --input "認証機能について教えて"

# または、AWS SDKから呼び出し
```

## IAMロールの設定

AgentCore Runtimeの実行ロールに以下の権限が必要です：

### 1. Gateway呼び出し権限

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeGateway"
      ],
      "Resource": "arn:aws:bedrock-agentcore:ap-northeast-1:*:gateway/your-gateway-id"
    }
  ]
}
```

### 2. Bedrock呼び出し権限

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
    }
  ]
}
```

## トラブルシューティング

### デプロイエラー

```
❌ Error: GATEWAY_URL not set
```

→ 環境変数を設定してください

### Gateway接続エラー

```
❌ Error: 403 Forbidden
```

→ 実行ロールにGateway呼び出し権限があるか確認してください

### ツール一覧取得エラー

```
❌ Error: No tools found
```

→ GatewayにLambdaターゲットが正しく設定されているか確認してください

## ローカルテストについて

IAM認証のGatewayは**AgentCore Runtime環境でのみ動作**します。

ローカルでテストする場合は以下の方法があります：

1. **Lambda関数を直接テスト**
   ```bash
   cd kbquery
   python test_local.py
   ```

2. **OAuth認証のGatewayを別途作成**
   - 開発用にOAuth認証のGatewayを作成
   - ローカルでテスト
   - 本番環境ではIAM認証のGatewayを使用

## 参考資料

- [AgentCore Runtime ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-runtime.html)
- [AgentCore Gateway ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-gateway.html)
- [IAM認証設定](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-iam.html)

# AgentCore Gateway経由でナレッジベース検索を使う手順

このドキュメントでは、Lambda関数をAgentCore Gateway経由で呼び出す設定手順を説明します。

## アーキテクチャ

```
AgentCore Agent (Strands)
    ↓ ツール呼び出し
AgentCore Gateway (MCP準拠)
    ↓ Smithyモデル
Lambda関数 (kbquery)
    ↓ Bedrock API
Knowledge Base
```

## 前提条件

- AWS CLIがインストール・設定済み
- Python 3.10以上
- 必要なAWS権限（Lambda、Bedrock、AgentCore Gateway）

## 手順

### 1. Lambda関数のデプロイ

```bash
# kbqueryディレクトリに移動
cd kbquery

# 依存関係をインストール
pip install -r requirements.txt -t .

# Lambda関数をパッケージング
zip -r function.zip . -x "*.pyc" "__pycache__/*" "*.git*"

# Lambda関数を作成（初回のみ）
aws lambda create-function \
  --function-name kbquery-function \
  --runtime python3.10 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --memory-size 512 \
  --region ap-northeast-1

# 既存の関数を更新する場合
aws lambda update-function-code \
  --function-name kbquery-function \
  --zip-file fileb://function.zip \
  --region ap-northeast-1
```

### 2. IAMロールの設定

Lambda実行ロールに以下のポリシーをアタッチ：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve",
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### 3. AgentCore Gatewayの作成

```bash
# Gatewayを作成
aws bedrock-agent create-gateway \
  --gateway-name kb-search-gateway \
  --description "ナレッジベース検索Gateway" \
  --region ap-northeast-1

# Gateway IDをメモ（出力から取得）
# 例: gtw-abc123def456
```

### 4. Gatewayにターゲットを追加

```bash
# Smithyモデルファイルをアップロード（S3経由）
aws s3 cp model.smithy s3://YOUR_BUCKET/models/kbquery-model.smithy

# Gatewayターゲットを作成
aws bedrock-agent create-gateway-target \
  --gateway-id gtw-abc123def456 \
  --target-name kb-search-lambda \
  --target-type LAMBDA \
  --lambda-configuration functionArn=arn:aws:lambda:ap-northeast-1:YOUR_ACCOUNT_ID:function:kbquery-function \
  --model-location s3://YOUR_BUCKET/models/kbquery-model.smithy \
  --region ap-northeast-1
```

### 5. AgentCore側の環境変数設定

```bash
# agentcoreディレクトリで環境変数を設定
export AGENTCORE_GATEWAY_ID=gtw-abc123def456
export AWS_REGION=ap-northeast-1
```

または `.env` ファイルを作成：

```bash
# agentcore/.env
AGENTCORE_GATEWAY_ID=gtw-abc123def456
AWS_REGION=ap-northeast-1
```

### 6. ローカルテスト

```bash
cd agentcore

# 依存関係をインストール
pip install -r requirements.txt

# REPLを起動
python main.py
```

REPLで以下のように質問：

```
you> 認証機能について教えて
```

エージェントが自動的にナレッジベースを検索して回答します。

### 7. AgentCore Runtimeへのデプロイ

```bash
cd agentcore

# AgentCore CLIでデプロイ
agentcore deploy \
  --name kb-search-agent \
  --entry-point app.py \
  --runtime python3.10 \
  --region ap-northeast-1
```

## トラブルシューティング

### Gateway IDが見つからない

```bash
# Gateway一覧を確認
aws bedrock-agent list-gateways --region ap-northeast-1
```

### Lambda関数が呼び出せない

- Lambda実行ロールの権限を確認
- Gatewayターゲットの設定を確認
- CloudWatch Logsでエラーログを確認

```bash
aws logs tail /aws/lambda/kbquery-function --follow
```

### ナレッジベースが見つからない

`kbquery/kb_config.py` でKB IDが正しく設定されているか確認：

```python
KNOWLEDGE_BASES = {
    "product_docs": {
        "id": "YOUR_KB_ID",  # ← ここを確認
        ...
    }
}
```

## 参考資料

- [AgentCore Gateway ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-gateway.html)
- [Smithy モデル仕様](https://smithy.io/2.0/index.html)
- [Bedrock Knowledge Base API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_Retrieve.html)

# クイックスタートガイド

AgentCore Runtime + Gateway でナレッジベース検索エージェントを構築する手順です。

## 前提条件

- AWS CLI 設定済み
- Python 3.10+
- AgentCore CLI インストール済み

```bash
pip install bedrock-agentcore-cli
```

## 手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd agentcore-hands-on
```

### 2. 仮想環境のセットアップ

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux

pip install -r agentcore/requirements.txt
```

### 3. Lambda関数のデプロイ

```bash
cd kbquery

# パッケージ作成
pip install -r requirements.txt -t .
zip -r function.zip . -x "*.pyc" -x "__pycache__/*"

# Lambda関数を更新（既存の場合）
aws lambda update-function-code \
  --function-name kb-search-function \
  --zip-file fileb://function.zip

cd ..
```

### 4. Gateway作成（初回のみ）

```bash
# Gateway作成
agentcore gateway create \
  --name kb-search-gateway \
  --authorizer-type AWS_IAM

# ターゲット追加
agentcore gateway add-target \
  --gateway-name kb-search-gateway \
  --target-name kb-search-target \
  --lambda-arn arn:aws:lambda:ap-northeast-1:xxx:function:kb-search-function
```

### 5. 環境変数の設定

```bash
cd agentcore

# .envファイルを作成
cp .env.template .env

# Gateway URLを設定
# GATEWAY_URL=https://xxx.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp
```

### 6. ローカルテスト

```bash
python test_local_iam.py
```

期待される出力:
```
🧪 IAM認証Gateway ローカルテスト
✅ AWS認証情報: AKIAXXX...
✅ 成功
利用可能なツール: ['target-xxx___list_kbs', ...]
🎉 すべてのテストが成功しました！
```

### 7. AgentCore Runtimeにデプロイ

```bash
agentcore launch --auto-update-on-conflict
```

### 8. エージェントをテスト

```bash
agentcore invoke '{"prompt": "認証について検索して"}'
```

期待される出力:
```json
{
  "result": "認証機能に関する情報を検索した結果、次のことがわかりました..."
}
```

## ファイル構成

```
.
├── agentcore/
│   ├── app.py              # エントリーポイント
│   ├── main.py             # エージェント実装
│   ├── requirements.txt    # 依存関係
│   ├── test_local_iam.py   # ローカルテスト
│   └── .env                # 環境変数
├── kbquery/
│   ├── lambda_function.py  # Lambda関数
│   ├── kb_config.py        # KB設定
│   └── requirements.txt    # Lambda依存関係
└── docs/
    ├── QUICKSTART.md       # このファイル
    ├── ARCHITECTURE.md     # アーキテクチャ
    ├── AGENTCORE_GATEWAY_INTEGRATION.md  # 詳細ガイド
    └── TROUBLESHOOTING.md  # トラブルシューティング
```

## 次のステップ

- [アーキテクチャ](./ARCHITECTURE.md) - システム構成の詳細
- [Gateway連携ガイド](./AGENTCORE_GATEWAY_INTEGRATION.md) - 実装の詳細
- [トラブルシューティング](./TROUBLESHOOTING.md) - 問題解決

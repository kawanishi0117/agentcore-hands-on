# AgentCore ナレッジベース検索エージェント

Gatント

## 機能

- **ListKnowledgeBases**: 利用可能なナレッジベース一覧を取得
ジベースを検索
- **AutoSearchKnowledgeBase**: クエリから最適索



トール


pip install -r requirements.txt
`

境変数の設定

#### 方法A: PowerShellスクリプトで設定

```hell
ps1
```

対話形式でOAuth認証情報を入力できます。



```powershe
# テンプレートをコピー
nv

入力
notepad .env
`

数：
- `GATEWAY_URL`: Gateway MCP エンドポイント（既に設定済み）

- `GATEWAY_CLIENT_SECRET`: OAuth クライアントシークレット
- `GATEWAY_TOKEN_URL`: OAuth トークンエンドポイント

###の取得方法

1. AWSコンソール → **Amazon Bedrock** → **AgentCore** → **Gateways**
を開く
3. **OAuth Configuration** セクションから以下をコピー：
 ID
   - Client Secret
   - Token Endpoint URL

## 使い方

###PLモード

```powershell
y
```

きます：

``
you> 認証機能について教えて
bot> [ナレッジベースを検索して回答]

you> どんなナレッジベースがある？
bot> [KB一覧を表示]

you> exit

l.io/)rotocoodelcontextptps://mCP プロトコル](ht[M- ts)
agenabs/strands-m/awsl//github.coents](https:[Strands Ag
- eway.html)tcore-gatide/agenrguk/latest/useedroccom/bmazon./docs.aws.as:/tpト](htway ドキュメンGateAgentCore 

- [## 参考資料```

 # このファイル
d          DME.mREAト
└── 数テンプレー # 環境変    mplate  ── .env.teスクリプト
├    # 環境変数設定nv.ps1   ── setup_e 依存関係
├xt    #s.tuirement
├── req本体 + REPLモード    # エージェント   n.py      ├── mai
ポイントuntime用エントリーgentCore R         # A  ── app.py   tcore/
├gen

```
aイル構成ファい

## 確認してくださいるかが稼働してewayURLが正しいか、GatGATEWAY_
```

→ edction refusConne
❌ 初期化エラー: ```way接続エラー

ate### Gください。

ます。再起動して能性がありれている可ンの有効期限が切アクセストーク
→ ```
403

❌ HTTPエラー: 得エラー

```
### ツール一覧取いか確認してください
ECRETが正しとCLIENT_ST_IDLIEN
```

→ C01ン取得失敗: 4``
❌ トーク
`取得エラー


### トークン トラブルシューティング
##
``ast-1
`n ap-northe
  --region3.10 `ytho--runtime ppy `
  -point app.  --entry
ent `b-search-ag --name kdeploy `
 core hell
agent

```powersimeへのデプロイCore Runt
### Agentbye!
```

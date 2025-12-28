# agentcore/main.py
"""
AgentCore メインモジュール
Gateway経由でナレッジベース検索ツールを使用するエージェント（IAM認証版）
短期記憶（STM）機能付き

このコードはAgentCore Runtime上で動作します。
"""
import os
import json
from typing import Optional, Any
import boto3
import requests  # type: ignore
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from strands import Agent, tool
from strands.models import BedrockModel
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent

# メモリクライアント（オプション）
try:
    from bedrock_agentcore.memory import MemoryClient
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("Warning: bedrock_agentcore.memory not available")


# Gateway設定（環境変数から取得）
GATEWAY_URL = os.environ.get(
    "GATEWAY_URL",
    "https://kb-search-internal-dev-blplmqcf9d.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp"
)
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# メモリ設定（yaml設定ファイルから自動取得）
# AgentCore Runtimeが環境変数 MEMORY_ID を自動設定する
MEMORY_ID = os.environ.get("MEMORY_ID", "kb_search_agent_mem-W9ODNgGzYW")

# ツール名のプレフィックス（Gatewayのターゲット名）
TOOL_PREFIX = "target-quick-start-234b89___"

# メモリクライアント初期化
memory_client = None
if MEMORY_AVAILABLE and MEMORY_ID:
    memory_client = MemoryClient(region_name=REGION)
    print(f"Memory enabled: {MEMORY_ID}")


# ========================================
# 短期記憶（STM）フック
# ========================================

class ShortTermMemoryHook(HookProvider):
    """
    セッション内の会話履歴を管理するフック
    
    - エージェント初期化時: 過去の会話を読み込んでコンテキストに追加
    - メッセージ追加時: 会話をメモリに保存
    """
    
    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        """エージェント起動時に過去の会話を読み込む"""
        if not memory_client or not MEMORY_ID:
            return
        
        # セッションIDを取得（デフォルト値付き）
        session_id = str(event.agent.state.get("session_id") or "default")
        
        try:
            # 直近10ターンの会話を取得（聞き返し対応のため多めに）
            turns = memory_client.get_last_k_turns(
                memory_id=MEMORY_ID,
                actor_id="anonymous",  # 認証なしなので固定
                session_id=session_id,
                k=10
            )
            
            if turns:
                # 会話履歴をフォーマット
                history_lines = []
                for turn in turns:
                    for msg in turn:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", {})
                        text = content.get("text", "") if isinstance(content, dict) else str(content)
                        history_lines.append(f"{role}: {text}")
                
                # システムプロンプトに追加
                if history_lines and event.agent.system_prompt:
                    context = "\n".join(history_lines)
                    event.agent.system_prompt = event.agent.system_prompt + f"\n\n## 直前の会話履歴\n{context}"
                    print(f"Loaded {len(turns)} conversation turns from memory")
        
        except Exception as e:
            print(f"Warning: Failed to load memory: {e}")
    
    def on_message_added(self, event: MessageAddedEvent) -> None:
        """メッセージをメモリに保存"""
        if not memory_client or not MEMORY_ID:
            return
        
        # セッションIDを取得（デフォルト値付き）
        session_id = str(event.agent.state.get("session_id") or "default")
        
        try:
            # 最新のメッセージを取得
            msg = event.agent.messages[-1]
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # contentがリストの場合はテキストを抽出
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                content = " ".join(text_parts)
            
            # メモリに保存
            memory_client.create_event(
                memory_id=MEMORY_ID,
                actor_id="anonymous",
                session_id=session_id,
                messages=[(str(content), str(role))]
            )
        
        except Exception as e:
            print(f"Warning: Failed to save to memory: {e}")
    
    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """フックを登録"""
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(MessageAddedEvent, self.on_message_added)


# システムプロンプト
SYSTEM_PROMPT = """あなたは親切な日本語アシスタントです。

## 利用可能なツール
あなたはナレッジベース検索ツールを使って、社内ドキュメントやFAQを検索できます。

### ツールの使い分け
1. **list_kbs**: どんなナレッジベースがあるか確認したいとき
2. **kb_search**: 特定のナレッジベースを検索したいとき（kb_nameとqueryを指定）
3. **auto_search**: どのKBを使うか迷ったとき（自動選択、queryのみ指定）

## 利用可能なナレッジベース
- product_docs: 認証機能マニュアル
- faq: サンプルドキュメント

## 回答のルール
- ユーザーの質問に対して、まず適切なナレッジベースを検索してください
- 検索結果を元に、わかりやすく回答してください
- 検索結果がない場合は、その旨を伝えてください
- 不明な点は正直に「わかりません」と答えてください

## 重要: 不明点は必ず確認する
- ユーザーの質問が曖昧な場合は、**検索する前に**具体的に聞き返してください
- 例: 「認証について教えて」→「ログイン認証、API認証、どちらについてお知りになりたいですか？」
- 複数の解釈ができる場合は、想定される選択肢を提示して確認してください
- 会話履歴を参照して、前回の質問や回答を踏まえて対応してください
"""


def sign_request(method: str, url: str, body: Optional[str] = None) -> dict:
    """IAM認証でリクエストに署名（SigV4）"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    if credentials is None:
        raise ValueError("AWS credentials not found")
    
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
    
    SigV4Auth(credentials, "bedrock-agentcore", REGION).add_auth(request)
    return dict(request.headers)


def call_mcp_method(method: str, params: Optional[dict] = None) -> dict:
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
    return response.json()


def get_gateway_tools() -> list:
    """Gatewayからツール一覧を取得"""
    try:
        result = call_mcp_method("tools/list")
        print(f"tools/list レスポンス: {json.dumps(result, ensure_ascii=False)[:500]}")
        
        if "result" in result and "tools" in result["result"]:
            return result["result"]["tools"]
        
        # エラーがあれば表示
        if "error" in result:
            print(f"tools/list エラー: {result['error']}")
        
        return []
    except Exception as e:
        print(f"tools/list 例外: {e}")
        return []


def call_gateway_tool(tool_name: str, arguments: dict) -> str:
    """Gatewayのツールを呼び出し"""
    # ツール名にプレフィックスを追加
    full_tool_name = f"{TOOL_PREFIX}{tool_name}"
    
    result = call_mcp_method(
        "tools/call",
        {
            "name": full_tool_name,
            "arguments": arguments
        }
    )
    
    if "result" in result:
        tool_result = result["result"]
        if "content" in tool_result:
            content = tool_result["content"]
            if isinstance(content, list) and len(content) > 0:
                text = content[0].get("text", str(content))
                # Lambda関数のレスポンスをパース
                try:
                    parsed = json.loads(text)
                    if "body" in parsed:
                        return parsed["body"]
                    return text
                except:
                    return text
        return json.dumps(tool_result, ensure_ascii=False)
    
    if "error" in result:
        return f"エラー: {json.dumps(result['error'], ensure_ascii=False)}"
    
    return json.dumps(result, ensure_ascii=False)


def build_agent():
    """Gateway経由でツールを使用するエージェントを構築"""
    
    if not GATEWAY_URL:
        raise ValueError(
            "GATEWAY_URL環境変数が設定されていません。\n"
            "デプロイ時に設定してください。"
        )
    
    # Gatewayからツール一覧を取得（確認用）
    print(f"Gateway URL: {GATEWAY_URL}")
    gateway_tools = get_gateway_tools()
    print(f"利用可能なツール: {[t['name'] for t in gateway_tools]}")
    
    # Gatewayツールをラップする関数を定義
    @tool
    def list_kbs() -> str:
        """利用可能なナレッジベース一覧を取得"""
        return call_gateway_tool("list_kbs", {})
    
    @tool
    def kb_search(kb_name: str, query: str, max_results: int = 5) -> str:
        """
        指定したナレッジベースを検索
        
        Args:
            kb_name: 検索するナレッジベースの名前（product_docs または faq）
            query: 検索クエリ
            max_results: 取得する結果の最大数
        """
        return call_gateway_tool("kb_search", {
            "kb_name": kb_name,
            "query": query,
            "max_results": max_results
        })
    
    @tool
    def auto_search(query: str, max_results: int = 5) -> str:
        """
        クエリから最適なナレッジベースを自動選択して検索
        
        Args:
            query: 検索クエリ
            max_results: 取得する結果の最大数
        """
        return call_gateway_tool("auto_search", {
            "query": query,
            "max_results": max_results
        })
    
    # Bedrockモデル設定
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name=REGION,
    )
    
    # メモリフックを設定（MEMORY_IDがある場合のみ）
    hooks = []
    if memory_client and MEMORY_ID:
        hooks.append(ShortTermMemoryHook())
        print("Short-term memory hook enabled")
    
    # エージェント作成
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[list_kbs, kb_search, auto_search],
        hooks=hooks,
        state={"session_id": "default"}  # デフォルトセッションID
    )


def main():
    """
    ローカルREPLモード
    
    注意: IAM認証のGatewayはAgentCore Runtime環境でのみ動作します。
    ローカルでは動作しません。
    """
    print("❌ このエージェントはAgentCore Runtime環境でのみ動作します")
    print("ローカルでのテストはできません")
    print()
    print("デプロイ方法:")
    print("  agentcore launch --auto-update-on-conflict")


if __name__ == "__main__":
    main()

# agentcore/app.py
"""
AgentCore Runtime用エントリーポイント
Gateway経由でナレッジベース検索を実行（IAM認証）
短期記憶（STM）対応、ストリーミングレスポンス対応
"""
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from main import build_agent

app = BedrockAgentCoreApp()

# エージェントを初期化（グローバルで一度だけ）
agent = None


@app.entrypoint
async def invoke(payload: dict, context=None):
    """
    AgentCore Runtimeからの呼び出しを処理（ストリーミング対応）
    
    Args:
        payload: {"prompt": "ユーザーの質問"}
        context: 実行コンテキスト（session_id等を含む）
    
    Yields:
        ストリーミングイベント（思考過程、ツール呼び出し、結果を含む）
    """
    global agent
    
    # 初回呼び出し時にエージェントを構築
    if agent is None:
        agent = build_agent()
    
    # セッションIDを取得（AgentCore Runtimeが自動管理）
    session_id = "default"
    if context:
        session_id = getattr(context, "session_id", None) or \
                     getattr(context, "sessionId", None) or \
                     "default"
        print(f"Session ID from context: {session_id}")
    
    # エージェントのセッションIDを更新
    agent.state.set("session_id", session_id)
    
    user_text = payload.get("prompt") or payload.get("input") or ""
    
    # ストリーミングでエージェントを実行
    agent_stream = agent.stream_async(user_text)
    
    async for event in agent_stream:
        # イベントの種類をログ出力（デバッグ用）
        event_type = type(event).__name__
        print(f"[Stream Event] {event_type}")
        
        # ツール呼び出しの詳細をログ
        if hasattr(event, 'tool_name'):
            print(f"  Tool: {event.tool_name}")
        if hasattr(event, 'tool_input'):
            print(f"  Input: {json.dumps(event.tool_input, ensure_ascii=False)[:200]}")
        if hasattr(event, 'tool_result'):
            print(f"  Result: {str(event.tool_result)[:200]}")
        
        yield event


if __name__ == "__main__":
    app.run()

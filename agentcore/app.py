# agentcore/app.py
"""
AgentCore Runtime用エントリーポイント
Gateway経由でナレッジベース検索を実行（IAM認証）
短期記憶（STM）対応
"""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from main import build_agent

app = BedrockAgentCoreApp()

# エージェントを初期化（グローバルで一度だけ）
agent = None


@app.entrypoint
def invoke(payload: dict, context=None):
    """
    AgentCore Runtimeからの呼び出しを処理
    
    Args:
        payload: {"prompt": "ユーザーの質問"}
        context: 実行コンテキスト（session_id等を含む）
    
    Returns:
        {"result": "エージェントの回答"}
    """
    global agent
    
    # 初回呼び出し時にエージェントを構築
    if agent is None:
        agent = build_agent()
    
    # セッションIDを取得（AgentCore Runtimeが自動管理）
    session_id = "default"
    if context:
        # contextオブジェクトからsession_idを取得
        session_id = getattr(context, "session_id", None) or \
                     getattr(context, "sessionId", None) or \
                     "default"
        print(f"Session ID from context: {session_id}")
    
    # エージェントのセッションIDを更新（setメソッドを使用）
    agent.state.set("session_id", session_id)
    
    user_text = payload.get("prompt") or payload.get("input") or ""
    
    # エージェントを実行
    result = agent(user_text)
    
    return {"result": str(result)}


if __name__ == "__main__":
    app.run()

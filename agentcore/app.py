# agentcore/app.py
"""
AgentCore Runtime用エントリーポイント
Gateway経由でナレッジベース検索を実行（IAM認証）
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
        context: 実行コンテキスト（オプション）
    
    Returns:
        {"result": "エージェントの回答"}
    """
    global agent
    
    # 初回呼び出し時にエージェントを構築
    if agent is None:
        agent = build_agent()
    
    user_text = payload.get("prompt") or payload.get("input") or ""
    
    # エージェントを実行
    result = agent(user_text)
    
    return {"result": str(result)}


if __name__ == "__main__":
    app.run()

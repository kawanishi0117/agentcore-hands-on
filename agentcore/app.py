# agentcore/app.py
"""
AgentCore Runtime用エントリーポイント
Gateway経由でナレッジベース検索を実行（IAM認証）
"""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from main import build_agent

app = BedrockAgentCoreApp()

# エージェントを初期化
agent, mcp_client = build_agent()


@app.entrypoint
def handler(payload: dict):
    """
    AgentCore Runtimeからの呼び出しを処理
    
    Args:
        payload: {"input": "ユーザーの質問"} or {"prompt": "ユーザーの質問"}
    
    Returns:
        {"output": "エージェントの回答"}
    """
    user_text = payload.get("input") or payload.get("prompt") or ""
    
    # MCPクライアントのコンテキスト内でエージェントを実行
    with mcp_client:
        result = agent(user_text)
    
    return {"output": str(result)}

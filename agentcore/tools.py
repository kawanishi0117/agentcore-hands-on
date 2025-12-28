# agentcore/tools.py
"""
ナレッジベース検索ツール（AgentCore Gateway経由）
Strands Agentから呼び出し可能なツールとして定義
"""
import json
import os
from typing import Any, Dict

from strands import tool


# Gateway設定
GATEWAY_ID = os.environ.get("AGENTCORE_GATEWAY_ID", "")
GATEWAY_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")


def call_gateway_tool(tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    AgentCore Gateway経由でツールを呼び出し
    
    Args:
        tool_name: ツール名（Smithyのオペレーション名）
        input_data: ツールへの入力パラメータ
    
    Returns:
        ツールの実行結果
    """
    import boto3
    
    if not GATEWAY_ID:
        raise ValueError(
            "AGENTCORE_GATEWAY_ID環境変数が設定されていません。\n"
            "Gateway IDを設定してください。"
        )
    
    client = boto3.client("bedrock-agent-runtime", region_name=GATEWAY_REGION)
    
    # Gateway経由でツールを呼び出し
    response = client.invoke_agent_tool(
        gatewayId=GATEWAY_ID,
        toolName=tool_name,
        input=input_data
    )
    
    # レスポンスをパース
    result = json.loads(response["body"].read())
    
    if response["statusCode"] != 200:
        error_msg = result.get("message", "Unknown error")
        raise RuntimeError(f"Gateway呼び出しエラー: {error_msg}")
    
    return result


@tool
def list_knowledge_bases() -> str:
    """
    利用可能なナレッジベース一覧を取得します。
    どのナレッジベースを検索すべきか判断するために、まずこのツールを呼んでください。
    
    Returns:
        利用可能なナレッジベースの名前と説明のリスト
    """
    result = call_gateway_tool("ListKnowledgeBases", {})
    kbs = result.get("knowledgeBases", [])
    
    # エージェントが理解しやすい形式で返す
    lines = ["利用可能なナレッジベース:"]
    for kb in kbs:
        lines.append(f"- {kb['name']}: {kb['description']}")
    
    return "\n".join(lines)


@tool
def search_knowledge_base(kb_name: str, query: str, max_results: int = 5) -> str:
    """
    指定したナレッジベースを検索します。
    
    Args:
        kb_name: 検索するナレッジベースの名前（list_knowledge_basesで確認可能）
        query: 検索クエリ（ユーザーの質問や検索したい内容）
        max_results: 取得する結果の最大数（デフォルト: 5）
    
    Returns:
        検索結果（関連するドキュメントの内容とスコア）
    """
    result = call_gateway_tool("SearchKnowledgeBase", {
        "kbName": kb_name,
        "query": query,
        "maxResults": max_results
    })
    
    # エラーチェック
    if "error" in result:
        return f"検索エラー: {result['error']}"
    
    search_result = result.get("result", {})
    
    # 結果を整形
    lines = [
        f"【{search_result.get('kbName', 'Unknown')}】を検索しました",
        f"クエリ: {search_result.get('query', '')}",
        f"ヒット数: {search_result.get('count', 0)}件",
        ""
    ]
    
    for i, item in enumerate(search_result.get("results", []), 1):
        score = item.get("score", 0)
        content = item.get("content", "")[:500]  # 長すぎる場合は切り詰め
        source = item.get("source", "不明")
        
        lines.append(f"--- 結果 {i} (スコア: {score:.3f}) ---")
        lines.append(f"ソース: {source}")
        lines.append(content)
        lines.append("")
    
    return "\n".join(lines)


@tool
def auto_search_knowledge_base(query: str, max_results: int = 5) -> str:
    """
    クエリ内容から最適なナレッジベースを自動選択して検索します。
    どのナレッジベースを使うか迷った場合はこのツールを使ってください。
    
    Args:
        query: 検索クエリ（ユーザーの質問）
        max_results: 取得する結果の最大数（デフォルト: 5）
    
    Returns:
        最適なナレッジベースでの検索結果
    """
    result = call_gateway_tool("AutoSearchKnowledgeBase", {
        "query": query,
        "maxResults": max_results
    })
    
    # エラーチェック
    if "error" in result:
        return f"検索エラー: {result['error']}"
    
    selected_kb = result.get("selectedKb", "Unknown")
    search_result = result.get("result", {})
    
    # 結果を整形
    lines = [
        f"【自動選択】{selected_kb} を選択しました",
        f"理由: クエリ内容から最適と判断",
        "",
        f"ヒット数: {search_result.get('count', 0)}件",
        ""
    ]
    
    for i, item in enumerate(search_result.get("results", []), 1):
        score = item.get("score", 0)
        content = item.get("content", "")[:500]
        
        lines.append(f"--- 結果 {i} (スコア: {score:.3f}) ---")
        lines.append(content)
        lines.append("")
    
    return "\n".join(lines)

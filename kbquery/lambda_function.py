# kbquery/lambda_function.py
"""
ナレッジベース検索用Lambda関数
AgentCore Gateway経由で呼び出される（Smithyモデル対応）

機能:
- クエリ分解: 長いクエリを複数に分けて検索
- ハイブリッド検索: ベクトル検索 + キーワード完全一致
- リランキング: 検索結果の再順位付け
"""
import json
import os
import re
import boto3
from typing import Any, Dict, List, Optional

from kb_config import get_kb_config, list_available_kbs


REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# クエリ分解の閾値（この文字数を超えたら分解を試みる）
QUERY_SPLIT_THRESHOLD = 50


def get_bedrock_client():
    """Bedrock Agent Runtimeクライアントを取得"""
    return boto3.client("bedrock-agent-runtime", region_name=REGION)


def split_query(query: str) -> List[str]:
    """
    長いクエリを複数のサブクエリに分解
    
    分解ルール:
    - 句読点（。、！？）で分割
    - 「と」「や」「および」などの接続詞で分割
    - 短すぎる分割は除外
    """
    if len(query) < QUERY_SPLIT_THRESHOLD:
        return [query]
    
    # 句読点・接続詞で分割
    patterns = [
        r'[。！？\n]',           # 句読点
        r'(?:、また|、そして)',   # 接続表現
        r'(?:について|に関して)', # トピック区切り
    ]
    
    sub_queries = [query]
    for pattern in patterns:
        new_queries = []
        for q in sub_queries:
            parts = re.split(pattern, q)
            new_queries.extend([p.strip() for p in parts if p.strip()])
        sub_queries = new_queries
    
    # 短すぎるクエリを除外（5文字未満）、重複除去
    sub_queries = list(set([q for q in sub_queries if len(q) >= 5]))
    
    # 分解結果が1つだけなら元のクエリを返す
    return sub_queries if len(sub_queries) > 1 else [query]


def extract_keywords(query: str) -> List[str]:
    """
    クエリから重要キーワードを抽出（ハイブリッド検索用）
    
    抽出対象:
    - 英数字の連続（API名、関数名など）
    - カタカナ語
    - 括弧内の文字列
    """
    keywords = []
    
    # 英数字（API名、関数名、エラーコードなど）
    keywords.extend(re.findall(r'[A-Za-z][A-Za-z0-9_]{2,}', query))
    
    # カタカナ語（3文字以上）
    keywords.extend(re.findall(r'[ァ-ヶー]{3,}', query))
    
    # 括弧内の文字列
    keywords.extend(re.findall(r'[「『\(]([^」』\)]+)[」』\)]', query))
    
    # 重複除去して返す
    return list(set(keywords))


def build_retrieval_config(
    kb_config: Dict[str, Any],
    max_results: int,
    use_hybrid: bool = True
) -> Dict[str, Any]:
    """
    KB設定からretrieval configを構築
    リランキング・ハイブリッド検索の設定を自動適用
    """
    config: Dict[str, Any] = {
        "vectorSearchConfiguration": {
            "numberOfResults": max_results
        }
    }
    
    # ハイブリッド検索（ベクトル + キーワード）
    if use_hybrid:
        config["vectorSearchConfiguration"]["overrideSearchType"] = "HYBRID"
    
    # リランキング設定
    if kb_config.get("rerank"):
        rerank_model = kb_config.get("rerank_model", "AMAZON")
        
        # モデルARNを構築
        if rerank_model == "AMAZON":
            model_arn = f"arn:aws:bedrock:{REGION}::foundation-model/amazon.rerank-v1:0"
        else:  # COHERE
            model_arn = f"arn:aws:bedrock:{REGION}::foundation-model/cohere.rerank-v3-5:0"
        
        config["vectorSearchConfiguration"]["rerankingConfiguration"] = {
            "type": "BEDROCK_RERANKING_MODEL",
            "bedrockRerankingConfiguration": {
                "modelConfiguration": {
                    "modelArn": model_arn
                }
            }
        }
    
    return config


def merge_results(
    all_results: List[Dict[str, Any]],
    max_results: int
) -> List[Dict[str, Any]]:
    """
    複数クエリの結果をマージ・重複除去・スコア順ソート
    """
    # sourceをキーにして重複除去（スコアが高い方を残す）
    seen: Dict[str, Dict[str, Any]] = {}
    for result in all_results:
        source = result.get("source", "")
        if source not in seen or result.get("score", 0) > seen[source].get("score", 0):
            seen[source] = result
    
    # スコア順でソートして上位を返す
    merged = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)
    return merged[:max_results]


def search_knowledge_base_impl(
    kb_name: str,
    query: str,
    max_results: int = 5
) -> Dict[str, Any]:
    """
    ナレッジベースを検索（クエリ分解・ハイブリッド検索対応）
    
    Args:
        kb_name: KB設定名（kb_config.pyで定義）
        query: 検索クエリ
        max_results: 取得する結果の最大数
    
    Returns:
        検索結果
    """
    # KB設定を取得
    kb_config = get_kb_config(kb_name)
    if not kb_config:
        raise ValueError(f"Unknown knowledge base: {kb_name}")
    
    client = get_bedrock_client()
    
    # クエリ分解
    sub_queries = split_query(query)
    
    # キーワード抽出（ハイブリッド検索の補助）
    keywords = extract_keywords(query)
    
    # ハイブリッド検索（ベクトル + キーワード）- KB設定で有効な場合のみ
    use_hybrid = kb_config.get("hybrid", False)
    
    # 各サブクエリで検索実行
    all_results: List[Dict[str, Any]] = []
    queries_used = []
    
    for sub_query in sub_queries:
        # キーワードがあればクエリに追加（検索精度向上）
        enhanced_query = sub_query
        if keywords:
            enhanced_query = f"{sub_query} {' '.join(keywords[:3])}"
        
        queries_used.append(enhanced_query)
        
        response = client.retrieve(
            knowledgeBaseId=kb_config["id"],
            retrievalQuery={"text": enhanced_query},
            retrievalConfiguration=build_retrieval_config(
                kb_config,
                max_results=max_results * 2,  # マージ用に多めに取得
                use_hybrid=use_hybrid
            )
        )
        
        # 結果を収集
        for item in response.get("retrievalResults", []):
            content = item.get("content", {}).get("text", "")
            score = item.get("score", 0.0)
            location = item.get("location", {})
            
            all_results.append({
                "content": content,
                "score": score,
                "source": location.get("s3Location", {}).get("uri", "unknown")
            })
    
    # 結果をマージ・重複除去
    merged_results = merge_results(all_results, max_results)
    
    return {
        "kbName": kb_name,
        "kbDescription": kb_config["description"],
        "query": query,
        "subQueries": queries_used,
        "keywordsExtracted": keywords,
        "results": merged_results,
        "count": len(merged_results),
        "reranked": kb_config.get("rerank", False),
        "hybridSearch": kb_config.get("hybrid", False)
    }


def auto_select_kb(query: str) -> str:
    """
    クエリ内容から最適なナレッジベースを自動選択
    
    Args:
        query: 検索クエリ
    
    Returns:
        選択されたKB名
    """
    kbs = list_available_kbs()
    
    if not kbs:
        raise ValueError("No knowledge bases available")
    
    # キーワードマッチングで最適なKBを選択
    query_lower = query.lower()
    best_kb = None
    best_score = 0
    
    # 簡易的なキーワードマッチング
    keyword_map = {
        "product_docs": ["認証", "ログイン", "パスワード", "auth", "login", "マニュアル", "使い方"],
        "faq": ["よくある質問", "faq", "サンプル", "例", "ドキュメント"],
    }
    
    for kb in kbs:
        kb_name = kb["name"]
        keywords = keyword_map.get(kb_name, [])
        
        # キーワードマッチスコア計算
        score = sum(1 for kw in keywords if kw in query_lower)
        
        # 説明文とのマッチも考慮
        if kb["description"].lower() in query_lower:
            score += 2
        
        if score > best_score:
            best_score = score
            best_kb = kb_name
    
    # マッチしなければ最初のKBを使用
    if not best_kb:
        best_kb = kbs[0]["name"]
    
    return best_kb


# ========================================
# ツールハンドラー（AgentCore Gateway対応）
# ========================================

def handle_list_kbs(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    list_kbs ツール: 利用可能なKB一覧を返す
    """
    kbs = list_available_kbs()
    return {
        "knowledgeBases": kbs
    }


def handle_kb_search(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    kb_search ツール: 指定KBを検索する
    
    Args:
        kb_name: 検索するナレッジベースの名前
        query: 検索クエリ
        max_results: 取得する結果の最大数（デフォルト: 5）
    """
    kb_name = args.get("kb_name")
    query = args.get("query")
    max_results = args.get("max_results", 5)
    
    if not kb_name:
        raise ValueError("kb_name is required")
    if not query:
        raise ValueError("query is required")
    
    result = search_knowledge_base_impl(kb_name, query, max_results)
    return result


def handle_auto_search(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    auto_search ツール: クエリから最適なKBを自動選択して検索
    
    Args:
        query: 検索クエリ
        max_results: 取得する結果の最大数（デフォルト: 5）
    """
    query = args.get("query")
    max_results = args.get("max_results", 5)
    
    if not query:
        raise ValueError("query is required")
    
    # 最適なKBを自動選択
    selected_kb = auto_select_kb(query)
    
    # 検索実行
    result = search_knowledge_base_impl(selected_kb, query, max_results)
    
    return {
        "selectedKb": selected_kb,
        "result": result
    }


# ツール名とハンドラーのマッピング
TOOL_HANDLERS = {
    "list_kbs": handle_list_kbs,
    "kb_search": handle_kb_search,
    "auto_search": handle_auto_search,
}


# ========================================
# Lambda ハンドラー（AgentCore Gateway対応）
# ========================================

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda エントリーポイント（AgentCore Gateway対応）
    
    Gatewayからは以下の形式でイベントが渡される:
    {
        "toolName": "list_kbs" | "kb_search" | "auto_search",
        "input": { ... }  # ツール固有の引数
    }
    
    または直接引数が渡される場合:
    {
        "kb_name": "...",
        "query": "...",
        ...
    }
    """
    try:
        # デバッグ用: 受信イベントをログ出力
        print(f"Received event: {json.dumps(event, ensure_ascii=False)}")
        
        # ツール名を取得（複数の形式に対応）
        tool_name = (
            event.get("toolName") or 
            event.get("tool_name") or 
            event.get("name") or
            event.get("operation")  # 旧形式との互換性
        )
        
        # 引数を取得（複数の形式に対応）
        args = event.get("input") or event.get("arguments") or event
        
        # ツール名がない場合、引数から推測
        if not tool_name:
            if "kb_name" in args and "query" in args:
                tool_name = "kb_search"
            elif "query" in args:
                tool_name = "auto_search"
            else:
                tool_name = "list_kbs"
        
        # 旧形式のオペレーション名を新形式に変換
        operation_mapping = {
            "ListKnowledgeBases": "list_kbs",
            "SearchKnowledgeBase": "kb_search",
            "AutoSearchKnowledgeBase": "auto_search",
        }
        tool_name = operation_mapping.get(tool_name, tool_name)
        
        print(f"Tool name: {tool_name}, Args: {json.dumps(args, ensure_ascii=False)}")
        
        # ハンドラーを取得して実行
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Unknown tool: {tool_name}",
                    "availableTools": list(TOOL_HANDLERS.keys())
                }, ensure_ascii=False)
            }
        
        # ツール実行
        output = handler(args)
        
        # 成功レスポンス
        return {
            "statusCode": 200,
            "body": json.dumps(output, ensure_ascii=False)
        }
    
    except ValueError as e:
        # バリデーションエラー
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": str(e)
            }, ensure_ascii=False)
        }
    except Exception as e:
        # 内部エラー
        import traceback
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            }, ensure_ascii=False)
        }

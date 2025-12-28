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
# Smithy対応のオペレーションハンドラー
# ========================================

def handle_list_knowledge_bases(event: Dict[str, Any]) -> Dict[str, Any]:
    """ListKnowledgeBases オペレーション"""
    kbs = list_available_kbs()
    return {
        "knowledgeBases": kbs
    }


def handle_search_knowledge_base(event: Dict[str, Any]) -> Dict[str, Any]:
    """SearchKnowledgeBase オペレーション"""
    kb_name = event.get("kbName")
    query = event.get("query")
    max_results = event.get("maxResults", 5)
    
    if not kb_name:
        raise ValueError("kbName is required")
    if not query:
        raise ValueError("query is required")
    
    result = search_knowledge_base_impl(kb_name, query, max_results)
    return {"result": result}


def handle_auto_search_knowledge_base(event: Dict[str, Any]) -> Dict[str, Any]:
    """AutoSearchKnowledgeBase オペレーション"""
    query = event.get("query")
    max_results = event.get("maxResults", 5)
    
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


# ========================================
# Lambda ハンドラー（Gateway対応）
# ========================================

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda エントリーポイント（AgentCore Gateway対応）
    
    Gatewayからは以下の形式でイベントが渡される:
    {
        "operation": "ListKnowledgeBases" | "SearchKnowledgeBase" | "AutoSearchKnowledgeBase",
        "input": { ... }  # オペレーション固有の入力
    }
    """
    try:
        operation = event.get("operation")
        input_data = event.get("input", {})
        
        # オペレーションに応じてハンドラーを呼び出し
        if operation == "ListKnowledgeBases":
            output = handle_list_knowledge_bases(input_data)
        elif operation == "SearchKnowledgeBase":
            output = handle_search_knowledge_base(input_data)
        elif operation == "AutoSearchKnowledgeBase":
            output = handle_auto_search_knowledge_base(input_data)
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": f"Unknown operation: {operation}"
                }, ensure_ascii=False)
            }
        
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
                "message": str(e)
            }, ensure_ascii=False)
        }
    except Exception as e:
        # 内部エラー
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": str(e)
            }, ensure_ascii=False)
        }

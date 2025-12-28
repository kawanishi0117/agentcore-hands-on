# kbquery/lambda_function.py
"""
ナレッジベース検索用Lambda関数
AgentCore Gateway経由で呼び出される

機能:
- クエリ分解: 長いクエリを複数に分けて検索
- ハイブリッド検索: ベクトル検索 + キーワード完全一致
- リランキング: 検索結果の再順位付け

呼び出し例:
{
    "action": "search",
    "kb_name": "product_docs",
    "query": "〇〇の使い方",
    "max_results": 5
}

{
    "action": "list_kbs"
}
"""
import json
import os
import re
import boto3
from typing import Any

from kb_config import get_kb_config, list_available_kbs


REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

# クエリ分解の閾値（この文字数を超えたら分解を試みる）
QUERY_SPLIT_THRESHOLD = 50


def get_bedrock_client():
    """Bedrock Agent Runtimeクライアントを取得"""
    return boto3.client("bedrock-agent-runtime", region_name=REGION)


def split_query(query: str) -> list[str]:
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


def extract_keywords(query: str) -> list[str]:
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
    kb_config: dict,
    max_results: int,
    use_hybrid: bool = True
) -> dict:
    """
    KB設定からretrieval configを構築
    リランキング・ハイブリッド検索の設定を自動適用
    """
    config: dict[str, Any] = {
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
    all_results: list[dict],
    max_results: int
) -> list[dict]:
    """
    複数クエリの結果をマージ・重複除去・スコア順ソート
    """
    # sourceをキーにして重複除去（スコアが高い方を残す）
    seen: dict[str, dict] = {}
    for result in all_results:
        source = result.get("source", "")
        if source not in seen or result.get("score", 0) > seen[source].get("score", 0):
            seen[source] = result
    
    # スコア順でソートして上位を返す
    merged = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)
    return merged[:max_results]


def search_knowledge_base(
    kb_name: str,
    query: str,
    max_results: int = 5
) -> dict[str, Any]:
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
    all_results: list[dict] = []
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
        "kb_name": kb_name,
        "kb_description": kb_config["description"],
        "query": query,
        "sub_queries": queries_used,
        "keywords_extracted": keywords,
        "results": merged_results,
        "count": len(merged_results),
        "reranked": kb_config.get("rerank", False),
        "hybrid_search": kb_config.get("hybrid", False)
    }


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Lambda エントリーポイント
    
    アクション:
    - list_kbs: 利用可能なKB一覧を取得
    - search: 指定KBを検索
    """
    try:
        action = event.get("action", "search")
        
        # KB一覧取得
        if action == "list_kbs":
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "knowledge_bases": list_available_kbs()
                }, ensure_ascii=False)
            }
        
        # 検索
        if action == "search":
            kb_name = event.get("kb_name", "")
            query = event.get("query", "")
            max_results = event.get("max_results", 5)
            
            if not kb_name:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "kb_name is required"}, ensure_ascii=False)
                }
            
            if not query:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "query is required"}, ensure_ascii=False)
                }
            
            result = search_knowledge_base(kb_name, query, max_results)
            
            return {
                "statusCode": 200,
                "body": json.dumps(result, ensure_ascii=False)
            }
        
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)
        }
    
    except ValueError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}, ensure_ascii=False)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}, ensure_ascii=False)
        }

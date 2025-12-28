#!/usr/bin/env python3
# kbquery/test_gateway.py
"""
Gateway対応Lambda関数のローカルテスト
実際のGatewayを使わずに、Lambda関数を直接呼び出してテスト
"""
import json
from lambda_function import lambda_handler


def test_list_knowledge_bases():
    """KB一覧取得のテスト"""
    print("=" * 60)
    print("テスト: ListKnowledgeBases")
    print("=" * 60)
    
    event = {
        "operation": "ListKnowledgeBases",
        "input": {}
    }
    
    result = lambda_handler(event, None)
    print(f"ステータスコード: {result['statusCode']}")
    print(f"レスポンス:\n{json.dumps(json.loads(result['body']), indent=2, ensure_ascii=False)}")
    print()


def test_search_knowledge_base():
    """KB検索のテスト"""
    print("=" * 60)
    print("テスト: SearchKnowledgeBase")
    print("=" * 60)
    
    event = {
        "operation": "SearchKnowledgeBase",
        "input": {
            "kbName": "product_docs",
            "query": "認証機能の使い方",
            "maxResults": 3
        }
    }
    
    result = lambda_handler(event, None)
    print(f"ステータスコード: {result['statusCode']}")
    
    body = json.loads(result['body'])
    if result['statusCode'] == 200:
        search_result = body.get('result', {})
        print(f"KB名: {search_result.get('kbName')}")
        print(f"クエリ: {search_result.get('query')}")
        print(f"ヒット数: {search_result.get('count')}")
        print(f"リランキング: {search_result.get('reranked')}")
        print(f"ハイブリッド検索: {search_result.get('hybridSearch')}")
        print("\n検索結果:")
        for i, item in enumerate(search_result.get('results', [])[:2], 1):
            print(f"\n--- 結果 {i} ---")
            print(f"スコア: {item.get('score', 0):.3f}")
            print(f"内容: {item.get('content', '')[:200]}...")
    else:
        print(f"エラー: {body}")
    print()


def test_auto_search_knowledge_base():
    """自動KB選択検索のテスト"""
    print("=" * 60)
    print("テスト: AutoSearchKnowledgeBase")
    print("=" * 60)
    
    event = {
        "operation": "AutoSearchKnowledgeBase",
        "input": {
            "query": "ログイン方法について教えて",
            "maxResults": 3
        }
    }
    
    result = lambda_handler(event, None)
    print(f"ステータスコード: {result['statusCode']}")
    
    body = json.loads(result['body'])
    if result['statusCode'] == 200:
        print(f"選択されたKB: {body.get('selectedKb')}")
        search_result = body.get('result', {})
        print(f"ヒット数: {search_result.get('count')}")
        print("\n検索結果:")
        for i, item in enumerate(search_result.get('results', [])[:2], 1):
            print(f"\n--- 結果 {i} ---")
            print(f"スコア: {item.get('score', 0):.3f}")
            print(f"内容: {item.get('content', '')[:200]}...")
    else:
        print(f"エラー: {body}")
    print()


def test_validation_error():
    """バリデーションエラーのテスト"""
    print("=" * 60)
    print("テスト: バリデーションエラー")
    print("=" * 60)
    
    event = {
        "operation": "SearchKnowledgeBase",
        "input": {
            # kbNameが欠落
            "query": "テスト"
        }
    }
    
    result = lambda_handler(event, None)
    print(f"ステータスコード: {result['statusCode']}")
    print(f"エラーメッセージ: {json.loads(result['body'])}")
    print()


def test_unknown_operation():
    """不明なオペレーションのテスト"""
    print("=" * 60)
    print("テスト: 不明なオペレーション")
    print("=" * 60)
    
    event = {
        "operation": "UnknownOperation",
        "input": {}
    }
    
    result = lambda_handler(event, None)
    print(f"ステータスコード: {result['statusCode']}")
    print(f"エラーメッセージ: {json.loads(result['body'])}")
    print()


if __name__ == "__main__":
    print("\n🧪 Gateway対応Lambda関数のテスト開始\n")
    
    # 各テストを実行
    test_list_knowledge_bases()
    test_search_knowledge_base()
    test_auto_search_knowledge_base()
    test_validation_error()
    test_unknown_operation()
    
    print("✅ すべてのテストが完了しました")

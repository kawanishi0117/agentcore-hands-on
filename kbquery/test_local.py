# kbquery/test_local.py
"""
ローカルテスト用スクリプト
"""
from lambda_function import lambda_handler


def test_list_kbs():
    """KB一覧取得テスト"""
    print("=== KB一覧取得 ===")
    event = {"action": "list_kbs"}
    result = lambda_handler(event, None)
    print(f"Status: {result['statusCode']}")
    print(f"Body: {result['body']}")


def test_search():
    """検索テスト"""
    print("\n=== 検索テスト ===")
    event = {
        "action": "search",
        "kb_name": "product_docs",
        "query": "使い方を教えて",
        "max_results": 3
    }
    result = lambda_handler(event, None)
    print(f"Status: {result['statusCode']}")
    print(f"Body: {result['body']}")


def test_unknown_kb():
    """存在しないKBのエラーテスト"""
    print("\n=== 存在しないKBテスト ===")
    event = {
        "action": "search",
        "kb_name": "unknown_kb",
        "query": "テスト"
    }
    result = lambda_handler(event, None)
    print(f"Status: {result['statusCode']}")
    print(f"Body: {result['body']}")


if __name__ == "__main__":
    test_list_kbs()
    test_search()
    test_unknown_kb()

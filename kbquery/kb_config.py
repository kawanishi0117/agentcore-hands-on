# kbquery/kb_config.py
"""
ナレッジベース設定
ここにKBのIDと説明を追加していく
"""

# ナレッジベース定義
# key: 呼び出し時に使う名前
# id: BedrockのKB ID
# description: 何が入っているかの説明
# rerank: リランキングを有効にするか
# rerank_model: リランキングモデル（AMAZON or COHERE）
KNOWLEDGE_BASES: dict[str, dict] = {
    "product_docs": {
        "id": "JEBUX7Q8QN",
        "description": "認証機能マニュアル",
        "rerank": True,
        "rerank_model": "AMAZON",
    },
    "faq": {
        "id": "2I5CHITSB5",
        "description": "サンプルドキュメント",
        "rerank": True,
        "rerank_model": "AMAZON",
    },
    # "internal_wiki": {
    #     "id": "ZZZZZZZZZZ",  # 実際のKB IDに置き換え
    #     "description": "社内Wiki・ナレッジ",
    #     "rerank": False,
    #     "rerank_model": None,
    # },
}


def get_kb_config(kb_name: str) -> dict | None:
    """指定した名前のKB設定を取得"""
    return KNOWLEDGE_BASES.get(kb_name)


def list_available_kbs() -> list[dict]:
    """利用可能なKB一覧を取得（呼び出し元が選択用に使う）"""
    return [
        {"name": name, "description": config["description"]}
        for name, config in KNOWLEDGE_BASES.items()
    ]

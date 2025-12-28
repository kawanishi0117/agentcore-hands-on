$version: "2.0"

namespace com.example.kbquery

/// ナレッジベース検索サービス
@title("Knowledge Base Query Service")
service KnowledgeBaseQueryService {
    version: "1.0"
    operations: [
        ListKnowledgeBases
        SearchKnowledgeBase
        AutoSearchKnowledgeBase
    ]
}

/// 利用可能なナレッジベース一覧を取得
@readonly
@http(method: "POST", uri: "/list-knowledge-bases")
operation ListKnowledgeBases {
    input := {}
    output := {
        @required
        knowledgeBases: KnowledgeBaseList
    }
    errors: [InternalError]
}

/// 指定したナレッジベースを検索
@http(method: "POST", uri: "/search-knowledge-base")
operation SearchKnowledgeBase {
    input := {
        /// 検索するナレッジベースの名前
        @required
        kbName: String

        /// 検索クエリ
        @required
        query: String

        /// 取得する結果の最大数（デフォルト: 5）
        maxResults: Integer = 5
    }
    output := {
        @required
        result: SearchResult
    }
    errors: [ValidationError, InternalError]
}

/// クエリ内容から最適なナレッジベースを自動選択して検索
@http(method: "POST", uri: "/auto-search-knowledge-base")
operation AutoSearchKnowledgeBase {
    input := {
        /// 検索クエリ
        @required
        query: String

        /// 取得する結果の最大数（デフォルト: 5）
        maxResults: Integer = 5
    }
    output := {
        @required
        selectedKb: String

        @required
        result: SearchResult
    }
    errors: [ValidationError, InternalError]
}

/// ナレッジベース情報
structure KnowledgeBase {
    /// ナレッジベース名
    @required
    name: String

    /// 説明
    @required
    description: String
}

/// ナレッジベースリスト
list KnowledgeBaseList {
    member: KnowledgeBase
}

/// 検索結果
structure SearchResult {
    /// ナレッジベース名
    @required
    kbName: String

    /// ナレッジベースの説明
    @required
    kbDescription: String

    /// 元のクエリ
    @required
    query: String

    /// 分解されたサブクエリ
    subQueries: StringList

    /// 抽出されたキーワード
    keywordsExtracted: StringList

    /// 検索結果アイテム
    @required
    results: SearchResultItemList

    /// 結果数
    @required
    count: Integer

    /// リランキングが適用されたか
    @required
    reranked: Boolean

    /// ハイブリッド検索が使用されたか
    @required
    hybridSearch: Boolean
}

/// 検索結果アイテム
structure SearchResultItem {
    /// ドキュメント内容
    @required
    content: String

    /// 関連度スコア
    @required
    score: Double

    /// ソースURI
    @required
    source: String
}

/// 検索結果アイテムリスト
list SearchResultItemList {
    member: SearchResultItem
}

/// 文字列リスト
list StringList {
    member: String
}

/// バリデーションエラー
@error("client")
@httpError(400)
structure ValidationError {
    @required
    message: String
}

/// 内部エラー
@error("server")
@httpError(500)
structure InternalError {
    @required
    message: String
}

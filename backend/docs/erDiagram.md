erDiagram
    User ||--o{ ServiceRecord : 1対多 (主体)
    Staff ||--o{ ServiceRecord : 1対多 (提供者)
    Staff ||--o{ SelfAwarenessLog : 1対多 (記録者)
    SelfAwarenessLog }|--|| ServiceRecord : 1対1 (提供の前提)
    ServiceRecord ||--o{ BillingData : 1対1 (請求の根拠)
    LawMaster ||--o{ BillingData : 1対多 (加算条項の適用)
    
    %% 強調ポイント
    %% サービス提供記録には、提供前に作成された「自己覚知ログ」が必須で紐づく。
    %% 報酬請求データは、法律マスターを参照し「法的逸脱監視アラート」を生成する。

    %% エンティティの属性ハイライト
    User {
        UserID PK
        非依存性指標履歴 Array
    }
    Staff {
        StaffID PK
        最終自己覚知ログ日時 DateTime
    }
    ServiceRecord {
        RecordID PK
        自己覚知ログID FK
        活きる糧評価 Int
        非依存性シグナル Boolean
    }
    SelfAwarenessLog {
        LogID PK
        介入前のエゴ Text
    }
    BillingData {
        BillingID PK
        法的逸脱監視アラート Boolean
        適用加算条項 Array
    }
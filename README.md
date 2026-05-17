# Ramp-System: 就労移行支援業務統合システム

現場の記録、運営のコンプライアンス、経営の意思決定を統合し、支援の質と業務効率を最大化する「就労移行支援」特化型SaaS。

## 🚀 主要機能
- **リアルタイム活動トラッカー**: ダッシュボードから直接支援・間接業務をワンクリックで記録。
- **インテリジェント日報連携**: 記録した活動を自動的に日報タイムラインへ反映し、転記ミスをゼロに。
- **個別支援計画連動**: すべての支援記録を計画目標と紐付け、算定根拠と監査証跡を自動生成。
- **日本時間 (JST) 最適化**: サーバー所在地を問わず、日本のカレンダーと時刻に基づいた業務運用を実現。

## 📚 開発ガイドライン
開発に参加する際は、必ず以下の命名規則とルールブックを参照してください。
- [📏 命名規則と予約語](backend/docs/NAMING_CONVENTIONS.md)
- [📏 バージョン管理とコミットルール](backend/docs/CONTRIBUTING.md)

## 🛠 技術スタック

### バックエンド (Python 3.12+)
- **フレームワーク:** Flask (Web API)
- **データベース操作 (ORM):** SQLAlchemy / Flask-SQLAlchemy
- **マイグレーション:** Flask-Migrate (Alembic)
- **認証・セキュリティ:** Flask-JWT-Extended (Cookie-based JWT with CSRF Protection)
- **暗号化:** Flask-Bcrypt, Cryptography (PII暗号化)
- **テスト:** pytest

### フロントエンド (Modern Web Stack)
- **フレームワーク:** React 18 / Vite
- **言語:** TypeScript (Strict Mode)
- **スタイリング:** Tailwind CSS
- **アイコン:** Lucide React
- **通信:** Axios (CSRF Token Auto-injection)

### インフラ・DB
- **RDBMS:** PostgreSQL / SQLite (Local/Test)
- **タイムゾーン:** Asia/Tokyo (JST)

## 📅 最近のアップデート

- **フロントエンド関心の分離（Separation of Concerns）リファクタリング (2026年5月)**:
  - **利用者ダッシュボードのクリーン設計**: ロジック（API通信および状態遷移）を [useUserDashboard.ts](frontend/src/hooks/useUserDashboard.ts) に、表示レイアウト（UIマークアップ）を [UserDashboardView.tsx](frontend/src/components/UserDashboardView.tsx) に完全分離。300行超の巨大ファイルを約30行の極めてスリムなブリッジコンポーネントへ整理し、高い保守性とユニットテスト性を確保。
  - **スタッフ詳細・編集機能の完全実装（Phase 1 残課題の解消）**: スタッフの基本情報（姓・名、ふりがな、コード、メール、雇用形態、週労働時間、有効ステータス、入社日）の閲覧カードと、インプットモード最適化済みの対話型「編集モード」フォームを [StaffDetailPanel.tsx](frontend/src/features/staff/components/StaffDetailPanel.tsx) に統合。対応するバックエンド `PUT /api/management/staff/<id>` API も新設し、双方向の更新処理が完全な型安全（tscエラーなし）で稼働。
- **フェーズ1 セキュリティと基本管理機能の実装 (2026年5月)**:
  - **個人情報（PII）閲覧アクセス監査ログ**: PII属性（名前、連絡先、住所等）の復号化時に理由（10文字以上）の入力を必須とし、データベース内の `AuditActionLog` テーブルにアクセス証跡を永続保存するバックエンド監査APIを新設。
  - **揮発性個人情報保護ラッパー**: 目のアイコンクリックから監査ログを記録して一時的に PII を復号し、20秒後に自動的に再マスク表示へと切り替える保護ラッパーコンポーネント `PiiSecureWrapper` をフロントエンドに配備。
  - **PIIセッション保護自動ロックタイマー**: 10分間のユーザー非アクティブ時にダッシュボード画面全体をすりガラス状のオーバーレイで強力にロックし、パスワード認証を求める `SessionLockTimer` セキュリティガードを統合。
  - **事業所加算届出（Filing）履歴管理**: 加算適用期間をカレンダーから設定し、現在日付と照らし合わせて自動的に `"有効"` や `"期限切れ"` を色分け表示する届出履歴カードおよび追加モーダルを事業所設定画面に完全統合。
- **事業所設定とスタッフ管理の完成**: 郵便番号からの住所自動入力、法令準拠の入力項目追加、スタッフ新規登録機能（モーダルUI・厳格なバリデーション）の実装。

## 🏗 セットアップ

### バックエンド
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python seed_admin.py     # デモデータの投入
python run.py            # サーバー起動
```

### フロントエンド
```bash
cd frontend
npm install
npm run dev              # 開発サーバー起動
```
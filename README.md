# Ramp-System: 就労移行支援業務統合システム

## 目的
現場の記録、運営のコンプライアンス、経営の意思決定を統合し、支援の質と業務効率を最大化する。

## 📚 開発ガイドライン
開発に参加する際は、必ず以下の命名規則とルールブックを参照してください。
- [📏 命名規則と予約語 (NAMING_CONVENTIONS.md)](backend/docs/NAMING_CONVENTIONS.md)
- [📏 バージョン管理とコミットルール (NAMING_CONVENTIONS.md)](backend/docs/CONTRIBUTING.md)

## 技術スタック

### バックエンド (Python)
- **フレームワーク:** Flask (Web API)
- **データベース操作 (ORM):** SQLAlchemy / Flask-SQLAlchemy
- **マイグレーション:** Flask-Migrate (Alembic)
- **認証・セキュリティ:** Flask-Bcrypt (パスワードハッシュ化), Cryptography (Fernet暗号化), Flask-JWT-Extended (予定: トークン認証)
- **環境管理:** python-dotenv (環境変数)
- **テスト:** pytest (単体テスト)

### データベース
- **RDBMS:** PostgreSQL (本番/開発), SQLite (テスト用インメモリ)

### フロントエンド (予定)
- **言語:** TypeScript
- **フレームワーク:** React / Vite
- **UIライブラリ:** Tailwind CSS (予定)
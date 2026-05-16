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
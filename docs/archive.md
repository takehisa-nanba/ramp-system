# 削除ファイルアーカイブ記録 (MVP整理フェーズ)

本ドキュメントは、MVP (Minimum Viable Product) としての要件にフォーカスし、ソースコードをクリーンに保つために整理・削除したファイルの記録です。将来的にこれらの機能（スタッフ管理、タイムカード等）を復活させる際の参照元として機能します。

## 削除対象ファイルおよびディレクトリ一覧

### 1. フロントエンド旧モックコンポーネント (frontend/src/components/)
- **[ActivityTracker.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/ActivityTracker.tsx)**: 職員の稼働状態や活動内容をフローティングUIで記録・測定するコンポーネント。
- **[DailyLogCreator.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/DailyLogCreator.tsx)**: 日報データを対話的（面談や送迎等の項目別）に生成するためのモックダイアログ。
- **[Dashboard.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/Dashboard.tsx)**: 移行前の旧モックダッシュボードUI。現在は `pages/DashboardPage.tsx` が本番稼働中。
- **[OfficeSettings.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/OfficeSettings.tsx)**: 事業所の加算届出や基本設定を管理するUIコンポーネント。
- **[PlanCreator.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/PlanCreator.tsx)**: 個別支援計画をステップバイステップで作成するウィザード型モックUI。
- **[StaffManagement.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/StaffManagement.tsx)**: スタッフ管理画面のラッパー。
- **[Timecard.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/Timecard.tsx)**: 打刻およびタイムカードの一覧を表示するMVP外のUI。
- **[UserBasicEditForm.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/UserBasicEditForm.tsx)**: 旧利用者詳細画面における、基本情報編集用のフォームUI。
- **[UserDashboard.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/UserDashboard.tsx)**: 利用者向けの簡易ポータルダッシュボード。
- **[UserDashboardView.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/UserDashboardView.tsx)**: 利用者ダッシュボードの表示専用コンポーネント。
- **[UserDetailPage.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/UserDetailPage.tsx)**: 移行前の旧利用者詳細画面。現在は `pages/UserDetailPage.tsx` が本番稼働中。
- **[UserManager.tsx](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/UserManager.tsx)**: 移行前の旧利用者管理画面。現在は `pages/UserListPage.tsx` が本番稼働中。
- **[staff/](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/components/staff/)** (ディレクトリ): スタッフ管理に関連する旧UIファイル群。

### 2. フロントエンド旧モック機能 (frontend/src/features/)
- **[staff/](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/features/staff/)** (ディレクトリ): 職員の職種や就業状況を管理・シードするためのMVP外機能。

### 3. フロントエンド旧モックフック (frontend/src/hooks/)
- **[useUserDashboard.ts](file:///c:/Users/nanba/Desktop/ramp-system/frontend/src/hooks/useUserDashboard.ts)**: 利用者ダッシュボード用のビジネスロジック用フック。

### 4. ルートディレクトリの過去アーカイブ
- **[backend.zip](file:///c:/Users/nanba/Desktop/ramp-system/backend.zip)**: バックエンド開発中のバックアップファイル。
- **[frontend.zip](file:///c:/Users/nanba/Desktop/ramp-system/frontend.zip)**: フロントエンド開発中のバックアップファイル。

## 復活させる際の手順
これらはすべて git コミット履歴に保存されています。過去のリビジョンからファイルを復元するには以下のコマンドを実行してください：
```bash
git checkout <commit_hash> -- <file_path>
```
例 (Timecard.tsxを復元する場合):
```bash
git checkout HEAD~1 -- frontend/src/components/Timecard.tsx
```

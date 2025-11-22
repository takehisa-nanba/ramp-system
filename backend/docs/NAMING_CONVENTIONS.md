# 📏 RAMP System 開発ガイドライン：命名規則と予約語

このドキュメントは、開発における***名前の衝突***を防ぎ、コードの可読性を保つためのルールブックです。

---

## 🚫 1. 使用禁止・要注意単語 (Reserved Words)

以下の単語は、ライブラリやデータベースの予約語と衝突するため、**変数名やカラム名として単独で使用することを禁止**します。

### 💀 SQLAlchemy / ORM との衝突（絶対禁止）
これらをモデルのカラム名に使うと、起動時にクラッシュします。

| 禁止ワード | 理由 | 代替案（OK） |
| :--- | :--- | :--- |
| **`relationship`** | リレーション定義関数と衝突 | `relation`, `conn`, `link_type` |
| **`metadata`** | モデルのメタデータ属性と衝突 | `meta_info`, `additional_data` |
| **`query`** | クエリオブジェクトと衝突 | `search_query`, `query_text` |

### ⚠️ Python 組み込み関数との衝突（非推奨）
エラーにはなりませんが、バグの温床になります。

| 禁止ワード | 理由 | 代替案（OK） |
| :--- | :--- | :--- |
| **`id`** | `id()` 関数と衝突 | `user_id`, `target_id`, `obj_id` |
| **`type`** | `type()` 関数と衝突 | `record_type`, `category`, `kind` |
| **`list`, `dict`** | 型コンストラクタと衝突 | `user_list`, `data_dict`, `items` |

### 💾 SQL (PostgreSQL) 予約語との衝突
SQLを書く際にエスケープが必要になるため、避けるのが無難です。

* **`user`** （`users` テーブルはOKだが、カラム名は避ける）
* **`order`** （`sort_order` などにする）
* **`group`** （`group_name` などにする）
* **`limit`, `offset`, `where`, `select`**

---

## 📝 2. 命名規則 (Naming Conventions)

「中身を見なくても、名前だけで型（Type）と意味がわかる」状態を目指します。

### 🔹 カラム名の接尾辞（Suffix）

| データ型 | ルール | 良い例 | 悪い例 |
| :--- | :--- | :--- | :--- |
| **外部キー** | **`_id`** を付ける | `user_id`, `supporter_id` | `user`, `supporter` |
| **日時** | **`_at`** (日時) / **`_date`** (日付) | `created_at`, `hire_date` | `time`, `day` |
| **真偽値** | **`is_`**, **`has_`** で始める | `is_active`, `has_consent` | `active`, `consent` |
| **区分/種別** | **`_type`** を付ける | `employment_type` | `employment` |
| **テキスト** | **`_text`**, **`_content`**, **`_notes`** | `support_content_notes` | `memo`, `body` |
| **マスタID** | **`_master_id`** または **`_id`** | `job_title_master_id` | `job_title` |

### 🔹 期間（Period）
開始と終了はセットで命名します。

* ✅ `service_start_date` / `service_end_date`
* ❌ `start` / `finish`

---

## 💡 3. 迷った時の判断基準 (Golden Rule)

> **「その変数名だけで、中身が『文字列』なのか『オブジェクト』なのか『ID』なのか、推測できますか？」**

* **`user`**
    * ⭕ `user = User()` (オブジェクトが入っているならOK)
    * ❌ `user = 1` (IDが入っているなら `user_id` にすべき)
* **`time`**
    * ❌ 単位は？ 秒？ 分？ 日時？
    * ⭕ `work_minutes` (分だとわかる)
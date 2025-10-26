SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'alembic_version' -- ← 目的のテーブル名1
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'attendance_status_master' -- ← 目的のテーブル名2
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'contact_category_master' -- ← 目的のテーブル名3
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'contacts' -- ← 目的のテーブル名4
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'contracts_certificates' -- ← 目的のテーブル名5
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'daily_logs' -- ← 目的のテーブル名6
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'disclosure_type_master' -- ← 目的のテーブル名7
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'employment_type_master' -- ← 目的のテーブル名8
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'employments' -- ← 目的のテーブル名9
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'employments' -- ← 目的のテーブル名10
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'meeting_minutes' -- ← 目的のテーブル名11
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'meeting_type_master' -- ← 目的のテーブル名12
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'prospects' -- ← 目的のテーブル名13
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'referral_source_master' -- ← 目的のテーブル名14
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'role_master' -- ← 目的のテーブル名15
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'status_master' -- ← 目的のテーブル名16
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'support_plans' -- ← 目的のテーブル名17
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'supporters' -- ← 目的のテーブル名18
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'users' -- ← 目的のテーブル名19
ORDER BY
    ordinal_position;

SELECT
    column_name,
    data_type,
    character_maximum_length AS max_length,
    is_nullable             AS nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_schema = 'public'
    AND table_name = 'work_style_master' -- ← 目的のテーブル名20
ORDER BY
    ordinal_position;

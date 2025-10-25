-- publicスキーマ内の全てのテーブル名を取得
SELECT table_name 
FROM information_schema.tables
WHERE table_schema = 'public';
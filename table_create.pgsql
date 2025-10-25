-- ---------------------------------------------------
-- MASTER TABLES (マスタデータ)
-- ---------------------------------------------------

CREATE TABLE status_master (
	id SERIAL NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE referral_source_master (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE role_master (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE employment_type_master (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE work_style_master (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE disclosure_type_master (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE contact_category_master (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE attendance_status_master (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE meeting_type_master (
	id SERIAL NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

-- ---------------------------------------------------
-- CORE APPLICATION TABLES (主要テーブル)
-- ---------------------------------------------------

-- 職員マスタ (Supporters) - role_id は未定義の StaffSalaryMaster で使用されます。
CREATE TABLE supporters (
	id SERIAL NOT NULL, 
	last_name VARCHAR(50) NOT NULL, 
	first_name VARCHAR(50) NOT NULL, 
	last_name_kana VARCHAR(50), 
	first_name_kana VARCHAR(50), 
	role_id INTEGER, 
	hire_date DATE, 
	is_active BOOLEAN, 
	remarks TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(role_id) REFERENCES role_master (id)
);

-- 見込み利用者 (Prospects)
CREATE TABLE prospects (
	id SERIAL NOT NULL, 
	status_id INTEGER, 
	last_name VARCHAR(50) NOT NULL, 
	first_name VARCHAR(50) NOT NULL, 
	last_name_kana VARCHAR(50), 
	first_name_kana VARCHAR(50), 
	phone_number VARCHAR(20), 
	email VARCHAR(100), 
	inquiry_date DATE, 
	referral_source_id INTEGER, 
	referral_source_other VARCHAR(200), 
	notes TEXT, 
	next_action_date DATE, 
	remarks TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(status_id) REFERENCES status_master (id), 
	FOREIGN KEY(referral_source_id) REFERENCES referral_source_master (id)
);

-- 利用者マスタ (Users)
CREATE TABLE users (
	id SERIAL NOT NULL, 
	prospect_id INTEGER, 
	status_id INTEGER, 
	last_name VARCHAR(50) NOT NULL, 
	first_name VARCHAR(50) NOT NULL, 
	last_name_kana VARCHAR(50), 
	first_name_kana VARCHAR(50), 
	primary_supporter_id INTEGER, 
	handbook_type VARCHAR(50), 
	primary_disorder VARCHAR(200), 
	remarks TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (prospect_id), 
	FOREIGN KEY(prospect_id) REFERENCES prospects (id), 
	FOREIGN KEY(status_id) REFERENCES status_master (id), 
	FOREIGN KEY(primary_supporter_id) REFERENCES supporters (id)
);

-- 契約・受給者証情報 (Contracts & Certificates)
CREATE TABLE contracts_certificates (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	certificate_number VARCHAR(100), 
	valid_from DATE, 
	valid_to DATE, 
	max_burden_amount INTEGER, 
	supply_amount INTEGER, 
	remarks TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- 就職・定着情報 (Employments)
CREATE TABLE employments (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	company_name VARCHAR(100), 
	department VARCHAR(100), 
	contact_person VARCHAR(100), 
	contact_person_kana VARCHAR(100), 
	address VARCHAR(200), 
	phone_number VARCHAR(20), 
	email VARCHAR(100), 
	start_date DATE, 
	employment_type_id INTEGER, 
	work_style_id INTEGER, 
	disclosure_type_id INTEGER, 
	remarks TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(employment_type_id) REFERENCES employment_type_master (id), 
	FOREIGN KEY(work_style_id) REFERENCES work_style_master (id), 
	FOREIGN KEY(disclosure_type_id) REFERENCES disclosure_type_master (id)
);

-- 関係機関 (Contacts)
CREATE TABLE contacts (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	category_id INTEGER, 
	organization_name VARCHAR(100), 
	contact_person VARCHAR(100), 
	address VARCHAR(200), 
	phone_number VARCHAR(20), 
	email VARCHAR(100), 
	remarks TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(category_id) REFERENCES contact_category_master (id)
);

-- 行政機関マスタ (Government Offices)
CREATE TABLE government_offices (
	id SERIAL NOT NULL, 
	municipality_name VARCHAR(100), 
	municipality_code VARCHAR(20), 
	department VARCHAR(100), 
	contact_person VARCHAR(100), 
	address VARCHAR(200), 
	phone_number VARCHAR(20), 
	email VARCHAR(100), 
	remarks TEXT, 
	PRIMARY KEY (id)
);

-- 個別支援計画 (Support Plans)
CREATE TABLE support_plans (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	status_id INTEGER, 
	plan_date DATE, 
	main_goal TEXT, 
	short_goal TEXT, 
	supporter_comments TEXT, 
	user_agreement_date DATE, 
	remarks TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(status_id) REFERENCES status_master (id)
);

-- 日々の支援記録 (Daily Logs)
CREATE TABLE daily_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	supporter_id INTEGER, 
	activity_date DATE NOT NULL, 
	attendance_status_id INTEGER, 
	mood_hp INTEGER, 
	mood_mp INTEGER, 
	activity_summary TEXT, 
	user_voice TEXT, 
	supporter_insight TEXT, 
	remarks TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(supporter_id) REFERENCES supporters (id), 
	FOREIGN KEY(attendance_status_id) REFERENCES attendance_status_master (id)
);

-- 支援会議議事録 (Meeting Minutes)
CREATE TABLE meeting_minutes (
	id SERIAL NOT NULL, 
	support_plan_id INTEGER, 
	meeting_date TIMESTAMP WITHOUT TIME ZONE, 
	meeting_type_id INTEGER, 
	attendees TEXT, 
	agenda TEXT, 
	decisions TEXT, 
	next_actions TEXT, 
	remarks TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(support_plan_id) REFERENCES support_plans (id), 
	FOREIGN KEY(meeting_type_id) REFERENCES meeting_type_master (id)
);
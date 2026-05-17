export interface StaffMember {
  id: number;
  staff_code: string;
  name: string;
  last_name: string;
  first_name: string;
  last_name_kana: string;
  first_name_kana: string;
  email: string | null;
  roles: string[];
  role_ids: number[];
  is_active: boolean;
  employment_type: string;
  weekly_scheduled_minutes: number;
  hire_date: string | null;
}

export interface Role {
  id: number;
  name: string;
  scope: 'JOB' | 'CORPORATE' | 'SYSTEM';
}

export interface NewStaffData {
  last_name: string;
  first_name: string;
  last_name_kana: string;
  first_name_kana: string;
  staff_code: string;
  email: string;
  employment_type: string;
  password?: string;
  hire_date: string;
  weekly_scheduled_minutes: number;
  role_ids: number[];
}

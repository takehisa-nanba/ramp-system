export interface JobAssignment {
  id?: number;
  job_title_id: number;
  title_name?: string;
  assigned_minutes: number;
  office_service_configuration_id?: number;
  is_deemed_assignment?: boolean;
  deemed_expiry_date?: string | null;
}

export interface JobTitle {
  id: number;
  title_name: string;
  is_management_role: boolean;
  is_qualified_role: boolean;
}

export interface EmploymentShiftPattern {
  id?: number;
  day_of_week: string; // 'Monday', 'Tuesday' 等
  start_time: string | null; // '09:00' 形式
  end_time: string | null; // '18:00' 形式
  break_minutes: number;
}

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
  allow_overlap_calculation: boolean;
  hire_date: string | null;
  retirement_date?: string | null;
  job_assignments: JobAssignment[];
  shift_patterns?: EmploymentShiftPattern[];
  personal_phone?: string;
  address?: string;
  bank_account_info?: string;
}

export interface Role {
  id: number;
  name: string;
  scope: 'JOB' | 'CORPORATE' | 'SYSTEM' | 'STAFF';
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
  retirement_date?: string | null;
  weekly_scheduled_minutes: number;
  role_ids: number[];
  allow_overlap_calculation?: boolean;
  is_active?: boolean;
  job_assignments?: JobAssignment[];
  shift_patterns?: EmploymentShiftPattern[];
  personal_phone?: string;
  address?: string;
  bank_account_info?: string;
}

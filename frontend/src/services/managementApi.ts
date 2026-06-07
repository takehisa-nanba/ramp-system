import apiClient from './apiClient';

const API_URL = '/management';

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
  day_of_week: string;
  start_time: string | null;
  end_time: string | null;
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
  personal_phone?: string;
  address?: string;
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
}

export interface Role {
  id: number;
  name: string;
  scope: 'JOB' | 'CORPORATE' | 'SYSTEM';
}

export interface OfficeService {
  id?: number;
  service_type_master_id: number;
  jigyosho_bango: string;
  capacity: number;
  manager_supporter_id: number | null;
  initial_designation_date?: string;
  designation_expiry_date?: string;
  regional_category?: string;
  target_disabilities?: Record<string, boolean> | null;
  cooperating_medical_institution?: string;
  manager_name?: string;
}

export interface OfficeSettings {
  id: number;
  corporation_id?: number | null;
  corporation_name?: string;
  corporation_type?: string;
  corporation_number?: string;
  corporation_representative_name?: string;
  corporation_postal_code?: string;
  corporation_address?: string;
  corporation_phone_number?: string;
  tenant_id?: string;
  office_name: string;
  municipality_id?: number;
  full_time_weekly_minutes: number;
  is_active: boolean;
  postal_code?: string;
  address?: string;
  phone_number?: string;
  fax_number?: string;
  email_address?: string;
  representative_name?: string;
  service_config_id?: number;
  service_type_master_id?: number;
  manager_supporter_id?: number | null;
  jigyosho_bango?: string;
  capacity?: number;
  initial_designation_date?: string;
  designation_expiry_date?: string;
  regional_category?: string;
  target_disabilities?: Record<string, boolean> | null;
  cooperating_medical_institution?: string;
  manager_name?: string;
  services?: OfficeService[];
}

export interface AdditiveFiling {
  id: number;
  fee_master_id?: number;
  fee_name: string;
  filing_date: string;
  start_date: string;
  end_date?: string | null;
}

export interface MasterOption {
  id: number;
  name?: string;
  city_name?: string;
  city_code?: string;
  service_name?: string;
  service_code?: string;
}

export interface ManagementMasters {
  municipalities: MasterOption[];
  service_types: MasterOption[];
  genders: MasterOption[];
  disabilities: MasterOption[];
}

export const managementApi = {
  getStaffMembers: async (): Promise<StaffMember[]> => {
    const res = await apiClient.get(`${API_URL}/staff`);
    return res.data;
  },
  getAvailableRoles: async (): Promise<Role[]> => {
    const res = await apiClient.get(`${API_URL}/masters/roles`);
    return res.data;
  },
  getJobTitles: async (): Promise<JobTitle[]> => {
    const res = await apiClient.get(`${API_URL}/masters/job-titles`);
    return res.data;
  },
  getMasters: async (): Promise<ManagementMasters> => {
    const res = await apiClient.get(`${API_URL}/masters`);
    return res.data;
  },
  updateStaffRoles: async (staffId: number, roleIds: number[]): Promise<void> => {
    await apiClient.put(`${API_URL}/staff/${staffId}/roles`, { role_ids: roleIds });
  },
  registerStaff: async (data: any) => {
    const res = await apiClient.post(`${API_URL}/staff`, data);
    return res.data;
  },
  updateStaff: async (staffId: number, data: any): Promise<void> => {
    await apiClient.put(`${API_URL}/staff/${staffId}`, data);
  },
  getOfficeSettings: async (): Promise<OfficeSettings> => {
    const res = await apiClient.get(`${API_URL}/office`);
    return res.data;
  },
  updateOfficeSettings: async (settings: Partial<OfficeSettings>): Promise<void> => {
    await apiClient.put(`${API_URL}/office`, settings);
  },
  getAdditiveFilings: async (): Promise<AdditiveFiling[]> => {
    const res = await apiClient.get(`${API_URL}/office/additive-filings`);
    return res.data;
  },
  addAdditiveFiling: async (data: Omit<AdditiveFiling, 'id' | 'fee_master_id'>): Promise<AdditiveFiling> => {
    const res = await apiClient.post(`${API_URL}/office/additive-filings`, data);
    return res.data;
  },
  deleteAdditiveFiling: async (filingId: number): Promise<void> => {
    await apiClient.delete(`${API_URL}/office/additive-filings/${filingId}`);
  }
};

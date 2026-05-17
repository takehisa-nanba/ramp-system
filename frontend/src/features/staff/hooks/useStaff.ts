import { useState, useEffect, useCallback } from 'react';
import { managementApi } from '../../../services/managementApi';
import type { StaffMember, Role, NewStaffData } from '../types';

export const useStaff = () => {
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedStaff, setSelectedStaff] = useState<StaffMember | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const showMessage = useCallback((type: 'success' | 'error', text: string, duration = 3000) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), duration);
  }, []);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [staffData, roleData] = await Promise.all([
        managementApi.getStaffMembers(),
        managementApi.getAvailableRoles()
      ]);
      setStaff(staffData);
      setRoles(roleData);
      
      // 選択中スタッフの参照を最新データで更新
      if (selectedStaff) {
        const updated = staffData.find((s) => s.id === selectedStaff.id);
        if (updated) setSelectedStaff(updated);
      }
    } catch (err) {
      console.error('Failed to fetch staff data:', err);
      showMessage('error', 'データの取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  }, [selectedStaff, showMessage]);

  useEffect(() => {
    fetchData();
  }, []);

  const handleSaveRoles = async () => {
    if (!selectedStaff) return;
    setIsSaving(true);
    try {
      await managementApi.updateStaffRoles(selectedStaff.id, selectedStaff.role_ids);
      showMessage('success', '権限を更新しました');
      await fetchData();
    } catch (err) {
      console.error(err);
      showMessage('error', '権限の更新に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRegister = async (newStaffData: NewStaffData) => {
    setIsSaving(true);
    try {
      await managementApi.registerStaff(newStaffData);
      showMessage('success', 'スタッフを登録しました');
      await fetchData();
      return true; // 成功
    } catch (err: any) {
      const errorMsg = err.response?.data?.msg || '登録に失敗しました';
      showMessage('error', errorMsg, 5000);
      return false; // 失敗
    } finally {
      setIsSaving(false);
    }
  };

  const handleRoleToggle = (roleId: number) => {
    if (!selectedStaff) return;
    const newRoleIds = selectedStaff.role_ids.includes(roleId)
      ? selectedStaff.role_ids.filter((id) => id !== roleId)
      : [...selectedStaff.role_ids, roleId];
    
    setSelectedStaff({
      ...selectedStaff,
      role_ids: newRoleIds,
      roles: roles.filter((r) => newRoleIds.includes(r.id)).map((r) => r.name)
    });
  };

  const handleUpdateStaff = async (data: any) => {
    if (!selectedStaff) return false;
    setIsSaving(true);
    try {
      await managementApi.updateStaff(selectedStaff.id, data);
      showMessage('success', 'スタッフ情報を更新しました');
      await fetchData();
      return true;
    } catch (err: any) {
      console.error(err);
      const errorMsg = err.response?.data?.msg || '情報の更新に失敗しました';
      showMessage('error', errorMsg, 5000);
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  return {
    staff,
    roles,
    isLoading,
    isSaving,
    selectedStaff,
    message,
    setSelectedStaff,
    handleRoleToggle,
    handleSaveRoles,
    handleRegister,
    handleUpdateStaff,
    refresh: fetchData
  };
};

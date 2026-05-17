import React from 'react';
import { useUserDashboard } from '../hooks/useUserDashboard';
import { UserDashboardView } from './UserDashboardView';

interface UserDashboardProps {
  userName: string | null;
}

const UserDashboard: React.FC<UserDashboardProps> = ({ userName }) => {
  const {
    status,
    goals,
    loading,
    formValues,
    setFormValues,
    isSubmitting,
    handlePunch,
    submitLog
  } = useUserDashboard();

  return (
    <UserDashboardView
      userName={userName}
      status={status}
      goals={goals}
      loading={loading}
      formValues={formValues}
      setFormValues={setFormValues}
      isSubmitting={isSubmitting}
      handlePunch={handlePunch}
      submitLog={submitLog}
    />
  );
};

export default UserDashboard;

import { useState, useEffect, useCallback } from 'react';
import { userSupportApi } from '../services/userSupportApi';
import type { UserStatus, UserGoal, DailyLogSubmission } from '../services/userSupportApi';

export const useUserDashboard = () => {
  const [status, setStatus] = useState<UserStatus | null>(null);
  const [goals, setGoals] = useState<UserGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, goalsRes] = await Promise.all([
        userSupportApi.getStatus(),
        userSupportApi.getGoals()
      ]);
      setStatus(statusRes);
      setGoals(goalsRes.goals);
    } catch (err) {
      console.error('Failed to fetch user data', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePunch = async (type: 'CHECK_IN' | 'CHECK_OUT') => {
    setLoading(true);
    try {
      await userSupportApi.recordAttendance(type);
      await fetchData();
    } catch (err) {
      alert('打刻に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const submitLog = async (section: 'morning' | 'evening') => {
    setIsSubmitting(true);
    try {
      const fields = section === 'morning' ? status?.log_config?.morning_fields : status?.log_config?.evening_fields;
      if (!fields) return;

      const submission: DailyLogSubmission = {
        custom_data: {},
        morning_completed: section === 'morning',
        evening_completed: section === 'evening'
      };

      fields.forEach(field => {
        const val = formValues[field.id];
        if (field.id === 'mood') {
          submission.physical_condition_score = val;
        } else if (field.id === 'review') {
          submission.user_self_evaluation = val;
        } else {
          submission.custom_data![field.id] = val;
        }
      });

      await userSupportApi.submitDailyLog(submission);
      await fetchData();
    } catch (err) {
      alert('保存に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    status,
    goals,
    loading,
    formValues,
    setFormValues,
    isSubmitting,
    handlePunch,
    submitLog,
    refresh: fetchData
  };
};

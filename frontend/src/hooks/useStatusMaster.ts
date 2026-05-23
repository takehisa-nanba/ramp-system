import { useState, useEffect } from 'react';
import { fetchStatusMaster, type StatusMaster } from '../services/userService';

export const useStatusMaster = () => {
  const [statuses, setStatuses] = useState<StatusMaster[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStatusMaster().then(data => {
      setStatuses(data);
      setLoading(false);
    }).catch(err => {
      console.error('Failed to load status master', err);
      setLoading(false);
    });
  }, []);

  return { statuses, loading };
};

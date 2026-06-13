import React, { useEffect, useState } from 'react';
import { fetchUserPii } from '../../services/userService';
import { UserCertificateTab } from '../../components/common/UserCertificateTab';

export const UserCertificateTabPage: React.FC<{ userId: number }> = ({ userId }) => {
  const [certificates, setCertificates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCertificates = async () => {
    try {
      setLoading(true);
      const data = await fetchUserPii(userId);
      setCertificates(data.certificates || []);
    } catch (err) {
      console.error(err);
      setError('受給者証情報の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCertificates();
  }, [userId]);

  if (loading) {
    return (
      <div className="flex justify-center p-12">
        <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error) {
    return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <UserCertificateTab 
        userId={userId} 
        certificates={certificates} 
        onUpdateSuccess={loadCertificates} 
      />
    </div>
  );
};

import { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';

export interface Municipality {
  id: number;
  city_name: string;
  city_code: string;
}

export interface ServiceType {
  id: number;
  service_name: string;
  service_code: string;
}

export interface Gender {
  id: number;
  name: string;
}

export interface Disability {
  id: number;
  name: string;
}

export interface MastersData {
  municipalities: Municipality[];
  service_types: ServiceType[];
  genders: Gender[];
  disabilities: Disability[];
}

export const useMasters = () => {
  const [masters, setMasters] = useState<MastersData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMasters = async () => {
      try {
        const response = await apiClient.get<MastersData>('/management/masters');
        setMasters(response.data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch masters:', err);
        setError('マスターデータの取得に失敗しました。');
      } finally {
        setLoading(false);
      }
    };

    fetchMasters();
  }, []);

  return { masters, loading, error };
};

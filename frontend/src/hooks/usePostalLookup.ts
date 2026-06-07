import { useState } from 'react';

export interface PostalLookupResult {
  loading: boolean;
  error: string | null;
  lookupAddress: (zipcode: string) => Promise<string | null>;
}

export const usePostalLookup = (): PostalLookupResult => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const lookupAddress = async (zipcode: string): Promise<string | null> => {
    // ハイフンを除去して7桁の数値か判定
    const cleanZip = zipcode.replace(/[^\d]/g, '');
    if (cleanZip.length !== 7) {
      setError('郵便番号は7桁の半角数字で入力してください。');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      // Zipcloud API は CORS 許可されており、直接ブラウザからフェッチ可能です
      const response = await fetch(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${cleanZip}`);
      if (!response.ok) {
        throw new Error('郵便番号APIの接続に失敗しました。');
      }

      const data = await response.json();
      if (data.status !== 200) {
        throw new Error(data.message || '住所情報の取得に失敗しました。');
      }

      if (!data.results || data.results.length === 0) {
        setError('該当する住所が見つかりませんでした。');
        return null;
      }

      const result = data.results[0];
      // 都道府県 + 市区町村 + 町域 を結合
      const fullAddress = `${result.address1}${result.address2}${result.address3}`;
      return fullAddress;
    } catch (err: any) {
      setError(err.message || 'ネットワークエラーが発生しました。');
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    error,
    lookupAddress,
  };
};

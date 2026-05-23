/**
 * 入力画面共通で利用する文字列操作・入力支援ヘルパー関数群
 */

/**
 * ひらがなをカタカナに変換する
 */
export const toKatakana = (str: string): string => {
  return str.replace(/[ぁ-ん]/g, (s) => String.fromCharCode(s.charCodeAt(0) + 0x60));
};

/**
 * 文字列がひらがな、カタカナ、スペースのみで構成されているか判定する
 */
export const isKanaOrHira = (str: string): boolean => {
  return /^[ぁ-んァ-ヶー\s]*$/.test(str);
};

/**
 * 郵便番号から数字のみを抽出する（ハイフン除去等）
 */
export const cleanZipCode = (zip: string): string => {
  return zip.replace(/[^\d]/g, '');
};

/**
 * 郵便番号から住所をフェッチする共通関数
 */
export interface ZipAddressResult {
  success: boolean;
  address?: string;
  error?: string;
}

export const fetchAddressByZip = async (zip: string): Promise<ZipAddressResult> => {
  const cleaned = cleanZipCode(zip);
  if (cleaned.length !== 7) {
    return { success: false, error: '郵便番号は7桁で入力してください。' };
  }

  try {
    const response = await fetch(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${cleaned}`);
    const data = await response.json();
    if (data.status === 200 && data.results && data.results[0]) {
      const result = data.results[0];
      const fullAddress = `${result.address1}${result.address2}${result.address3}`;
      return { success: true, address: fullAddress };
    } else {
      return { success: false, error: '該当する住所が見つかりませんでした。' };
    }
  } catch {
    return { success: false, error: '住所の取得に失敗しました。' };
  }
};

// frontend/src/utils/dateUtils.ts

/**
 * ブラウザのローカル日時（JSTなど）に基づいて YYYY-MM-DD 文字列を返す。
 * toISOString() のようにUTCに変換しないため、日本時間の深夜帯（0:00〜8:59）でも前日になりません。
 */
export const getLocalDateString = (d: Date = new Date()): string => {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * 暦上のnか月後を計算するヘルパー（Pythonの relativedelta(months=n) と同等）
 * 例: 2026-08-31 + 6 months -> 2027-02-28
 */
export const addCalendarMonths = (dateStr: string, months: number): string => {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-').map(Number);
  const targetMonthIndex = m - 1 + months;
  const targetYear = y + Math.floor(targetMonthIndex / 12);
  const targetMonth = ((targetMonthIndex % 12) + 12) % 12 + 1;

  const lastDayOfTargetMonth = new Date(targetYear, targetMonth, 0).getDate();
  const clampedDay = Math.min(d, lastDayOfTargetMonth);

  return `${targetYear}-${String(targetMonth).padStart(2, '0')}-${String(clampedDay).padStart(2, '0')}`;
};

/**
 * 計画開始日から標準の終了予定日（原則: start_date + 6 calendar months - 1 day）を算出
 * 例: 2026-09-01 -> 2027-02-28
 */
export const calculateDefaultPlanEndDate = (dateStr: string): string => {
  if (!dateStr) return '';
  const sixMonthsLater = addCalendarMonths(dateStr, 6);
  const [y, m, d] = sixMonthsLater.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() - 1);
  return getLocalDateString(dt);
};

/**
 * 指定日の翌日を算出（次計画開始予定日）
 */
export const calculateNextDay = (dateStr: string): string => {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + 1);
  return getLocalDateString(dt);
};

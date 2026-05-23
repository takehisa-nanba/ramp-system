export interface ShiftPattern {
  day_of_week: string;
  start_time: string;
  end_time: string;
  break_minutes: number;
  is_active: boolean;
}

export interface JobAssignment {
  job_title_id: number;
  hours: string;
  is_deemed_assignment?: boolean;
  deemed_expiry_date?: string;
}

/**
 * 曜日ごとの実働時間（時間換算）を計算する
 * @param pattern シフトパターンのオブジェクト
 * @returns 実働時間（時間）
 */
export const calculateShiftWorkingHours = (pattern: ShiftPattern): number => {
  if (!pattern.is_active || !pattern.start_time || !pattern.end_time) return 0;
  const [sh, sm] = pattern.start_time.split(':').map(Number);
  const [eh, em] = pattern.end_time.split(':').map(Number);
  
  const startMinutes = sh * 60 + sm;
  const endMinutes = eh * 60 + em;
  
  if (endMinutes <= startMinutes) return 0;
  
  const workingMinutes = (endMinutes - startMinutes) - pattern.break_minutes;
  return Math.max(0, workingMinutes / 60);
};

/**
 * 有効な全シフトパターンの合計実働時間を計算する
 * @param shiftPatterns シフトパターンの配列
 * @returns 合計実働時間（時間）
 */
export const calculateTotalShiftWorkingHours = (shiftPatterns: ShiftPattern[]): number => {
  return shiftPatterns.reduce((sum, p) => sum + calculateShiftWorkingHours(p), 0);
};

/**
 * 兼務時間の合計を計算する
 * @param assignments 兼務情報の配列
 * @returns 兼務合計時間（時間）
 */
export const calculateTotalAssignedHours = (assignments: JobAssignment[]): number => {
  return assignments.reduce((sum, item) => sum + (parseFloat(item.hours) || 0), 0);
};

/**
 * 兼務時間が週の契約時間を超過していないか（特例重複許可がOFFの場合）を検証する
 */
export const validateAssignedHoursMismatch = (
  contractHours: number,
  assignments: JobAssignment[],
  isMultipleJobs: boolean,
  allowOverlap: boolean
): boolean => {
  if (!isMultipleJobs || allowOverlap) return false;
  const assignedHoursSum = calculateTotalAssignedHours(assignments);
  return assignedHoursSum > contractHours;
};

/**
 * シフトの合計時間が週の契約時間と一致しているかを検証する
 */
export const validateShiftHoursMismatch = (
  contractHours: number,
  shiftPatterns: ShiftPattern[],
  isShiftPatternEnabled: boolean
): boolean => {
  if (!isShiftPatternEnabled) return false;
  const totalShiftWorkingHours = calculateTotalShiftWorkingHours(shiftPatterns);
  return Math.abs(totalShiftWorkingHours - contractHours) > 0.01;
};

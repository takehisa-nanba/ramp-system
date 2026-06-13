// frontend/src/pages/tabs/UserScheduleActualsTab.tsx

import React, { useEffect, useState } from 'react';
import { fetchUserDailySchedules } from '../../services/userService';
import type { UserDailyScheduleItem } from '../../services/userService';
import { Button, Table, message, DatePicker, Space } from 'antd';
import dayjs, { Dayjs } from 'dayjs';

const DAY_OF_WEEK_JA: Record<string, string> = {
  Monday: '月曜日',
  Tuesday: '火曜日',
  Wednesday: '水曜日',
  Thursday: '木曜日',
  Friday: '金曜日',
  Saturday: '土曜日',
  Sunday: '日曜日',
};

const LOCATION_TYPE_JA: Record<string, string> = {
  ON_SITE: '施設内支援',
  OFF_SITE_SUPPORT: '施設外支援',
  TRANSITION_PREP: '移行準備',
  OFF_SITE_WORK: '施設外就労',
  AT_HOME: '在宅支援',
};

const SCHEDULE_STATUS_JA: Record<string, string> = {
  NORMAL: '通常',
  EXTRA: '臨時追加',
  SUBSTITUTED: '時間変更',
};

const APPROVAL_STATUS_JA: Record<string, string> = {
  APPROVED: '承認済',
  CANCELLED: 'キャンセル',
  REQUESTED: '申請中',
  REJECTED: '却下',
  PENDING: '保留中',
};

interface Props {
  userId: number;
}

export const UserScheduleActualsTab: React.FC<Props> = ({ userId }) => {
  const [dailySchedules, setDailySchedules] = useState<UserDailyScheduleItem[]>([]);
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs().startOf('month'));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentMonth, userId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const start_date = currentMonth.format('YYYY-MM-DD');
      const end_date = currentMonth.endOf('month').format('YYYY-MM-DD');

      const res = await fetchUserDailySchedules(userId, { start_date, end_date });
      setDailySchedules(res.items);
    } catch (err) {
      console.error(err);
      message.error('データ取得に失敗しました');
    }
    setLoading(false);
  };

  return (
    <div className="animate-in fade-in duration-500">
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-black text-slate-800 flex items-center gap-2">
            🗓️ 確定日別スケジュール
          </h2>
          <Space>
            <Button onClick={() => setCurrentMonth(currentMonth.subtract(1, 'month'))}>前月</Button>
            <DatePicker 
              picker="month" 
              value={currentMonth} 
              onChange={(d) => d && setCurrentMonth(d.startOf('month'))} 
              allowClear={false} 
            />
            <Button onClick={() => setCurrentMonth(currentMonth.add(1, 'month'))}>翌月</Button>
          </Space>
        </div>
        <Table
          dataSource={dailySchedules.map((d) => ({ ...d, key: d.id }))}
          loading={loading}
          bordered
          pagination={false}
          size="small"
          columns={[
            { 
              title: '日付', 
              dataIndex: 'date', 
              key: 'date',
              render: (v: string) => {
                const d = dayjs(v);
                return `${d.format('MM/DD')} (${DAY_OF_WEEK_JA[d.format('dddd')] || d.format('ddd')})`;
              }
            },
            { title: '開始', dataIndex: 'start_time', key: 'start', render: (v: string | null) => v?.slice(0,5) || '-' },
            { title: '終了', dataIndex: 'end_time', key: 'end', render: (v: string | null) => v?.slice(0,5) || '-' },
            { title: '予定', dataIndex: 'is_scheduled', key: 'scheduled', render: (v: boolean) => (v ? 'あり' : 'なし') },
            { title: '支援区分', dataIndex: 'location_type', key: 'location_type', render: (v: string) => LOCATION_TYPE_JA[v] || v || '-' },
            { title: '状態', dataIndex: 'schedule_status', key: 'schedule_status', render: (v: string) => SCHEDULE_STATUS_JA[v] || v || '-' },
            { title: '承認', dataIndex: 'approval_status', key: 'approval_status', render: (v: string) => APPROVAL_STATUS_JA[v] || v || '-' },
          ]}
        />
      </div>
    </div>
  );
};

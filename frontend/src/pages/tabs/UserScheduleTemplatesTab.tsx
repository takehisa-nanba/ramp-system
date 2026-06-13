// frontend/src/pages/tabs/UserScheduleTemplatesTab.tsx

import React, { useEffect, useState } from 'react';
import {
  fetchUserScheduleTemplates,
  saveUserScheduleTemplates,
} from '../../services/userService';
import { managementApi } from '../../services/managementApi';
import type { UserScheduleTemplateItem } from '../../services/userService';
import { Button, Input, Table, message, Radio } from 'antd';

const DAY_OF_WEEK_JA: Record<string, string> = {
  Monday: '月曜日',
  Tuesday: '火曜日',
  Wednesday: '水曜日',
  Thursday: '木曜日',
  Friday: '金曜日',
  Saturday: '土曜日',
  Sunday: '日曜日',
};

interface Props {
  userId: number;
}

export const UserScheduleTemplatesTab: React.FC<Props> = ({ userId }) => {
  const [templates, setTemplates] = useState<UserScheduleTemplateItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [tmplRes, officeRes] = await Promise.all([
        fetchUserScheduleTemplates(userId),
        managementApi.getOfficeSettings(),
      ]);
      
      const defaults = officeRes || {};
      const newTemplates = tmplRes.items.map((t: any) => ({
        ...t,
        start_time: t.is_scheduled && !t.start_time ? defaults.default_start_time ?? '' : t.start_time,
        end_time: t.is_scheduled && !t.end_time ? defaults.default_end_time ?? '' : t.end_time,
      }));
      setTemplates(newTemplates);
    } catch (err) {
      console.error(err);
      message.error('データ取得に失敗しました');
    }
    setLoading(false);
  };

  const handleTemplateChange = (index: number, field: keyof UserScheduleTemplateItem, value: any) => {
    const newTemplates = [...templates];
    // @ts-ignore
    newTemplates[index][field] = value;
    setTemplates(newTemplates);
  };

  const saveTemplates = async () => {
    for (const t of templates) {
      if (t.is_scheduled && t.start_time && t.end_time) {
        const [sh, sm] = t.start_time.split(':').map(Number);
        const [eh, em] = t.end_time.split(':').map(Number);
        if (eh * 60 + em <= sh * 60 + sm) {
          message.error(`${DAY_OF_WEEK_JA[t.day_of_week] || t.day_of_week} の終了時間は開始時間より後にしてください`);
          return;
        }
      }
    }
    const res = await saveUserScheduleTemplates(userId, templates);
    if (res.success) {
      message.success('テンプレートを保存しました');
      loadAll();
    } else {
      message.error(res.message);
    }
  };

  return (
    <div className="animate-in fade-in duration-500">
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
        <h2 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
          📅 曜日別予定テンプレート
        </h2>
        <Table
          dataSource={templates.map((t, idx) => ({ ...t, key: idx }))}
          pagination={false}
          loading={loading}
          bordered
          size="middle"
          columns={[
            {
              title: '曜日',
              dataIndex: 'day_of_week',
              key: 'day',
              render: (value: string) => DAY_OF_WEEK_JA[value] || value,
            },
            {
              title: '通所',
              dataIndex: 'is_scheduled',
              key: 'is_scheduled',
              render: (value: boolean, _: any, idx: number) => (
                <Radio.Group
                  value={value ? true : false}
                  onChange={(e) => handleTemplateChange(idx, 'is_scheduled', e.target.value)}
                >
                  <Radio.Button value={true}>はい</Radio.Button>
                  <Radio.Button value={false}>いいえ</Radio.Button>
                </Radio.Group>
              ),
            },
            {
              title: '開始時刻',
              dataIndex: 'start_time',
              key: 'start_time',
              render: (value: string | null, _: any, idx: number) => (
                <Input
                  type="time"
                  value={value ?? ''}
                  onChange={(e) => handleTemplateChange(idx, 'start_time', e.target.value)}
                  disabled={!templates[idx].is_scheduled}
                />
              ),
            },
            {
              title: '終了時刻',
              dataIndex: 'end_time',
              key: 'end_time',
              render: (value: string | null, _: any, idx: number) => (
                <Input
                  type="time"
                  value={value ?? ''}
                  onChange={(e) => handleTemplateChange(idx, 'end_time', e.target.value)}
                  disabled={!templates[idx].is_scheduled}
                />
              ),
            },
          ]}
        />
        <Button type='primary' className="mt-3" onClick={saveTemplates}>
          テンプレート保存
        </Button>
      </div>
    </div>
  );
};

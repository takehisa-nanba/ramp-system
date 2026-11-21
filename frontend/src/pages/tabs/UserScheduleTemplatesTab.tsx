import { ClockTimeInput } from '../../components/common/ClockTimeInput';
import { CalendarDateInput } from '../../components/common/CalendarDateInput';
import apiClient from '../../services/apiClient';
import dayjs from 'dayjs';
import axios from 'axios';
// frontend/src/pages/tabs/UserScheduleTemplatesTab.tsx

import React, { useEffect, useState } from 'react';
import {
  fetchUserScheduleTemplates,
  saveUserScheduleTemplates,
} from '../../services/userService';
import { managementApi } from '../../services/managementApi';
import type { UserScheduleTemplateItem } from '../../services/userService';
import { Button, Table, message, Radio, Modal } from 'antd';

type BulkResult = { created_count: number; skipped_count: number; items: { date: string; start_time: string; end_time: string; action: string }[] };

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
  const [baseStart, setBaseStart] = useState('09:00');
  const [baseEnd, setBaseEnd] = useState('15:00');
  const [selectedDays, setSelectedDays] = useState(['Monday','Tuesday','Wednesday','Thursday','Friday']);
  const [targetMonth, setTargetMonth] = useState(dayjs().format('YYYY-MM'));
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<{ result: BulkResult; payload: { month: string; templates: UserScheduleTemplateItem[] }; userId: number } | null>(null);
  const showFailure = (error: unknown) => {
    const data = axios.isAxiosError(error) ? error.response?.data : null;
    message.error(data?.error?.message || data?.message || '予定を作成できませんでした。入力内容を確認してください。');
  };
  const applyBase = () => {
    if (!baseStart || !baseEnd || baseEnd <= baseStart || !selectedDays.length) {
      message.warning('対象曜日と、開始より後の終了時刻を指定してください。'); return;
    }
    setTemplates(templates.map(t => ({ ...t, is_scheduled: selectedDays.includes(t.day_of_week),
      start_time: selectedDays.includes(t.day_of_week) ? baseStart : t.start_time,
      end_time: selectedDays.includes(t.day_of_week) ? baseEnd : t.end_time })));
    message.success('下の曜日別設定に反映しました。曜日ごとに調整できます。');
  };
  const previewBulk = async () => {
    setBusy(true);
    const payload = { month: targetMonth, templates };
    try {
      const { data } = await apiClient.post<BulkResult>(`/users/${userId}/schedule-templates/bulk-preview`, payload);
      setPreview({ result: data, payload, userId });
    } catch (error) { showFailure(error); } finally { setBusy(false); }
  };
  const createBulk = async () => {
    if (!preview || preview.userId !== userId) return;
    setBusy(true);
    try {
      const { data } = await apiClient.post<BulkResult>(`/users/${userId}/schedule-templates/bulk-create`, preview.payload);
      message.success(`${data.created_count}件作成しました。既存予定・実績・申請のある${data.skipped_count}件は保持しました。`);
      setPreview(null);
    } catch (error) { showFailure(error); } finally { setBusy(false); }
  };

  useEffect(() => {
    setPreview(null);
    setTemplates([]);
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [tmplRes, officeRes] = await Promise.all([
        fetchUserScheduleTemplates(userId),
        // Office settings are optional defaults; their permission must not block scheduling.
        managementApi.getOfficeSettings().catch(() => null),
      ]);
      
      const newTemplates = tmplRes.items.map((t: any) => ({
        ...t,
        start_time: t.is_scheduled && !t.start_time ? officeRes?.default_start_time ?? '' : t.start_time,
        end_time: t.is_scheduled && !t.end_time ? officeRes?.default_end_time ?? '' : t.end_time,
      }));
      setTemplates(newTemplates);
    } catch (err) {
      console.error(err);
      message.error('データ取得に失敗しました');
    }
    setLoading(false);
  };

  const handleTemplateChange = (index: number, field: keyof UserScheduleTemplateItem, value: any) => {
    setTemplates(templates.map((t, i) => i === index ? { ...t, [field]: value } : t));
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
        <section className="rounded-xl bg-indigo-50 p-4 mb-5 space-y-3">
          <h3 className="font-bold text-indigo-900">基準時間を曜日に設定</h3>
          <div className="grid grid-cols-2 gap-3 max-w-md">
            <label>開始時刻<ClockTimeInput aria-label="基準の開始時刻" value={baseStart} onChange={e => setBaseStart(e.target.value)} /></label>
            <label>終了時刻<ClockTimeInput aria-label="基準の終了時刻" value={baseEnd} onChange={e => setBaseEnd(e.target.value)} /></label>
          </div>
          <div className="flex flex-wrap gap-3">{Object.entries(DAY_OF_WEEK_JA).map(([key, label]) =>
            <label key={key} className="flex items-center gap-1 p-2 bg-white rounded-lg">
              <input type="checkbox" checked={selectedDays.includes(key)} onChange={e => setSelectedDays(e.target.checked ? [...selectedDays,key] : selectedDays.filter(d => d !== key))} />{label}
            </label>)}</div>
          <Button onClick={applyBase} disabled={loading || busy || !templates.length}>曜日別設定に反映</Button>
          <p className="text-sm text-slate-600">選択した曜日を通所日に設定します。下の表で曜日ごとに時間を変更できます。</p>
        </section>
        <Table
          dataSource={templates.map((t, idx) => ({ ...t, key: idx }))}
          pagination={false}
          loading={loading}
          bordered
          size="middle"
          scroll={{ x: 560 }}
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
                <ClockTimeInput
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
                <ClockTimeInput
                  type="time"
                  value={value ?? ''}
                  onChange={(e) => handleTemplateChange(idx, 'end_time', e.target.value)}
                  disabled={!templates[idx].is_scheduled}
                />
              ),
            },
          ]}
        />
        <Button type='primary' className="mt-3" onClick={saveTemplates} disabled={loading || busy || !templates.length}>
          テンプレート保存
        </Button>
        <section className="border-t border-slate-200 mt-6 pt-5 space-y-3">
          <h3 className="font-bold text-slate-800">月間予定を一括作成</h3>
          <p className="text-sm text-slate-600">上の曜日別設定から作成します。既存予定（休み・取消を含む）や実績・申請がある日は保持します。祝日も曜日設定に従います。</p>
          <div className="flex flex-wrap items-end gap-3">
            <label>対象月<CalendarDateInput type="month" required value={targetMonth} onChange={e => setTargetMonth(e.target.value)} /></label>
            <Button type="primary" loading={busy} disabled={loading || !templates.length} onClick={previewBulk}>作成内容を確認</Button>
          </div>
          <p className="text-xs text-slate-500">一括作成ではテンプレート自体は保存しません。今後も使う曜日設定は「テンプレート保存」で保存してください。</p>
        </section>
      </div>
      <Modal title={`${preview?.payload.month ?? ''} の予定を確認`} open={!!preview} onCancel={() => { if (!busy) setPreview(null); }}
        maskClosable={!busy} closable={!busy} keyboard={!busy} onOk={createBulk} okText="この内容で一括作成" cancelText="戻る"
        confirmLoading={busy} cancelButtonProps={{ disabled: busy }} okButtonProps={{ disabled: !preview?.result.created_count || busy }}>
        <p className="mb-3">新規作成 {preview?.result.created_count ?? 0}件 ／ 保持 {preview?.result.skipped_count ?? 0}件</p>
        <div className="max-h-80 overflow-y-auto"><table className="w-full text-sm"><thead><tr><th>日付</th><th>設定時間</th><th>処理</th></tr></thead><tbody>
          {preview?.result.items.map(item => <tr key={item.date} className="border-t border-slate-100"><td className="py-2">{item.date}</td><td>{item.start_time}〜{item.end_time}</td><td>{item.action === 'CREATE' ? '新規作成' : item.action === 'EXISTING' ? '既存を保持' : '実績・申請を保持'}</td></tr>)}
        </tbody></table></div>
        <p className="mt-3 text-xs text-slate-500">確認後に予定が追加された場合も、作成時に再確認して保持します。</p>
      </Modal>
    </div>
  );
};

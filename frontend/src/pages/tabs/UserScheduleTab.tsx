// frontend/src/pages/tabs/UserScheduleTab.tsx

import React, { useEffect, useState, forwardRef, useImperativeHandle } from 'react';
import {
  fetchUserScheduleTemplates,
  saveUserScheduleTemplates,
  fetchUserScheduleRequests,
  createUserScheduleRequest,
  fetchUserDailySchedules,
  decideUserScheduleRequest,
} from '../../services/userService';
import { managementApi } from '../../services/managementApi';
import type {
  UserScheduleTemplateItem,
  UserScheduleRequestItem,
  UserDailyScheduleItem,
} from '../../services/userService';
import { Button, Input, Select, Table, message, Modal, Form, Radio, DatePicker, Space } from 'antd';
import type { FormInstance } from 'antd';
import dayjs, { Dayjs } from 'dayjs';


/**
 * 利用者詳細ページに表示される「予定管理」タブ。
 * - 契約曜日テンプレートの閲覧・編集
 * - 予定変更・欠席・追加の申請一覧・作成
 * - 確定した日別予定の一覧表示
 *
 * UI/UX デザインは RAMP の UI_UX_RULES に沿い、
 * - 時間入力は TimeDurationInput（ここでは Ant Design の TimePicker を利用）
 * - 日付は DatePicker
 * - 必須文字数 10 以上の理由入力はバリデーションで enforced
 * - カラーパレットはダークモード対応のグラデーション
 */

const { Option } = Select;
const { TextArea } = Input;

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

const REQUEST_TYPE_JA: Record<string, string> = {
  ABSENCE: '欠席',
  EXTRA_DAY: '臨時追加',
  SHIFT_TIME: '時間変更',
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

const UserScheduleTab: React.FC<Props> = ({ userId }) => {
  // --- State ---
  const [templates, setTemplates] = useState<UserScheduleTemplateItem[]>([]);
  const [requests, setRequests] = useState<UserScheduleRequestItem[]>([]);
  const [dailySchedules, setDailySchedules] = useState<UserDailyScheduleItem[]>([]);
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs().startOf('month'));
  
  const [loading, setLoading] = useState(false);

  // --- Effects ---
  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const start_date = currentMonth.format('YYYY-MM-DD');
      const end_date = currentMonth.endOf('month').format('YYYY-MM-DD');

      const [tmplRes, reqRes, dailyRes, officeRes] = await Promise.all([
        fetchUserScheduleTemplates(userId),
        fetchUserScheduleRequests(userId),
        fetchUserDailySchedules(userId, { start_date, end_date }),
        managementApi.getOfficeSettings(),
      ]);
      
      // Apply defaults if template is scheduled but times are missing
      const defaults = officeRes || {};
      const newTemplates = tmplRes.items.map((t: any) => ({
        ...t,
        start_time: t.is_scheduled && !t.start_time ? defaults.default_start_time ?? '' : t.start_time,
        end_time: t.is_scheduled && !t.end_time ? defaults.default_end_time ?? '' : t.end_time,
      }));
      setTemplates(newTemplates);
      setRequests(reqRes.items);
      setDailySchedules(dailyRes.items);
    } catch (err) {
      console.error(err);
      message.error('データ取得に失敗しました');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentMonth]);

  // --- Template Handlers ---
  const handleTemplateChange = (index: number, field: keyof UserScheduleTemplateItem, value: any) => {
    const newTemplates = [...templates];
    // @ts-ignore
    newTemplates[index][field] = value;
    setTemplates(newTemplates);
  };

  const saveTemplates = async () => {
    // バリデーション: 開始 < 終了
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

  // --- Request Handlers ---
  const openCreateRequestModal = () => {
    let formRef: { submit: () => Promise<void> } | null = null;

    Modal.confirm({
      title: '予定変更・欠席・追加の申請',
      icon: null,
      okText: '作成',
      cancelText: 'キャンセル',
      content: <CreateRequestForm userId={userId} onCreated={loadAll} ref={(ref) => { formRef = ref; }} />,
      onOk: async () => {
        if (formRef) {
          try {
            await formRef.submit();
          } catch {
            // バリデーションエラー時は閉じない
            return Promise.reject();
          }
        }
      },
    });
  };

  const handleDecision = async (requestId: number, status: 'APPROVED' | 'REJECTED') => {
    const decisionFormRef = React.createRef<FormInstance>();

    Modal.confirm({
      title: `${status === 'APPROVED' ? '承認' : '却下'}の確認`,
      content: (
        <Form ref={decisionFormRef} layout='vertical'>
          <Form.Item
            label='判断理由 (10文字以上)'
            name='decision_reason'
            rules={[{ required: true, min: 10, message: '10文字以上入力してください' }]}
          >
            <TextArea rows={3} />
          </Form.Item>
        </Form>
      ),
      onOk: async () => {
        if (!decisionFormRef.current) return;
        try {
          const values = await decisionFormRef.current.validateFields();
          await decideUserScheduleRequest(requestId, { status, decision_reason: values.decision_reason });
          message.success('処理が完了しました');
          loadAll();
        } catch (e: any) {
          if (e?.errorFields) {
            // バリデーションエラー時はモーダルを閉じない
            return Promise.reject();
          }
          console.error(e);
          message.error('処理に失敗しました');
        }
      },
    });
  };

  // --- Render ---
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* 曜日別テンプレート */}
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

      {/* 予定変更・欠席・追加申請 */}
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-black text-slate-800 flex items-center gap-2">
            📝 予定変更・欠席・追加申請
          </h2>
          <Button type='primary' onClick={openCreateRequestModal}>
            申請作成
          </Button>
        </div>
        <Table
          dataSource={requests.map((r) => ({ ...r, key: r.id }))}
          loading={loading}
          bordered
          size="middle"
          columns={[
            { title: '日付', dataIndex: 'target_date', key: 'date' },
            { title: '種別', dataIndex: 'request_type', key: 'type', render: (v: string) => REQUEST_TYPE_JA[v] || v },
            { title: '理由', dataIndex: 'request_reason', key: 'reason' },
            { title: '状態', dataIndex: 'request_status', key: 'status', render: (v: string) => APPROVAL_STATUS_JA[v] || v },
            {
              title: '操作',
              key: 'action',
              render: (_, record) =>
                record.request_status === 'PENDING' ? (
                  <span className="flex gap-2">
                    <Button
                      size='small'
                      type='primary'
                      onClick={() => handleDecision(record.id, 'APPROVED')}
                    >
                      承認
                    </Button>
                    <Button size='small' danger onClick={() => handleDecision(record.id, 'REJECTED')}>
                      却下
                    </Button>
                  </span>
                ) : null,
            },
          ]}
        />
      </div>

      {/* 確定日別スケジュール */}
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

/**
 * 申請作成用のサブコンポーネント（モーダル内で使用）
 */
interface CreateRequestFormProps {
  userId: number;
  onCreated: () => void;
}

interface CreateRequestFormRef {
  submit: () => Promise<void>;
}

const CreateRequestForm = forwardRef<CreateRequestFormRef, CreateRequestFormProps>(
  ({ userId, onCreated }, ref) => {
    const [form] = Form.useForm();

    const submit = async () => {
      try {
        const values = await form.validateFields();
        await createUserScheduleRequest(userId, {
          target_date: values.target_date,
          request_type: values.request_type,
          request_reason: values.request_reason,
          requested_start_time: values.requested_start_time ?? null,
          requested_end_time: values.requested_end_time ?? null,
        });
        message.success('申請が作成されました');
        onCreated();
        Modal.destroyAll();
      } catch (e) {
        console.error(e);
        throw e;
      }
    };

    useImperativeHandle(ref, () => ({
      submit,
    }));

    return (
      <Form form={form} layout='vertical'>
        <Form.Item name='userId' initialValue={userId} hidden />
        <Form.Item
          name='target_date'
          label='対象日付'
          rules={[{ required: true, message: '日付を選択してください' }]}
        >
          <Input type='date' />
        </Form.Item>
        <Form.Item
          name='request_type'
          label='種別'
          rules={[{ required: true }]}
        >
          <Select placeholder='選択'>
            <Option value='ABSENCE'>欠席</Option>
            <Option value='EXTRA_DAY'>臨時追加</Option>
            <Option value='SHIFT_TIME'>時間変更</Option>
          </Select>
        </Form.Item>
        <Form.Item
          name='request_reason'
          label='理由 (10文字以上)'
          rules={[{ required: true, min: 10, message: '10文字以上入力してください' }]}
        >
          <TextArea rows={3} />
        </Form.Item>
        <Form.Item name='requested_start_time' label='開始時刻'>
          <Input type="time" />
        </Form.Item>
        <Form.Item name='requested_end_time' label='終了時刻'>
          <Input type="time" />
        </Form.Item>
      </Form>
    );
  }
);

export default UserScheduleTab;

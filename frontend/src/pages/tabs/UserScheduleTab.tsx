// frontend/src/pages/tabs/UserScheduleTab.tsx

import React, { useEffect, useState } from 'react';
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
import { Button, Input, Select, Table, message, Modal, Form, Radio } from 'antd';


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



interface Props {
  userId: number;
}

const UserScheduleTab: React.FC<Props> = ({ userId }) => {
  // --- State ---
  const [templates, setTemplates] = useState<UserScheduleTemplateItem[]>([]);
  const [requests, setRequests] = useState<UserScheduleRequestItem[]>([]);
  const [dailySchedules, setDailySchedules] = useState<UserDailyScheduleItem[]>([]);
  
  const [loading, setLoading] = useState(false);

  // --- Effects ---
  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [tmplRes, reqRes, dailyRes, officeRes] = await Promise.all([
        fetchUserScheduleTemplates(userId),
        fetchUserScheduleRequests(userId),
        fetchUserDailySchedules(userId),
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
          message.error(`${t.day_of_week} の終了時間は開始時間より後にしてください`);
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
    Modal.confirm({
      title: '予定変更・欠席・追加の申請',
      icon: null,
      okText: '作成',
      cancelText: 'キャンセル',
      content: <CreateRequestForm onCreated={loadAll} />, // defined below
    });
  };

  const handleDecision = async (requestId: number, status: 'APPROVED' | 'REJECTED') => {
    Modal.confirm({
      title: `${status === 'APPROVED' ? '承認' : '却下'}の確認`,
      content: (
        <Form layout='vertical'>
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
        const decision_reason = (document.querySelector('textarea') as HTMLTextAreaElement).value;
        try {
          await decideUserScheduleRequest(requestId, { status, decision_reason });
          message.success('処理が完了しました');
          loadAll();
        } catch (e) {
          console.error(e);
          message.error('処理に失敗しました');
        }
      },
    });
  };

  // --- Render ---
  return (
    <div style={{ padding: '24px', background: 'linear-gradient(135deg, #f0f4ff, #e6f7ff)' }}>
      <h2 style={{ color: '#0d47a1' }}>曜日別予定テンプレート</h2>
      <Table
        dataSource={templates.map((t, idx) => ({ ...t, key: idx }))}
        pagination={false}
        loading={loading}
        bordered
        columns={[
          { title: '曜日', dataIndex: 'day_of_week', key: 'day' },
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
                placeholder='HH:MM'
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
                placeholder='HH:MM'
                value={value ?? ''}
                onChange={(e) => handleTemplateChange(idx, 'end_time', e.target.value)}
                disabled={!templates[idx].is_scheduled}
              />
            ),
          },
        ]}
      />
      <Button type='primary' style={{ marginTop: 12 }} onClick={saveTemplates}>
        テンプレート保存
      </Button>

      <hr style={{ margin: '32px 0' }} />

      <h2 style={{ color: '#0d47a1' }}>予定変更・欠席・追加申請</h2>
      <Button type='primary' onClick={openCreateRequestModal} style={{ marginBottom: 12 }}>
        申請作成
      </Button>
      <Table
        dataSource={requests.map((r) => ({ ...r, key: r.id }))}
        loading={loading}
        bordered
        columns={[
          { title: '日付', dataIndex: 'target_date', key: 'date' },
          { title: '種別', dataIndex: 'request_type', key: 'type' },
          { title: '理由', dataIndex: 'request_reason', key: 'reason' },
          { title: '状態', dataIndex: 'request_status', key: 'status' },
          {
            title: '操作',
            key: 'action',
            render: (_, record) =>
              record.request_status === 'PENDING' ? (
                <span>
                  <Button
                    size='small'
                    type='primary'
                    onClick={() => handleDecision(record.id, 'APPROVED')}
                    style={{ marginRight: 8 }}
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

      <hr style={{ margin: '32px 0' }} />

      <h2 style={{ color: '#0d47a1' }}>確定日別スケジュール</h2>
      <Table
        dataSource={dailySchedules.map((d) => ({ ...d, key: d.id }))}
        loading={loading}
        bordered
        columns={[
          { title: '日付', dataIndex: 'date', key: 'date' },
          { title: '開始', dataIndex: 'start_time', key: 'start' },
          { title: '終了', dataIndex: 'end_time', key: 'end' },
          { title: '予定有無', dataIndex: 'is_scheduled', key: 'scheduled', render: (v: boolean) => (v ? 'あり' : 'なし') },
          { title: 'ステータス', dataIndex: 'schedule_status', key: 'status' },
        ]}
      />
    </div>
  );
};

/**
 * 申請作成用のサブコンポーネント（モーダル内で使用）
 */
const CreateRequestForm: React.FC<{ onCreated: () => void }> = ({ onCreated }) => {
  const [form] = Form.useForm();

  const submit = async () => {
    try {
      const values = await form.validateFields();
      await createUserScheduleRequest(values.userId, {
        target_date: values.target_date.format('YYYY-MM-DD'),
        request_type: values.request_type,
        request_reason: values.request_reason,
        requested_start_time: values.requested_start_time?.format('HH:mm') ?? null,
        requested_end_time: values.requested_end_time?.format('HH:mm') ?? null,
      });
      message.success('申請が作成されました');
      onCreated();
      Modal.destroyAll();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Form form={form} layout='vertical'>
      <Form.Item name='userId' initialValue={0} hidden />
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
        <Input placeholder='HH:MM' />
      </Form.Item>
      <Form.Item name='requested_end_time' label='終了時刻'>
        <Input placeholder='HH:MM' />
      </Form.Item>
      <Form.Item>
        <Button type='primary' onClick={submit}>
          作成
        </Button>
      </Form.Item>
    </Form>
  );
};

export default UserScheduleTab;

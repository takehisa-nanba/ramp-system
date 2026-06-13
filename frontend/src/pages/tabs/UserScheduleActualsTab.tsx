// frontend/src/pages/tabs/UserScheduleActualsTab.tsx

import React, { useEffect, useState } from 'react';
import { fetchUserDailySchedules, updateUserDailySchedule } from '../../services/userService';
import type { UserDailyScheduleItem } from '../../services/userService';
import { Button, Table, message, DatePicker, Space, Modal, Form, Input, Select, Switch, Tag } from 'antd';
import dayjs, { Dayjs } from 'dayjs';

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

interface Props {
  userId: number;
}

export const UserScheduleActualsTab: React.FC<Props> = ({ userId }) => {
  const [dailySchedules, setDailySchedules] = useState<UserDailyScheduleItem[]>([]);
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs().startOf('month'));
  const [loading, setLoading] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<UserDailyScheduleItem | null>(null);
  const [form] = Form.useForm();

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

  const handleRowClick = (record: UserDailyScheduleItem) => {
    const today = dayjs().format('YYYY-MM-DD');
    // 過去日 または 本日かつ打刻済み は編集不可
    if (record.date < today || record.actual_check_in) {
      return;
    }
    
    setEditingItem(record);
    form.setFieldsValue({
      is_scheduled: record.is_scheduled,
      start_time: record.start_time?.slice(0, 5),
      end_time: record.end_time?.slice(0, 5),
      location_type: record.location_type || 'ON_SITE',
      decision_reason: record.decision_reason || '',
    });
    setEditModalVisible(true);
  };

  const handleEditSave = async () => {
    if (!editingItem) return;
    try {
      const values = await form.validateFields();
      await updateUserDailySchedule(userId, editingItem.date, {
        is_scheduled: values.is_scheduled,
        start_time: values.is_scheduled ? values.start_time : null,
        end_time: values.is_scheduled ? values.end_time : null,
        location_type: values.is_scheduled ? values.location_type : null,
        decision_reason: values.decision_reason,
      });
      message.success('予定を更新しました');
      setEditModalVisible(false);
      loadAll();
    } catch (e: any) {
      if (e?.errorFields) return; // Validation error
      if (e?.response?.data?.error?.message) {
        message.error(e.response.data.error.message);
      } else {
        message.error('保存に失敗しました');
      }
    }
  };

  return (
    <div className="animate-in fade-in duration-500">
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-black text-slate-800 flex items-center gap-2">
            🗓️ 予定・実績
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
          dataSource={dailySchedules.map((d) => ({ ...d, key: d.id || d.date }))}
          loading={loading}
          bordered
          pagination={false}
          size="small"
          onRow={(record) => {
            const today = dayjs().format('YYYY-MM-DD');
            const isEditable = record.date >= today && !record.actual_check_in;
            return {
              onClick: () => handleRowClick(record),
              style: {
                cursor: isEditable ? 'pointer' : 'default',
                backgroundColor: !isEditable ? '#f8fafc' : undefined,
              }
            };
          }}
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
            {
              title: '状態',
              key: 'actual_status',
              render: (_, record) => {
                const today = dayjs().format('YYYY-MM-DD');
                if (record.actual_check_in) {
                  return <Tag color="blue">実績</Tag>;
                } else if (record.date < today) {
                  if (record.is_scheduled) return <Tag color="red">未打刻</Tag>;
                  return <Tag color="default">予定なし</Tag>;
                } else {
                  return <Tag color="green">予定</Tag>;
                }
              }
            },
            { 
              title: '開始', 
              key: 'start', 
              render: (_, record) => record.actual_check_in || record.start_time?.slice(0,5) || '-' 
            },
            { 
              title: '終了', 
              key: 'end', 
              render: (_, record) => record.actual_check_out || record.end_time?.slice(0,5) || '-' 
            },
            { title: '通所予定', dataIndex: 'is_scheduled', key: 'scheduled', render: (v: boolean) => (v ? 'あり' : 'なし') },
            { title: '支援区分', dataIndex: 'location_type', key: 'location_type', render: (v: string) => LOCATION_TYPE_JA[v] || v || '-' },
            { title: '変更理由', dataIndex: 'decision_reason', key: 'decision_reason', render: (v: string) => v || '-' },
          ]}
        />
      </div>

      <Modal
        title={`予定の直接編集: ${editingItem?.date}`}
        open={editModalVisible}
        onOk={handleEditSave}
        onCancel={() => setEditModalVisible(false)}
        okText="保存"
        cancelText="キャンセル"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="is_scheduled" valuePropName="checked">
            <Switch checkedChildren="通所あり" unCheckedChildren="通所なし（欠席/キャンセル）" />
          </Form.Item>
          
          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.is_scheduled !== curr.is_scheduled}>
            {({ getFieldValue }) => {
              const isScheduled = getFieldValue('is_scheduled');
              return isScheduled ? (
                <>
                  <Space style={{ display: 'flex', marginBottom: 16 }}>
                    <Form.Item name="start_time" label="開始時刻" rules={[{ required: true }]} style={{ margin: 0 }}>
                      <Input type="time" />
                    </Form.Item>
                    <Form.Item name="end_time" label="終了時刻" rules={[{ required: true }]} style={{ margin: 0 }}>
                      <Input type="time" />
                    </Form.Item>
                  </Space>
                  <Form.Item name="location_type" label="支援区分" rules={[{ required: true }]}>
                    <Select>
                      {Object.entries(LOCATION_TYPE_JA).map(([k, v]) => (
                        <Option key={k} value={k}>{v}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </>
              ) : null;
            }}
          </Form.Item>

          <Form.Item 
            name="decision_reason" 
            label="変更理由 (欠席・追加・大幅な変更時は必須)"
            rules={[
              {
                validator: async (_, value) => {
                  const isScheduled = form.getFieldValue('is_scheduled');
                  const wasScheduled = editingItem?.is_scheduled;
                  if (!isScheduled && wasScheduled && !value) {
                    return Promise.reject(new Error('通所なしに変更する場合は理由を必ず入力してください'));
                  }
                  return Promise.resolve();
                }
              }
            ]}
          >
            <TextArea rows={3} placeholder="例: 利用者からの連絡により欠席" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

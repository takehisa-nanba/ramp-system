// frontend/src/pages/tabs/UserScheduleRequestsTab.tsx

import React, { useEffect, useState, forwardRef, useImperativeHandle } from 'react';
import {
  fetchUserScheduleRequests,
  createUserScheduleRequest,
  decideUserScheduleRequest,
} from '../../services/userService';
import type { UserScheduleRequestItem } from '../../services/userService';
import { Button, Input, Select, Table, message, Modal, Form } from 'antd';
import type { FormInstance } from 'antd';

const { Option } = Select;
const { TextArea } = Input;

const REQUEST_TYPE_JA: Record<string, string> = {
  ABSENCE: '欠席',
  EXTRA_DAY: '臨時追加',
  SHIFT_TIME: '時間変更',
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

export const UserScheduleRequestsTab: React.FC<Props> = ({ userId }) => {
  const [requests, setRequests] = useState<UserScheduleRequestItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const reqRes = await fetchUserScheduleRequests(userId);
      setRequests(reqRes.items);
    } catch (err) {
      console.error(err);
      message.error('データ取得に失敗しました');
    }
    setLoading(false);
  };

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
          if (e?.errorFields) return Promise.reject();
          console.error(e);
          message.error('処理に失敗しました');
        }
      },
    });
  };

  return (
    <div className="animate-in fade-in duration-500">
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
    </div>
  );
};

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

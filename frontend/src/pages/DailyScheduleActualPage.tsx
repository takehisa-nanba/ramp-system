import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { DatePicker, Table, Tag, Select, Space } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import { Heading, Text } from '../components/common/Typography';
import { fetchDailyScheduleActuals } from '../services/userService';
import type { DailyScheduleActualItem } from '../services/userService';

const { Option } = Select;

export const DailyScheduleActualPage: React.FC = () => {
  const navigate = useNavigate();
  const [targetDate, setTargetDate] = useState<Dayjs>(dayjs());
  const [items, setItems] = useState<DailyScheduleActualItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');

  const loadData = async (date: Dayjs) => {
    setLoading(true);
    try {
      const res = await fetchDailyScheduleActuals(date.format('YYYY-MM-DD'));
      setItems(res.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(targetDate);
  }, [targetDate]);

  const filteredItems = useMemo(() => {
    return items.filter(item => {
      switch (filterType) {
        case 'scheduled':
          return item.is_scheduled;
        case 'arrived':
          return !!item.check_in_at;
        case 'not_arrived':
          return item.is_scheduled && !item.check_in_at;
        case 'unscheduled':
          return item.effective_status === 'UNSCHEDULED_ARRIVAL';
        case 'cancelled':
          return item.effective_status === 'CANCELLED' || item.schedule_status === 'CANCELLED';
        case 'all':
        default:
          return true;
      }
    });
  }, [items, filterType]);

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'ARRIVED_AS_SCHEDULED':
        return <Tag color="green">予定通り来所</Tag>;
      case 'SCHEDULED_NOT_ARRIVED':
        return <Tag color="orange">未来所</Tag>;
      case 'UNSCHEDULED_ARRIVAL':
        return <Tag color="blue">予定外来所</Tag>;
      case 'CANCELLED':
        return <Tag color="default">欠席/キャンセル</Tag>;
      case 'MISSING_SUPPORT_RECORD':
        return <Tag color="red">支援記録未作成</Tag>;
      default:
        return <Tag color="default">予定なし</Tag>;
    }
  };

  const columns = [
    {
      title: '利用者名',
      dataIndex: 'user_name',
      key: 'user_name',
      render: (text: string) => <Text className="font-medium">{text}</Text>
    },
    {
      title: '予定',
      key: 'schedule',
      render: (_: any, record: DailyScheduleActualItem) => {
        if (!record.is_scheduled) return <Text className="text-gray-400">予定なし</Text>;
        const start = record.scheduled_start_time ? record.scheduled_start_time.slice(0, 5) : '';
        const end = record.scheduled_end_time ? record.scheduled_end_time.slice(0, 5) : '';
        return <Text>{`${start} - ${end}`}</Text>;
      }
    },
    {
      title: '実績（打刻）',
      key: 'actual',
      render: (_: any, record: DailyScheduleActualItem) => {
        if (!record.check_in_at) return <Text className="text-gray-400">未打刻</Text>;
        const start = dayjs(record.check_in_at).format('HH:mm');
        const end = record.check_out_at ? dayjs(record.check_out_at).format('HH:mm') : '未退所';
        return <Text>{`${start} - ${end}`}</Text>;
      }
    },
    {
      title: 'ステータス',
      dataIndex: 'effective_status',
      key: 'effective_status',
      render: (val: string) => getStatusTag(val)
    },
    {
      title: '変更理由',
      dataIndex: 'decision_reason',
      key: 'decision_reason',
      render: (val: string | null) => val ? <Text className="text-gray-600 text-sm">{val}</Text> : <Text className="text-gray-300">-</Text>
    },
    {
      title: '日報状態',
      dataIndex: 'daily_log_status',
      key: 'daily_log_status',
      render: (val: string) => {
        if (val === 'completed') return <Tag color="green">完了</Tag>;
        if (val === 'draft') return <Tag color="orange">下書き</Tag>;
        return <Tag color="default">未作成</Tag>;
      }
    }
  ];

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <Heading variant="h2" className="!mb-0 text-gray-800">日別予定・実績</Heading>
        <Space>
          <Select value={filterType} onChange={setFilterType} style={{ width: 150 }}>
            <Option value="all">全員</Option>
            <Option value="scheduled">予定あり</Option>
            <Option value="arrived">来所済</Option>
            <Option value="not_arrived">未来所</Option>
            <Option value="unscheduled">予定外来所</Option>
            <Option value="cancelled">欠席/キャンセル</Option>
          </Select>
          <DatePicker 
            value={targetDate} 
            onChange={(d) => d && setTargetDate(d)} 
            allowClear={false} 
          />
        </Space>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <Table 
            columns={columns} 
            dataSource={filteredItems} 
            rowKey="user_id" 
            loading={loading}
            pagination={false}
            rowClassName="hover:bg-slate-50 transition-colors"
            onRow={(record) => ({
              onClick: () => {
                navigate(`/users/${record.user_id}/schedule-actuals`);
              },
              style: { cursor: 'pointer' }
            })}
          />
        </div>
      </div>
    </div>
  );
};

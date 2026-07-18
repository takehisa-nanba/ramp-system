import React, { useEffect, useState } from 'react';
import { Table, Button, Tag, Space, DatePicker, Select, Modal, Form, Input, message } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import { fetchUserDailySchedules, updateUserDailySchedule, updateUserAttendanceActuals, fetchUserDailyLogs, createDailyLog, fetchActivityTags } from '../../services/userService';
import type { UserDailyScheduleItem, DailyLogItem, ActivityTag } from '../../services/userService';
import { Clock, CheckCircle, AlertTriangle, AlertCircle, X } from 'lucide-react';
import { TimeDurationInput, TextAreaWithCounter, UXField } from '../../components/common/UXFields';

const DAY_OF_WEEK_JA: Record<string, string> = {
  'Monday': '月', 'Tuesday': '火', 'Wednesday': '水', 'Thursday': '木', 'Friday': '金', 'Saturday': '土', 'Sunday': '日',
  'Mon': '月', 'Tue': '火', 'Wed': '水', 'Thu': '木', 'Fri': '金', 'Sat': '土', 'Sun': '日'
};

const LOCATION_TYPE_JA: Record<string, string> = {
  'ON_SITE': '施設内',
  'OFF_SITE': '施設外',
  'EMPLOYMENT': '就労',
  'TRANSITION_PREP': '移行準備',
  'HOME': '在宅'
};

export const UserAttendanceTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs().startOf('month'));
  const [dailySchedules, setDailySchedules] = useState<UserDailyScheduleItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<UserDailyScheduleItem | null>(null);
  const [form] = Form.useForm();
  const [actualForm] = Form.useForm();
  const [editActualModalVisible, setEditActualModalVisible] = useState(false);
  const [editingActualDate, setEditingActualDate] = useState<string>('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [dailyLogs, setDailyLogs] = useState<DailyLogItem[]>([]);
  const [tags, setTags] = useState<ActivityTag[]>([]);
  
  const [selectedTagId, setSelectedTagId] = useState<string>('');
  const [logDate, setLogDate] = useState<string>('');
  const [startTime, setStartTime] = useState<string>('10:00');
  const [endTime, setEndTime] = useState<string>('11:00');
  const [notes, setNotes] = useState<string>('');
  const [durationSeconds, setDurationSeconds] = useState<number>(3600);
  
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [attendanceInfo, setAttendanceInfo] = useState<{date: string, checkIn: string, checkOut: string|null}|null>(null);

  useEffect(() => {
    const startParts = startTime.split(':').map(Number);
    const endParts = endTime.split(':').map(Number);
    if (startParts.length >= 2 && endParts.length >= 2) {
      const startSecs = startParts[0] * 3600 + startParts[1] * 60;
      const endSecs = endParts[0] * 3600 + endParts[1] * 60;
      if (endSecs > startSecs) {
        setDurationSeconds(endSecs - startSecs);
      } else {
        setDurationSeconds(0);
      }
    }
  }, [startTime, endTime]);

  const loadAll = async () => {
    try {
      setLoading(true);
      const start_date = currentMonth.format('YYYY-MM-DD');
      const end_date = currentMonth.endOf('month').format('YYYY-MM-DD');
      const [res, logsRes, tagsRes] = await Promise.all([
        fetchUserDailySchedules(userId, { start_date, end_date }),
        fetchUserDailyLogs(userId),
        fetchActivityTags()
      ]);
      setDailySchedules(res.items);
      setDailyLogs(logsRes.items);
      // tags endpoint currently returns array directly according to userService.ts
      setTags(tagsRes.filter(t => t.is_direct_support));
    } catch (err) {
      console.error(err);
      setError('予定・実績データの取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, [userId, currentMonth]);

  const handleRowClick = (record: UserDailyScheduleItem) => {
    setEditingRecord(record);
    form.setFieldsValue({
      is_scheduled: record.is_scheduled,
      start_time: record.start_time?.slice(0, 5) || null,
      end_time: record.end_time?.slice(0, 5) || null,
      location_type: record.location_type || 'ON_SITE',
      decision_reason: record.decision_reason || ''
    });
    setEditModalVisible(true);
  };

  const handleRowClickActual = (record: UserDailyScheduleItem) => {
    setEditingActualDate(record.date);
    actualForm.setFieldsValue({
      actual_check_in: record.actual_check_in || null,
      actual_check_out: record.actual_check_out || null,
    });
    setEditActualModalVisible(true);
  };

  const handleEditActualSave = async () => {
    try {
      const values = await actualForm.validateFields();
      await updateUserAttendanceActuals(userId, editingActualDate, {
        actual_check_in: values.actual_check_in,
        actual_check_out: values.actual_check_out,
      });
      message.success('実績を更新しました');
      setEditActualModalVisible(false);
      loadAll();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.error?.message || '保存に失敗しました');
    }
  };

  const handleAction = (item: UserDailyScheduleItem) => {
    setLogDate(item.date);
    const associatedLog = dailyLogs.find(l => l.log_date === item.date);
    
    setAttendanceInfo({
      date: item.date,
      checkIn: item.actual_check_in || '',
      checkOut: item.actual_check_out || null
    });

    if (associatedLog) {
      const act = associatedLog.activities && associatedLog.activities.length > 0 ? associatedLog.activities[0] : null;
      setStartTime(act?.start_time?.slice(0, 5) || '10:00');
      setEndTime(act?.end_time?.slice(0, 5) || '11:00');
      setNotes(associatedLog.support_content_notes || '');
      setDurationSeconds(act?.duration_seconds || 3600);
      
      
      // tag_id is on activity, but backend expects it in createDailyLog. We will try to map it.
      if (tags.length > 0) {
        setSelectedTagId(tags[0].id.toString());
      }
    } else {
      
      if (item.actual_check_in) {
        setStartTime(item.actual_check_in.slice(0, 5));
        if (item.actual_check_out) {
          setEndTime(item.actual_check_out.slice(0, 5));
        } else {
          setEndTime(item.actual_check_in.slice(0, 5));
        }
      } else {
        setStartTime('10:00');
        setEndTime('11:00');
      }
      setNotes('');
      setSelectedTagId('');
      setDurationSeconds(3600);
    }
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setFormError(null);
  };

  const handleSubmit = async (status: 'DRAFT' | 'COMPLETED') => {
    if (!selectedTagId) {
      setFormError('支援区分を選択してください');
      return;
    }
    try {
      setFormSubmitting(true);
      setFormError(null);
      await createDailyLog({
        user_id: userId,
        tag_id: Number(selectedTagId),
        start_time: startTime + ':00',
        end_time: endTime + ':00',
        duration_seconds: durationSeconds,
        notes: notes,
        log_status: status
      });
      message.success('日報・支援記録を保存しました');
      handleCloseModal();
      loadAll();
    } catch (err: any) {
      console.error(err);
      setFormError(err.response?.data?.error?.message || '保存に失敗しました');
    } finally {
      setFormSubmitting(false);
    }
  };

  const getLogStatusBadge = (status?: string) => {
    switch (status) {
      case 'completed':
        return <span className="flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-1 rounded-full w-fit"><CheckCircle className="w-3 h-3" /> 完了</span>;
      case 'draft':
        return <span className="flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-100 px-2 py-1 rounded-full w-fit"><Clock className="w-3 h-3" /> 下書き</span>;
      default:
        return <span className="flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-100 px-2 py-1 rounded-full w-fit"><AlertTriangle className="w-3 h-3" /> 未作成</span>;
    }
  };

  const handleEditSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingRecord) {
        await updateUserDailySchedule(userId, editingRecord.date, {
          is_scheduled: values.is_scheduled,
          start_time: values.start_time,
          end_time: values.end_time,
          location_type: values.location_type,
          decision_reason: values.decision_reason
        });
        message.success('予定を更新しました');
        setEditModalVisible(false);
        loadAll();
      }
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.error?.message || '保存に失敗しました');
    }
  };

  if (error) return <div className="text-red-500">{error}</div>;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200">
      <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50 rounded-t-xl">
        <h2 className="text-lg font-bold text-slate-800">月間予定・実績・記録</h2>
        <div className="flex items-center gap-4">
          <DatePicker picker="month" value={currentMonth} onChange={(d) => setCurrentMonth(d || dayjs())} allowClear={false} />
          <Button onClick={loadAll} loading={loading}>更新</Button>
        </div>
      </div>
      
      <div className="p-0">
        <Table
          dataSource={dailySchedules}
          rowKey="date"
          pagination={false}
          loading={loading}
          size="middle"
          rowClassName={(record) => {
            const log = dailyLogs.find(l => l.log_date === record.date);
            const status = log ? (log.log_status === 'COMPLETED' ? 'completed' : 'draft') : 'missing';
            return status === 'missing' && record.actual_check_in ? 'bg-rose-50/30' : '';
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
                  if (record.is_scheduled) return <Tag color="green">予定あり</Tag>;
                  return <Tag color="default">予定なし</Tag>;
                }
              }
            },
            {
              title: '予定種類',
              dataIndex: 'schedule_status',
              key: 'schedule_status',
              render: (v: string) => {
                switch(v) {
                  case 'NORMAL': return '通常';
                  case 'CANCELLED': return <span className="text-red-500">欠席</span>;
                  case 'SUBSTITUTED': return '振替';
                  case 'EXTRA': return '追加';
                  default: return v || '-';
                }
              }
            },
            { title: '支援区分', dataIndex: 'location_type', key: 'location_type', render: (v: string) => LOCATION_TYPE_JA[v] || v || '-' },
            { 
              title: '時間帯 (予定)', 
              key: 'time_scheduled',
              render: (_, record) => record.is_scheduled ? `${record.start_time?.slice(0,5) || '-'} 〜 ${record.end_time?.slice(0,5) || '-'}` : '-'
            },
            { 
              title: '時間帯 (実績)', 
              key: 'time_actual',
              render: (_, record) => record.actual_check_in ? `${record.actual_check_in.slice(0,5)} 〜 ${record.actual_check_out?.slice(0,5) || '-'}` : '-'
            },
            { title: '変更理由', dataIndex: 'decision_reason', key: 'decision_reason', render: (v: string) => v || '-' },
            {
              title: '日報・支援記録',
              key: 'daily_log_status',
              render: (_, record) => {
                const log = dailyLogs.find(l => l.log_date === record.date);
                const status = log ? (log.log_status === 'COMPLETED' ? 'completed' : 'draft') : 'missing';
                return getLogStatusBadge(status);
              }
            },
            {
              title: 'アクション',
              key: 'action',
              render: (_, record) => {
                const log = dailyLogs.find(l => l.log_date === record.date);
                const status = log ? (log.log_status === 'COMPLETED' ? 'completed' : 'draft') : 'missing';
                return (
                  <Space direction="vertical" size="small">
                    <Space>
                      <Button size="small" onClick={(e) => { e.stopPropagation(); handleRowClick(record); }}>予定編集</Button>
                      <Button size="small" onClick={(e) => { e.stopPropagation(); handleRowClickActual(record); }}>実績編集</Button>
                    </Space>
                    <Button 
                      type={status === 'missing' && record.actual_check_in ? 'primary' : 'default'}
                      size="small"
                      className={status === 'missing' && record.actual_check_in ? 'bg-indigo-600 text-white border-transparent' : ''}
                      onClick={(e) => { e.stopPropagation(); handleAction(record); }}
                    >
                      {status === 'completed' ? '記録を確認' : '記録を作成'}
                    </Button>
                  </Space>
                );
              }
            }
          ]}
        />
      </div>

      <Modal title={`予定の編集: ${editingRecord?.date}`} open={editModalVisible} onOk={handleEditSave} onCancel={() => setEditModalVisible(false)} okText="保存" cancelText="キャンセル">
        <Form form={form} layout="vertical">
          <Form.Item name="is_scheduled" label="予定あり" valuePropName="checked"><Input type="checkbox" /></Form.Item>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="start_time" label="開始時間"><Input type="time" /></Form.Item>
            <Form.Item name="end_time" label="終了時間"><Input type="time" /></Form.Item>
          </Space>
          <Form.Item name="location_type" label="支援区分">
            <Select>
              {Object.entries(LOCATION_TYPE_JA).map(([k,v]) => <Select.Option key={k} value={k}>{v}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="decision_reason" label="変更理由"><Input.TextArea /></Form.Item>
        </Form>
      </Modal>

      <Modal title={`実績の編集: ${editingActualDate}`} open={editActualModalVisible} onOk={handleEditActualSave} onCancel={() => setEditActualModalVisible(false)} okText="保存" cancelText="キャンセル">
        <Form form={actualForm} layout="vertical">
          <Space style={{ display: 'flex' }}>
            <Form.Item name="actual_check_in" label="来所時間"><Input type="time" /></Form.Item>
            <Form.Item name="actual_check_out" label="退所時間"><Input type="time" /></Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* 新規支援記録作成モーダル */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-[2rem] shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200">
            {/* ヘッダー */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-xl font-black text-slate-800">新規支援記録の作成</h3>
              <button 
                onClick={handleCloseModal}
                className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* コンテンツ */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {attendanceInfo && (
                <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-4 flex flex-col gap-1.5 shadow-inner">
                  <h4 className="text-xs font-black text-indigo-600 flex items-center gap-1.5 uppercase tracking-wider">
                    <Clock className="w-3.5 h-3.5" /> 対象日の利用実績と紐付け
                  </h4>
                  <div className="text-sm font-black text-slate-800">
                    実績日: {attendanceInfo.date}
                  </div>
                  <div className="flex gap-4 text-xs font-bold text-slate-500">
                    <div>来所: <span className="text-indigo-600 font-black">{attendanceInfo.checkIn || '-'}</span></div>
                    <div>退所: <span className="text-indigo-600 font-black">{attendanceInfo.checkOut || '-'}</span></div>
                  </div>
                </div>
              )}

              {formError && (
                <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-start gap-2 text-sm border border-rose-200">
                  <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                  <div>{formError}</div>
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">支援区分 (必須)</label>
                <select
                  value={selectedTagId}
                  onChange={(e) => setSelectedTagId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm font-bold text-slate-700 focus:outline-none focus:border-indigo-500 transition-colors"
                >
                  <option value="" disabled>選択してください</option>
                  {tags.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">支援日</label>
                <UXField type="date" value={logDate} onChange={(e: any) => setLogDate(e.target.value)} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">開始時間</label>
                  <UXField type="time" value={startTime} onChange={(e: any) => setStartTime(e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">終了時間</label>
                  <UXField type="time" value={endTime} onChange={(e: any) => setEndTime(e.target.value)} />
                </div>
              </div>

              <TimeDurationInput
                label="活動所要時間"
                totalSeconds={durationSeconds}
                onChange={(secs: number) => setDurationSeconds(secs)}
                className="mt-2"
              />

              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">支援記録 (自由記述)</label>
                <TextAreaWithCounter placeholder="支援の具体的な内容などを入力してください" rows={4} value={notes} onChange={(e: any) => setNotes(e.target.value)} />
              </div>
            </div>

            {/* フッター */}
            <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex gap-3 justify-end">
              <button
                disabled={formSubmitting}
                onClick={() => handleSubmit('DRAFT')}
                className="px-5 py-2.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-xl font-bold text-sm transition-colors disabled:opacity-50"
              >
                下書き保存
              </button>
              <button
                disabled={formSubmitting}
                onClick={() => handleSubmit('COMPLETED')}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {formSubmitting && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                記録を完了する
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

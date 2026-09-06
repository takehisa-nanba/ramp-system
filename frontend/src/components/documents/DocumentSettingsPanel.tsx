import React, { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { fetchUserList, type UserListItem } from '../../services/userService';
import {
  documentSettingsApi,
  type OfficeElectronicDocumentSetting,
  type UserElectronicDocumentSetting,
} from '../../services/documentSettingsApi';

export const DocumentSettingsPanel: React.FC = () => {
  const [officeSetting, setOfficeSetting] = useState<OfficeElectronicDocumentSetting | null>(null);
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [userSetting, setUserSetting] = useState<UserElectronicDocumentSetting | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const errorMessage = (err: any, fallback: string) =>
    err?.response?.data?.msg || err?.response?.data?.error?.message || err?.message || fallback;

  const loadBase = async () => {
    setLoading(true);
    setError(null);
    try {
      const [office, userList] = await Promise.all([
        documentSettingsApi.getOfficeSetting(),
        fetchUserList(),
      ]);
      setOfficeSetting(office);
      setUsers(userList);
    } catch (err: any) {
      setError(errorMessage(err, '電子文書設定の取得に失敗しました。'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBase();
  }, []);

  const loadUserSetting = async (userId: number) => {
    setSelectedUserId(userId);
    setUserSetting(null);
    setError(null);
    setMessage(null);
    try {
      setUserSetting(await documentSettingsApi.getUserSetting(userId));
    } catch (err: any) {
      setError(errorMessage(err, '利用者の電子文書設定を取得できませんでした。'));
    }
  };

  const saveOfficeSetting = async (enabled: boolean) => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await documentSettingsApi.updateOfficeSetting(enabled);
      setOfficeSetting(updated);
      setMessage(enabled ? '事業所の電子交付を有効にしました。' : '事業所の電子交付を無効にしました。');
      if (selectedUserId) {
        setUserSetting(await documentSettingsApi.getUserSetting(selectedUserId));
      }
    } catch (err: any) {
      setError(errorMessage(err, '事業所設定の保存に失敗しました。'));
    } finally {
      setSaving(false);
    }
  };

  const saveUserSetting = async (optOut: boolean) => {
    if (!selectedUserId) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await documentSettingsApi.updateUserSetting(selectedUserId, optOut);
      setUserSetting(updated);
      setMessage(optOut ? 'この利用者は紙交付を優先する設定にしました。' : 'この利用者の電子交付例外を解除しました。');
    } catch (err: any) {
      setError(errorMessage(err, '利用者設定の保存に失敗しました。'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm font-bold text-slate-500">電子文書設定を読み込み中...</div>;
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm space-y-5">
      <div>
        <div className="flex items-center gap-2 text-slate-800 font-black">
          <ShieldCheck className="h-5 w-5 text-indigo-600" />
          電子交付・署名設定
        </div>
        <p className="mt-2 text-sm text-slate-500">
          電子交付は「事業所で有効」「利用者が紙交付例外でない」「本人が実際にログイン可能」の全条件を満たす場合だけ利用できます。最終判定は交付時にFail Closedで再確認されます。
        </p>
      </div>

      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">{error}</div>}
      {message && <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-700">{message}</div>}

      {officeSetting && (
        <div className="rounded-xl border border-slate-200 p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm font-black text-slate-800">事業所標準</div>
              <div className="mt-1 text-xs text-slate-500">{officeSetting.office_name}</div>
            </div>
            <label className="inline-flex items-center gap-3 text-sm font-bold text-slate-700">
              <input
                type="checkbox"
                checked={officeSetting.electronic_document_enabled}
                disabled={!officeSetting.can_edit || saving}
                onChange={(e) => saveOfficeSetting(e.target.checked)}
                className="h-5 w-5 rounded border-slate-300"
              />
              電子交付を利用する
            </label>
          </div>
          {!officeSetting.can_edit && <p className="mt-2 text-xs text-slate-400">この設定を変更できる管理権限がありません。</p>}
        </div>
      )}

      <div className="rounded-xl border border-slate-200 p-4 space-y-4">
        <div>
          <div className="text-sm font-black text-slate-800">利用者ごとの例外</div>
          <p className="mt-1 text-xs text-slate-500">電子交付が難しい利用者だけ、紙交付を優先できます。</p>
        </div>

        <select
          value={selectedUserId ?? ''}
          onChange={(e) => {
            const value = Number(e.target.value);
            if (value) loadUserSetting(value);
            else {
              setSelectedUserId(null);
              setUserSetting(null);
            }
          }}
          className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">利用者を選択</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>{user.display_name}</option>
          ))}
        </select>

        {userSetting && (
          <div className="space-y-3">
            <label className="inline-flex items-center gap-3 text-sm font-bold text-slate-700">
              <input
                type="checkbox"
                checked={userSetting.electronic_document_opt_out}
                disabled={!userSetting.can_edit || saving}
                onChange={(e) => saveUserSetting(e.target.checked)}
                className="h-5 w-5 rounded border-slate-300"
              />
              この利用者は紙交付を優先する
            </label>
            <div className="text-xs text-slate-500">
              現在の方針: {userSetting.effective_policy === 'PAPER' ? '紙交付' : '本人ログイン可能な場合のみ電子交付'}
            </div>
            {!userSetting.can_edit && <p className="text-xs text-slate-400">この利用者設定を変更する権限がありません。</p>}
          </div>
        )}
      </div>
    </section>
  );
};

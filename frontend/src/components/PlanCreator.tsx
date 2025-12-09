// frontend/src/components/PlanCreator.tsx

import React, { useState } from 'react';
// 🛠️ 修正: パスの末尾に .ts 拡張子を追加
import { createPlanDraft } from '../services/plans.ts';

// =================================================================
// PlanCreator コンポーネント (新規作成)
// =================================================================
const PlanCreator: React.FC = () => {
    // 利用者IDは田中太郎のID=1、方針IDは投入済みのID=1をデフォルトとする
    const [userId, setUserId] = useState(1);
    const [policyId, setPolicyId] = useState(1); // 総合支援方針ID (投入済み)
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{status: string, id: number} | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleCreateDraft = async () => {
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            // plans.ts の createPlanDraft 関数を呼び出し
            const data = await createPlanDraft({
                user_id: userId,
                holistic_support_policy_id: policyId,
            });

            setResult({ status: data.status, id: data.plan_id });
        } catch (err: any) {
            console.error(err);
            const msg = err.response?.data?.msg || err.message || '計画作成に失敗しました。';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-gradient-to-r from-green-600 to-teal-600 px-6 py-4 flex justify-between items-center">
                <h3 className="text-lg font-bold text-white">個別支援計画（原案）作成</h3>
                <span className="text-xs font-bold bg-white/20 text-white px-3 py-1 rounded-full">CREATE_PLAN 権限</span>
            </div>
            
            <div className="p-6">
                <div className="flex flex-col sm:flex-row gap-4 mb-6 items-end">
                    {/* 利用者ID */}
                    <div className="w-full sm:w-auto">
                        <label className="block text-xs font-bold text-gray-500 mb-1 ml-1">対象利用者ID</label>
                        <input 
                            type="number" 
                            value={userId} 
                            onChange={e => setUserId(Number(e.target.value))}
                            className="w-full pl-3 pr-3 py-2 border rounded-lg text-center font-mono"
                        />
                    </div>
                    {/* 方針ID */}
                    <div className="w-full sm:w-auto">
                        <label className="block text-xs font-bold text-gray-500 mb-1 ml-1">根拠方針ID (1)</label>
                        <input 
                            type="number" 
                            value={policyId} 
                            onChange={e => setPolicyId(Number(e.target.value))}
                            className="w-full pl-3 pr-3 py-2 border rounded-lg text-center font-mono bg-gray-100"
                            disabled
                        />
                    </div>
                    <button 
                        onClick={handleCreateDraft}
                        disabled={loading}
                        className="flex-1 sm:flex-none bg-green-600 hover:bg-green-700 text-white px-6 py-2.5 rounded-lg font-medium transition-all shadow-md"
                    >
                        {loading ? '作成中...' : '計画原案を作成'}
                    </button>
                </div>

                {error && (
                    <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4 text-red-700 rounded-r">{error}</div>
                )}
                
                {result && (
                    <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                        <p className="font-bold text-green-700">✅ 計画ドラフト作成成功</p>
                        <p className="text-sm text-green-600">Plan ID: <span className="font-mono">{result.id}</span>, Status: {result.status}</p>
                        <p className="text-xs mt-1 text-green-500">次のステップ: 目標の追加と承認フローへ進めます。</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default PlanCreator;
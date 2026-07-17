import React, { useState } from 'react';
import { aiGatewayService } from '../services/aiGatewayService';
import { Send, Cpu, Zap, Star } from 'lucide-react';

const AITestPage: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [usePro, setUsePro] = useState(false);
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [modelUsed, setModelUsed] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsLoading(true);
    setError('');
    setResponse('');
    setModelUsed('');

    const res = await aiGatewayService.testGateway({ prompt, use_pro: usePro });

    if (res.success) {
      setResponse(res.response || '');
      setModelUsed(res.model_used || '');
    } else {
      setError(res.error || '不明なエラーが発生しました');
    }
    setIsLoading(false);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center text-indigo-600">
          <Cpu size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-black text-slate-800">AI Gateway テスト</h1>
          <p className="text-sm text-slate-500 font-bold">Gemini APIとの疎通確認とモデル切り替えテスト</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Section */}
        <div className="col-span-1 lg:col-span-1 space-y-4">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h2 className="text-sm font-black text-slate-700 mb-4 flex items-center gap-2">
              <Zap size={16} className="text-amber-500" />
              モデル選択
            </h2>
            <div className="flex flex-col gap-3">
              <label className={`flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all ${!usePro ? 'border-indigo-500 bg-indigo-50/50' : 'border-slate-100 hover:border-slate-200'}`}>
                <input type="radio" checked={!usePro} onChange={() => setUsePro(false)} className="hidden" />
                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${!usePro ? 'border-indigo-500' : 'border-slate-300'}`}>
                  {!usePro && <div className="w-2 h-2 bg-indigo-500 rounded-full"></div>}
                </div>
                <div>
                  <div className="font-bold text-sm text-slate-800">Gemini 3.5 Flash</div>
                  <div className="text-[10px] text-slate-500 font-bold mt-0.5">高速・軽量 (テスト推奨)</div>
                </div>
              </label>

              <label className={`flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all ${usePro ? 'border-purple-500 bg-purple-50/50' : 'border-slate-100 hover:border-slate-200'}`}>
                <input type="radio" checked={usePro} onChange={() => setUsePro(true)} className="hidden" />
                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${usePro ? 'border-purple-500' : 'border-slate-300'}`}>
                  {usePro && <div className="w-2 h-2 bg-purple-500 rounded-full"></div>}
                </div>
                <div>
                  <div className="font-bold text-sm text-slate-800 flex items-center gap-1">
                    Gemini 3.5 Flash (Pro代用) <Star size={12} className="text-purple-500 fill-purple-500" />
                  </div>
                  <div className="text-[10px] text-slate-500 font-bold mt-0.5">高品質・推論用 (本番相当)</div>
                </div>
              </label>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col gap-4">
            <h2 className="text-sm font-black text-slate-700">プロンプト入力</h2>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="AIに話しかけてみてください..."
              className="w-full h-32 p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm resize-none"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !prompt.trim()}
              className="w-full flex items-center justify-center gap-2 bg-slate-900 text-white py-3 rounded-xl font-bold text-sm hover:bg-slate-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '生成中...' : '送信する'}
              {!isLoading && <Send size={16} />}
            </button>
          </form>
        </div>

        {/* Output Section */}
        <div className="col-span-1 lg:col-span-2">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 h-full min-h-[400px] flex flex-col">
            <h2 className="text-sm font-black text-slate-700 mb-4 flex items-center gap-2">
              <MessageSquare size={16} className="text-slate-400" />
              AIからの返答
            </h2>
            
            {error && (
              <div className="bg-rose-50 text-rose-600 p-4 rounded-xl text-sm font-bold mb-4">
                エラー: {error}
              </div>
            )}

            <div className="flex-1 bg-slate-50 rounded-xl p-4 overflow-y-auto whitespace-pre-wrap text-sm text-slate-700 font-medium">
              {isLoading ? (
                <div className="flex items-center gap-2 text-slate-400 animate-pulse">
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <span className="ml-2 font-bold text-xs">AIが思考中...</span>
                </div>
              ) : response ? (
                <div>
                  <div className="inline-block px-2 py-1 mb-3 rounded-md bg-indigo-100 text-indigo-700 text-[10px] font-black uppercase tracking-wider">
                    {modelUsed}
                  </div>
                  <div>{response}</div>
                </div>
              ) : (
                <div className="text-slate-400 text-center mt-20">
                  プロンプトを送信すると、ここに結果が表示されます
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// MessageSquare icon wasn't imported at top, so import it here or at top
import { MessageSquare } from 'lucide-react';

export default AITestPage;

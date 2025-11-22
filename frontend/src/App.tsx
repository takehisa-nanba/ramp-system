import { useState, FormEvent } from 'react';
import './App.css'; 
// Tailwind CSS を利用してモダンなデザインを作成します
const API_BASE_URL = 'http://localhost:5000/api'; // FlaskサーバーのデフォルトURLを想定

// ユーザー情報と認証状態を保持する型定義
type AuthState = {
  isLoggedIn: boolean;
  token: string | null;
  supporterName: string | null;
  role: string | null;
  error: string | null;
};

// ログイン画面のコンポーネント
// ★修正: props ではなく useAuth フックを使用するように変更
const LoginForm: React.FC = () => {
  // ★修正: onLoginSuccess を AuthContext から取得
  const { login, isLoading: authLoading, error: authError } = useAuth(); 
  
  const [email, setEmail] = useState('sato@ramp.co.jp'); // テスト用デフォルト値
  const [password, setPassword] = useState('adminpassword'); // テスト用デフォルト値
  const [loading, setLoading] = useState(false); // 個別のローディング状態
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // ★修正: fetchではなく、AuthContextの login 関数を使用
      await login({ email, password });
      
    } catch (err: any) {
      // AuthContextからスローされたエラーをキャッチ
      console.error('Login error:', err);
      setError(err.message || 'サーバーとの通信に失敗しました。バックエンドが実行されているか確認してください。');
    } finally {
      setLoading(false);
    }
  };

  // ... (JSXのレンダリング部分は変更なし) ...
  return (
    <div className="flex justify-center items-center h-full">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm p-8 bg-white shadow-xl rounded-lg border border-gray-100"
      >
        <h2 className="text-3xl font-extrabold text-indigo-700 mb-6 text-center">
          RAMP - 職員ログイン
        </h2>
        
        {/* エラーメッセージ (AuthContextからのエラーとフォームのエラーを両方表示) */}
        {(authError || error) && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4" role="alert">
            <p>{authError || error}</p>
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="email">
            メールアドレス
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="sato@ramp.co.jp"
            required
            disabled={loading || authLoading}
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
            パスワード
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="testpassword"
            required
            disabled={loading || authLoading}
          />
        </div>

        <button
          type="submit"
          className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white 
            ${(loading || authLoading) ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'} transition duration-150`}
          disabled={loading || authLoading}
        >
          {/* ローディング状態の修正 */}
          {(loading || authLoading) ? (
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : 'ログイン'}
        </button>
        
        <p className="mt-4 text-center text-xs text-gray-500">
            テストアカウント: sato@ramp.co.jp / adminpassword
        </p>
      </form>
    </div>
  );
};


// メインアプリケーションコンポーネント
const App: React.FC = () => {
  // ★修正: useAuthフックから認証状態を取得する
  const { user, isAuthenticated, logout } = useAuth();
  
  const handleLogout = logout; // AuthContextのlogout関数を使用
  
  // 認証前の画面表示
  if (!isAuthenticated) {
    return (
        <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-inter">
          <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                個別支援管理システム RAMP (仮)
            </h2>
          </div>
          <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
             <LoginForm /> {/* ★修正: propsを渡さずに直接LoginFormを呼び出す */}
          </div>
        </div>
    );
  }

  // 認証後のダッシュボード画面
  return (
    <div className="min-h-screen bg-gray-100 p-8 font-inter">
      <div className="max-w-7xl mx-auto">
        <header className="bg-white shadow rounded-lg p-6 flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            メインダッシュボード
          </h1>
          <div className="flex items-center space-x-4">
            <span className="text-gray-700">
              {user?.fullName} ({user?.roleName}) 様
            </span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              ログアウト
            </button>
          </div>
        </header>

        <div className="p-6 bg-white rounded-lg shadow">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">ようこそ、{user?.fullName} さん！</h2>
          <p className="text-lg text-gray-600">
            あなたの権限は **{user?.roleName}** です。この権限で利用可能な機能を確認できます。
          </p>
          <div className="mt-4 p-4 bg-indigo-50 rounded-lg">
            <h3 className="font-bold text-indigo-700">Auth Status</h3>
            <p className="text-sm break-all text-gray-800 mt-2">Authenticated successfully.</p>
            <p className="text-xs text-gray-500 mt-1">この認証状態はHTTP-Only Cookieによって維持されています。</p>
          </div>
        </div>
        
        {/* ここに今後のナビゲーションと主要機能コンポーネントを配置 */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold text-gray-700">利用者管理</h3>
                <p className="text-gray-600">利用者マスタの登録・閲覧</p>
                <button className="mt-3 text-indigo-600 hover:text-indigo-800">詳細を見る &rarr;</button>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold text-gray-700">支援計画</h3>
                <p className="text-gray-600">計画の作成、承認、モニタリング</p>
                <button className="mt-3 text-indigo-600 hover:text-indigo-800">詳細を見る &rarr;</button>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold text-gray-700">日報・勤怠</h3>
                <p className="text-gray-600">日々の活動記録、打刻実績</p>
                <button className="mt-3 text-indigo-600 hover:text-indigo-800">詳細を見る &rarr;</button>
            </div>
        </div>
      </div>
    </div>
  );
};

export default App;
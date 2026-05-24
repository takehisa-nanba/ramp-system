// APIリクエストの基盤となる型
export interface LoginRequest {
  login_id: string; // email または user_code
  password: string;
  user_type: 'staff' | 'user';
}

// ログイン成功時にAPIから返されるデータ
export interface LoginResponse {
  msg: string;
  user_id: number;
  role_name: string;
  full_name: string;
  role_scopes?: string[];
}


// 認証が必要なリクエストのヘッダーに含めるCSRFトークン
export interface CsrfToken {
  name: string; // usually 'csrf_access_token'
  value: string;
}

// アプリケーション全体で保持するユーザー/認証情報
export interface AuthUser {
  id: number;
  fullName: string;
  roleId: number;
  roleName: string; // JWTのclaimsから取得されるロール名（例: '管理者', '利用者'）
  roleScopes?: string[];
}

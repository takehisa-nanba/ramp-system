// APIリクエストの基盤となる型
export interface LoginRequest {
  email: string;
  password: string;
}

// ログイン成功時にAPIから返されるデータ
export interface LoginResponse {
  msg: string;
  supporter_id: number;
  role_id: number;
  full_name: string;
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
}

declare module AdminService {
  export type LoginData = {
    access_token: string;
    avatar: unknown;
    color_schema: 'Bright' | 'Dark';
    create_date: string;
    create_time: number;
    email: string;
    id: string;
    is_active: '0' | '1';
    is_anonymous: '0' | '1';
    is_authenticated: '0' | '1';
    is_superuser: boolean;
    language: string;
    last_login_time: string;
    login_channel: unknown;
    nickname: string;
    password: string;
    status: '0' | '1';
    timezone: string;
    update_date: [string];
    update_time: [number];
  };

  export type ListUsersItem = {
    create_date: string;
    email: string;
    is_active: '0' | '1';
    is_locked: boolean;
    is_superuser: boolean;
    role: string;
    nickname: string;
  };

  export type UserDetail = {
    avatar?: string;
    create_date: string;
    email: string;
    is_active: '0' | '1';
    is_anonymous: '0' | '1';
    is_superuser: boolean;
    language: string;
    last_login_time: string;
    login_channel: unknown;
    status: '0' | '1';
    update_date: string;
    role: string;
  };

  export type ListUserDatasetItem = {
    avatar?: string;
    chunk_num: number;
    create_date: string;
    doc_num: number;
    language: string;
    name: string;
    permission: string;
    status: '0' | '1';
    token_num: number;
    update_date: string;
  };

  export type ListUserAgentItem = {
    avatar?: string;
    canvas_category: 'agent';
    permission: 'string';
    title: string;
  };

  export type TaskExecutorHeartbeatItem = {
    name: string;
    boot_at: string;
    now: string;
    ip_address: string;
    current: Record<string, object>;
    done: number;
    failed: number;
    lag: number;
    pending: number;
    pid: number;
  };

  export type TaskExecutorInfo = Record<string, TaskExecutorHeartbeatItem[]>;

  export type ListServicesItem = {
    extra: Record<string, unknown>;
    host: string;
    id: number;
    name: string;
    port: number;
    service_type: string;
    status: 'alive' | 'timeout' | 'fail';
  };

  export type ServiceDetail =
    | {
        service_name: string;
        status: 'alive' | 'timeout';
        message: string | Record<string, any> | Record<string, any>[];
      }
    | {
        service_name: 'task_executor';
        status: 'alive' | 'timeout';
        message: AdminService.TaskExecutorInfo;
      };

  export type PermissionData = {
    enable: boolean;
    read: boolean;
    write: boolean;
    share: boolean;
  };

  export type ListRoleItem = {
    id: string;
    role_name: string;
    description: string;
    create_date: string;
    update_date: string;
  };

  export type ListRoleItemWithPermission = ListRoleItem & {
    permissions: Record<string, PermissionData>;
  };

  export type RoleDetailWithPermission = {
    role: {
      id: string;
      name: string;
      description: string;
    };
    permissions: Record<string, PermissionData>;
  };

  export type RoleDetail = {
    id: string;
    name: string;
    description: string;
    create_date: string;
    update_date: string;
  };

  export type AssignRolePermissionsInput = Record<
    string,
    Partial<PermissionData>
  >;
  export type RevokeRolePermissionInput = AssignRolePermissionsInput;

  export type UserDetailWithPermission = {
    user: {
      id: string;
      username: string;
      role: string;
    };
    role_permissions: Record<string, PermissionData>;
  };

  export type ResourceType = {
    resource_types: string[];
  };

  export type ListWhitelistItem = {
    id: number;
    email: string;
    create_date: string;
    create_time: number;
    update_date: string;
    update_time: number;
  };

  // Sandbox settings types
  export type SandboxProvider = {
    id: string;
    name: string;
    description: string;
    tags: string[];
  };

  export type SandboxConfigField = {
    type: 'string' | 'integer' | 'boolean' | 'json';
    required?: boolean;
    label?: string;
    placeholder?: string;
    default?: string | number | boolean;
    min?: number;
    max?: number;
    description?: string;
    secret?: boolean;
  };

  export type SandboxConfig = {
    provider_type: string;
    config: Record<string, unknown>;
  };

  export type AgentUsageParams = {
    from_date?: string;
    to_date?: string;
    source?: 'all' | 'agent' | 'dialog';
    keyword?: string;
    user_id?: string;
    granularity?: 'day' | 'week' | 'month';
    scope?: 'current' | 'all';
    sections?: string;
  };

  export type AgentUsageOverview = {
    total_sessions: number;
    total_rounds: number;
    active_users: number;
    total_tokens: number;
    total_duration: number;
    avg_duration: number;
    error_count: number;
    agent_sessions: number;
    dialog_sessions: number;
    chat_graph_count: number;
  };

  export type AgentUsageTrendItem = {
    date: string;
    sessions: number;
    rounds: number;
    tokens: number;
    errors: number;
    chat_graphs: number;
  };

  export type AgentUsageAppItem = {
    app_id: string;
    app_name: string;
    app_type: string;
    source: string;
    total_sessions: number;
    total_rounds: number;
    active_users: number;
    total_tokens: number;
    total_duration: number;
    avg_duration: number;
    error_count: number;
    latest_time: string;
  };

  export type AgentUsageUserItem = {
    user_id: string;
    user_name: string;
    user_email: string;
    total_sessions: number;
    used_apps: number;
    total_rounds: number;
    total_tokens: number;
    total_duration: number;
    avg_duration: number;
    error_count: number;
    chat_graph_count: number;
    latest_time: string;
  };

  export type AgentUsageChatGraphItem = {
    id: string;
    name: string;
    user_id: string;
    user_name: string;
    user_email: string;
    doc_num: number;
    chunk_num: number;
    token_num: number;
    create_date: string;
  };

  export type AgentUsageDetailItem = {
    id: string;
    app_id: string;
    app_name: string;
    app_type: string;
    source: string;
    user_id: string;
    user_name: string;
    user_email: string;
    question: string;
    status: string;
    rounds: number;
    tokens: number;
    duration: number;
    errors: string;
    create_date: string;
  };

  export type AgentUsageSummary = {
    overview: AgentUsageOverview;
    trend: AgentUsageTrendItem[];
    by_app: AgentUsageAppItem[];
    by_user: AgentUsageUserItem[];
    chat_graphs: AgentUsageChatGraphItem[];
    detail: AgentUsageDetailItem[];
    total_detail: number;
    filters: Record<string, string>;
  };
}

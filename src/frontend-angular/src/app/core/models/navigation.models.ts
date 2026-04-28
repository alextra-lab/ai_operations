import { UserRole } from '../auth/auth.models';

export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  route?: string;
  children?: MenuItem[];
  roles: readonly UserRole[];
  permissions?: readonly string[];
  disabled?: boolean;
  badge?: {
    text: string;
    color: 'primary' | 'accent' | 'warn' | 'success';
  };
  tooltip?: string;
  order?: number;
}

export interface Breadcrumb {
  label: string;
  route?: string;
  icon?: string;
  disabled?: boolean;
}

export interface QuickAction {
  id: string;
  label: string;
  icon: string;
  action: () => void;
  roles: readonly UserRole[];
  tooltip?: string;
  disabled?: boolean;
  keyboardShortcut?: string;
}

export interface NavigationState {
  isSidebarOpen: boolean;
  isSidebarCollapsed: boolean;
  currentBreadcrumbs: Breadcrumb[];
  activeMenuItem: string | null;
}

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  metaKey?: boolean;
  callback: () => void;
  description: string;
  roles?: readonly UserRole[];
  preventDefault?: boolean;
  stopPropagation?: boolean;
}

export interface NavigationConfig {
  sidebarWidth: number;
  collapsedSidebarWidth: number;
  quickActionsBarHeight: number;
  breadcrumbHeight: number;
  animationDuration: number;
}

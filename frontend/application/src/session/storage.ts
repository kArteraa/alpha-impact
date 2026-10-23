import { ROLE_LABELS, type Role } from "@alpha-impact/plugin";

const USER_KEY = "alpha-impact.user";

function roleKey(userId: string): string {
  return `alpha-impact.role.${userId}`;
}

function isRole(value: string | null): value is Role {
  return value !== null && Object.hasOwn(ROLE_LABELS, value);
}

export function saveUser(userId: string) {
  localStorage.setItem(USER_KEY, userId);
}

export function loadUser(): string | null {
  return localStorage.getItem(USER_KEY);
}

export function forgetUser() {
  localStorage.removeItem(USER_KEY);
}

export function saveRole(userId: string, role: Role) {
  localStorage.setItem(roleKey(userId), role);
}

export function loadRole(userId: string): Role | null {
  const value = localStorage.getItem(roleKey(userId));
  return isRole(value) ? value : null;
}

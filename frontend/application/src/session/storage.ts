import type { Role } from "@alpha-impact/plugin";
import { ROLE_LABELS } from "./roles";

const USER_KEY = "alpha-impact.user";

function roleKey(userId: string): string {
  return `alpha-impact.role.${userId}`;
}

function isRole(value: string | null): value is Role {
  return value !== null && value in ROLE_LABELS;
}

export function saveUser(userId: string) {
  localStorage.setItem(USER_KEY, userId);
}

export function loadUser(): string | null {
  return localStorage.getItem(USER_KEY);
}

export function saveRole(userId: string, role: Role) {
  localStorage.setItem(roleKey(userId), role);
}

export function loadRole(userId: string): Role | null {
  const value = localStorage.getItem(roleKey(userId));
  return isRole(value) ? value : null;
}

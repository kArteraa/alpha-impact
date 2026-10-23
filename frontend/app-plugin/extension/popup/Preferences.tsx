import { companyName, ROLE_LABELS, type Role } from "../../src";
import { PAGE_TYPE_LABELS, type PageType } from "../config";
import { type ExtensionState, type Send, type Settings, stateOf } from "../messages";

interface PreferencesProps {
  state: Extract<ExtensionState, { signedIn: true }>;
  send: Send;
  onState: (state: ExtensionState) => void;
}

const ROLES = Object.entries(ROLE_LABELS) as [Role, string][];
const PAGE_TYPES = Object.entries(PAGE_TYPE_LABELS) as [PageType, string][];

export function Preferences({ state, send, onState }: PreferencesProps) {
  const { userId, clients, settings } = state;

  async function update(patch: Partial<Settings>) {
    onState(stateOf(await send({ type: "settings", patch })));
  }

  async function logout() {
    onState(stateOf(await send({ type: "logout" })));
  }

  return (
    <>
      <div className="popup-user">
        <span>{userId}</span>
        <button className="button-ghost" type="button" onClick={logout}>
          Выйти
        </button>
      </div>
      <label className="popup-field">
        <span>Компания</span>
        <select value={settings.clientId ?? ""} onChange={(event) => update({ clientId: event.target.value })}>
          {clients.map((id) => (
            <option key={id} value={id}>
              {companyName(id)}
            </option>
          ))}
        </select>
      </label>
      <label className="popup-field">
        <span>Роль</span>
        <select value={settings.role ?? ""} onChange={(event) => update({ role: event.target.value as Role })}>
          <option value="" disabled>
            Выберите роль
          </option>
          {ROLES.map(([role, label]) => (
            <option key={role} value={role}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <fieldset className="popup-autoshow">
        <legend>Показывать панель сразу</legend>
        {PAGE_TYPES.map(([type, label]) => (
          <label key={type} className="popup-check">
            <input
              type="checkbox"
              checked={settings.autoshow[type]}
              onChange={(event) => update({ autoshow: { ...settings.autoshow, [type]: event.target.checked } })}
            />
            {label}
          </label>
        ))}
      </fieldset>
    </>
  );
}

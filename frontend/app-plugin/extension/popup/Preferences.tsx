import { companyName } from "../../src/companies";
import { ROLES } from "../../src/roles";
import type { Role } from "../../src/types";
import { PAGE_TYPE_LABELS, type PageType } from "../config";
import type { ExtensionState, Send, SettingsPatch } from "../messages";

interface PreferencesProps {
  state: Extract<ExtensionState, { signedIn: true }>;
  send: Send;
  onState: (state: ExtensionState) => void;
}

const PAGE_TYPES = Object.entries(PAGE_TYPE_LABELS) as [PageType, string][];

export function Preferences({ state, send, onState }: PreferencesProps) {
  const { userId, clients, settings } = state;

  async function update(patch: SettingsPatch) {
    onState(await send({ type: "settings", patch }));
  }

  async function logout() {
    onState(await send({ type: "logout" }));
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
        <legend>Подсказка на странице, если есть событие</legend>
        {PAGE_TYPES.map(([type, label]) => (
          <label key={type} className="popup-check">
            <input
              type="checkbox"
              checked={settings.autoshow[type]}
              onChange={(event) => update({ autoshow: { [type]: event.target.checked } })}
            />
            {label}
          </label>
        ))}
      </fieldset>
    </>
  );
}

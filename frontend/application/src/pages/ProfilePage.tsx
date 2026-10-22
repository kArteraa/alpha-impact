import type { ClientProfile, Feature } from "@alpha-impact/plugin";
import { useCallback, useId, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { useCompany } from "../company/context";
import { FEATURES, type FeatureSpec } from "../data/profile";
import { formatFeatureValue, isEditable } from "../profile/features";
import { Alert } from "../ui/Alert";

const SOURCE_LABELS: Record<Feature["source"], string> = {
  bank: "по данным банка",
  graph: "определено по данным",
  inferred: "определено по данным",
  user: "изменено вами",
};

function displayValue(spec: FeatureSpec, value: Feature["value"]): string {
  return (typeof value === "string" && spec.options?.[value]) || formatFeatureValue(value);
}

interface FeatureCardProps {
  spec: FeatureSpec;
  feature: Feature;
  onSave: (value: string) => Promise<boolean>;
}

function FeatureCard({ spec, feature, onSave }: FeatureCardProps) {
  const labelId = useId();
  const [draft, setDraft] = useState<string | null>(null);
  const options = isEditable(feature) ? spec.options : undefined;

  async function save(value: string) {
    if (await onSave(value)) {
      setDraft(null);
    }
  }

  return (
    <li className="card feature" aria-labelledby={labelId}>
      <span id={labelId} className="muted">
        {spec.label}
      </span>
      {options === undefined || draft === null ? (
        <span className="feature-value">{displayValue(spec, feature.value)}</span>
      ) : (
        <select aria-label={spec.label} value={draft} onChange={(event) => setDraft(event.target.value)}>
          {Object.entries(options).map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </select>
      )}
      <span className="feature-source" data-source={feature.source}>
        {SOURCE_LABELS[feature.source]}
      </span>
      {options && (
        <span className="feature-actions">
          {draft === null ? (
            <button type="button" className="button-ghost" onClick={() => setDraft(String(feature.value))}>
              Изменить
            </button>
          ) : (
            <>
              <button type="button" className="button-primary button-xs" onClick={() => save(draft)}>
                Сохранить
              </button>
              <button type="button" className="button-ghost" onClick={() => setDraft(null)}>
                Отмена
              </button>
            </>
          )}
        </span>
      )}
    </li>
  );
}

interface FeatureListProps {
  profile: ClientProfile;
  onSave: (name: string, value: string) => Promise<boolean>;
}

function FeatureList({ profile, onSave }: FeatureListProps) {
  const names = Object.keys(FEATURES).filter((name) => name in profile.features);
  if (names.length === 0) {
    return <p className="card card-neutral muted">Данных о компании у банка нет</p>;
  }
  return (
    <ul className="features">
      {names.map((name) => (
        <FeatureCard
          key={name}
          spec={FEATURES[name]}
          feature={profile.features[name]}
          onSave={(value) => onSave(name, value)}
        />
      ))}
    </ul>
  );
}

export function ProfilePage() {
  const { company } = useCompany();
  const navigate = useNavigate();
  const [profile, setProfile] = useLoad(useCallback(() => api.profile(company.id), [company.id]));
  const [saveError, setSaveError] = useState<string | null>(null);

  async function save(name: string, value: string): Promise<boolean> {
    setSaveError(null);
    try {
      setProfile(await api.patchFeature(company.id, name, value));
      return true;
    } catch (failure) {
      setSaveError(failure instanceof ApiError ? `Не удалось сохранить (${failure.status})` : "Сервер недоступен");
      return false;
    }
  }

  return (
    <section>
      <h1>Профиль компании</h1>
      <p className="page-sub">Проверьте, что банк знает о компании: по этим признакам Alpha Impact отбирает события</p>
      {profile.status === "failed" && <Alert text="Не удалось загрузить профиль" />}
      {saveError && <Alert text={saveError} />}
      {profile.status === "ready" && (
        <>
          <FeatureList profile={profile.value} onSave={save} />
          <div className="form-actions">
            <button type="button" className="button" onClick={() => navigate("/")}>
              Всё верно
            </button>
          </div>
        </>
      )}
    </section>
  );
}

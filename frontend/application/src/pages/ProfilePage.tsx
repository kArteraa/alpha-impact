import type { ClientProfile, Feature } from "@alpha-impact/plugin";
import { useEffect, useId, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api/client";
import { useCompany } from "../company/context";
import { FEATURE_LABELS, INDUSTRY_FEATURE, INDUSTRY_LABELS } from "../data/profile";
import { formatFeatureValue, isEditable } from "../profile/editFeature";
import { Icon } from "../ui/Icon";

const SOURCE_LABELS: Record<Feature["source"], string> = {
  bank: "по данным банка",
  graph: "определено по данным",
  inferred: "определено по данным",
  user: "изменено вами",
};

const INDUSTRIES = Object.entries(INDUSTRY_LABELS);

type Loaded = { status: "loading" } | { status: "failed" } | { status: "ready"; profile: ClientProfile };

function displayValue(name: string, value: Feature["value"]): string {
  if (name === INDUSTRY_FEATURE && typeof value === "string") {
    return INDUSTRY_LABELS[value] ?? value;
  }
  return formatFeatureValue(value);
}

function Alert({ text }: { text: string }) {
  return (
    <p className="error" role="alert">
      <Icon name="alert" size={18} />
      {text}
    </p>
  );
}

interface FeatureCardProps {
  name: string;
  feature: Feature;
  onSave: (value: string) => Promise<boolean>;
}

function FeatureCard({ name, feature, onSave }: FeatureCardProps) {
  const labelId = useId();
  const label = FEATURE_LABELS[name];
  const [draft, setDraft] = useState<string | null>(null);

  async function save(value: string) {
    if (await onSave(value)) {
      setDraft(null);
    }
  }

  return (
    <li className="card feature" aria-labelledby={labelId}>
      <span id={labelId} className="muted">
        {label}
      </span>
      {draft === null ? (
        <span className="feature-value">{displayValue(name, feature.value)}</span>
      ) : (
        <select aria-label={label} value={draft} onChange={(event) => setDraft(event.target.value)}>
          {INDUSTRIES.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </select>
      )}
      <span className="feature-source" data-source={feature.source}>
        {SOURCE_LABELS[feature.source]}
      </span>
      {isEditable(feature) && (
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
  const names = Object.keys(FEATURE_LABELS).filter((name) => name in profile.features);
  if (names.length === 0) {
    return <p className="card card-neutral muted">Данных о компании у банка нет</p>;
  }
  return (
    <ul className="features">
      {names.map((name) => (
        <FeatureCard key={name} name={name} feature={profile.features[name]} onSave={(value) => onSave(name, value)} />
      ))}
    </ul>
  );
}

export function ProfilePage() {
  const { company } = useCompany();
  const navigate = useNavigate();
  const [loaded, setLoaded] = useState<Loaded>({ status: "loading" });
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.profile(company.id).then(
      (profile) => {
        if (active) {
          setLoaded({ status: "ready", profile });
        }
      },
      () => {
        if (active) {
          setLoaded({ status: "failed" });
        }
      },
    );
    return () => {
      active = false;
    };
  }, [company.id]);

  async function save(name: string, value: string): Promise<boolean> {
    setSaveError(null);
    try {
      setLoaded({ status: "ready", profile: await api.patchFeature(company.id, name, value) });
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
      {loaded.status === "failed" && <Alert text="Не удалось загрузить профиль" />}
      {saveError && <Alert text={saveError} />}
      {loaded.status === "ready" && (
        <>
          <FeatureList profile={loaded.profile} onSave={save} />
          <div className="profile-confirm">
            <button type="button" className="button" onClick={() => navigate("/")}>
              Всё верно
            </button>
          </div>
        </>
      )}
    </section>
  );
}

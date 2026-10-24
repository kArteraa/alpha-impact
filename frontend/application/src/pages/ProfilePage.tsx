import { type ClientProfile, type Feature, ROLE_LABELS } from "@alpha-impact/plugin";
import { useCallback, useId, useState } from "react";
import { Link, useNavigate } from "react-router";
import { ApiError, api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { useCompany } from "../company/context";
import { FEATURES } from "../data/profile";
import { useFeed } from "../feed/context";
import { type FeatureSection, featureText, groupFeatures, isEditable } from "../profile/features";
import { Alert } from "../ui/Alert";
import { useSession } from "../session/context";
import { Select } from "../ui/Select";

const SOURCE_LABELS: Record<Feature["source"], string> = {
  bank: "по данным банка",
  graph: "определено по данным",
  inferred: "определено по данным",
  user: "изменено вами",
};

interface FeatureRowProps {
  name: string;
  feature: Feature;
  onSave: (value: string) => Promise<string | null>;
}

function draftOf(options: Record<string, string>, value: Feature["value"]): string {
  return typeof value === "string" && Object.hasOwn(options, value) ? value : Object.keys(options)[0];
}

function FeatureRow({ name, feature, onSave }: FeatureRowProps) {
  const labelId = useId();
  const spec = FEATURES[name];
  const [draft, setDraft] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const options = spec.editable && isEditable(feature) ? spec.labels : undefined;

  async function save(value: string) {
    setSaving(true);
    setError(null);
    const failure = await onSave(value);
    setSaving(false);
    setError(failure);
    if (failure === null) {
      setDraft(null);
    }
  }

  function cancel() {
    setDraft(null);
    setError(null);
  }

  return (
    <li className="feature" aria-labelledby={labelId}>
      <span id={labelId} className={draft === null ? "feature-label" : "visually-hidden"}>
        {spec.label}
      </span>
      {options === undefined || draft === null ? (
        <span className="feature-value">{featureText(name, feature.value)}</span>
      ) : (
        <Select
          label={spec.label}
          value={draft}
          options={Object.entries(options).map(([value, text]) => ({ value, label: text }))}
          onChange={setDraft}
        />
      )}
      <span className="feature-meta">
        <span className="feature-source" data-source={feature.source}>
          {SOURCE_LABELS[feature.source]}
        </span>
        {options &&
          (draft === null ? (
            <button
              type="button"
              className="button-ghost"
              onClick={() => setDraft(draftOf(options, feature.value))}
            >
              Изменить
            </button>
          ) : (
            <span className="feature-actions">
              <button
                type="button"
                className="button-primary button-xs"
                disabled={saving}
                onClick={() => save(draft)}
              >
                Сохранить
              </button>
              <button type="button" className="button-ghost" disabled={saving} onClick={cancel}>
                Отмена
              </button>
            </span>
          ))}
      </span>
      {error && <Alert text={error} />}
    </li>
  );
}

interface GroupProps {
  section: FeatureSection;
  profile: ClientProfile;
  onSave: (name: string, value: string) => Promise<string | null>;
}

function FeatureGroup({ section, profile, onSave }: GroupProps) {
  const headingId = useId();
  return (
    <section className="card profile-group" aria-labelledby={headingId}>
      <h2 id={headingId}>{section.title}</h2>
      <ul className="features">
        {section.names.map((name) => (
          <FeatureRow
            key={name}
            name={name}
            feature={profile.features[name]}
            onSave={(value) => onSave(name, value)}
          />
        ))}
      </ul>
    </section>
  );
}

interface FeatureListProps {
  profile: ClientProfile;
  onSave: (name: string, value: string) => Promise<string | null>;
}

function FeatureList({ profile, onSave }: FeatureListProps) {
  const sections = groupFeatures(Object.keys(profile.features));
  if (sections.length === 0) {
    return <p className="card card-neutral muted">Данных о компании у банка нет</p>;
  }
  return (
    <div className="profile-groups">
      {sections.map((section) => (
        <FeatureGroup key={section.title} section={section} profile={profile} onSave={onSave} />
      ))}
    </div>
  );
}

export function ProfilePage() {
  const { company } = useCompany();
  const { role } = useSession();
  const navigate = useNavigate();
  const { retry: refreshFeed } = useFeed();
  const [profile, setProfile] = useLoad(useCallback(() => api.profile(company.id), [company.id]));

  async function save(name: string, value: string): Promise<string | null> {
    try {
      setProfile(await api.patchFeature(company.id, name, value));
      refreshFeed();
      return null;
    } catch (failure) {
      return failure instanceof ApiError ? `Не удалось сохранить (${failure.status})` : "Сервер недоступен";
    }
  }

  return (
    <section>
      <div className="page-head">
        <h1>Профиль компании</h1>
        <p className="page-sub">
          Проверьте, что банк знает о компании: по этим признакам Alpha Impact отбирает события
        </p>
        <p className="page-sub">
          <span>Роль: {ROLE_LABELS[role]}</span> · <Link to="/role">Сменить роль</Link>
        </p>
      </div>
      {profile.status === "failed" && <Alert text="Не удалось загрузить профиль" />}
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

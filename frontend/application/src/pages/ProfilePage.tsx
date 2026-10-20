import type { Feature } from "@alpha-impact/plugin";
import { useId, useState } from "react";
import { FEATURE_LABELS, PROFILE_FEATURES } from "../data/profile";
import { editFeature, type Features, formatFeatureValue, isEditable } from "../profile/editFeature";

const SOURCE_LABELS: Record<Feature["source"], string> = {
  bank: "по данным банка",
  graph: "определено по данным",
  inferred: "определено по данным",
  user: "изменено вами",
};

interface FeatureCardProps {
  label: string;
  feature: Feature;
  onSave: (value: string) => void;
}

function FeatureCard({ label, feature, onSave }: FeatureCardProps) {
  const labelId = useId();
  const [draft, setDraft] = useState<string | null>(null);

  function save(value: string) {
    onSave(value);
    setDraft(null);
  }

  return (
    <li className="card feature" aria-labelledby={labelId}>
      <span id={labelId} className="muted">
        {label}
      </span>
      {draft === null ? (
        <span className="feature-value">{formatFeatureValue(feature.value)}</span>
      ) : (
        <input aria-label={label} value={draft} onChange={(event) => setDraft(event.target.value)} />
      )}
      <span className="feature-source" data-source={feature.source}>
        {SOURCE_LABELS[feature.source]}
      </span>
      {isEditable(feature) && (
        <span className="feature-actions">
          {draft === null ? (
            <button type="button" className="button-ghost" onClick={() => setDraft(formatFeatureValue(feature.value))}>
              Изменить
            </button>
          ) : (
            <>
              <button type="button" className="button-secondary" onClick={() => save(draft)}>
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

export function ProfilePage() {
  const [features, setFeatures] = useState<Features>(PROFILE_FEATURES);
  return (
    <section>
      <h1>Профиль компании</h1>
      <ul className="features">
        {Object.entries(features).map(([key, feature]) => (
          <FeatureCard
            key={key}
            label={FEATURE_LABELS[key]}
            feature={feature}
            onSave={(value) => setFeatures((current) => editFeature(current, key, value))}
          />
        ))}
      </ul>
    </section>
  );
}

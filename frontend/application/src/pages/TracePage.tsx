import { useParams } from "react-router";

export function TracePage() {
  const { id } = useParams();
  return (
    <section>
      <h1>Трасса {id}</h1>
      <div className="card">Экран «как получен вывод» появится в задаче AH-33.</div>
    </section>
  );
}

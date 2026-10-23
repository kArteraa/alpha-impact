const LINES = 3;

export function Skeleton({ text }: { text: string }) {
  return (
    <>
      {Array.from({ length: LINES }, (_, index) => (
        <span key={index} className="insight-skeleton" />
      ))}
      <p className="empty">{text}</p>
    </>
  );
}

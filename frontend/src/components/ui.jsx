export function bandClass(band) {
  const b = (band || "").toLowerCase();
  if (b === "sit") return "band band-sit";
  if (b === "crawl") return "band band-crawl";
  if (b === "walk") return "band band-walk";
  if (b === "run") return "band band-run";
  return "band";
}

export function Chip({ children }) {
  return <span className="chip">{children}</span>;
}

export function Sep() {
  return <div className="sep" />;
}

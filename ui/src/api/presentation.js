export function locationName(node) {
  if (!node) return "Select a location";
  const name = node.name || node.id || "";
  if (/^demo-\d+$/.test(name)) return `Location ${name.split("-")[1]}`;
  if (name === "mandi-api-grid" || name === "mandi-api-current") return "Mandi";
  return name;
}
export function sourceName(source) {
  return (
    {
      synthetic_demo: "Simulated readings",
      modeled_grid: "Weather model",
      physical_indra: "Sensor readings",
      observed_external_station: "Station readings",
    }[source] || "Source unavailable"
  );
}
export function readingTime(value) {
  if (!value) return "Waiting for a reading";
  return (
    new Intl.DateTimeFormat("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Kolkata",
    }).format(new Date(value)) + " IST"
  );
}
export function ageLabel(value) {
  const minutes = Math.max(0, Math.floor((Date.now() - value) / 60000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} hr ago`;
  return `${Math.floor(minutes / 1440)} days ago`;
}

export function locationName(node) {
  if (!node) return "Select a location";
  const name = node.name || node.id || "";
  if (name === "mandi-api-current") return "Mandi";
  return name;
}
export function sourceName(source) {
  return (
    {
      modeled_grid: "Mandi modeled data",
      physical_sensor: "Your ESP32 sensor",
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

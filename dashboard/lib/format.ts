const dt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/London",
});

export function when(iso: string | null | undefined): string {
  return iso ? dt.format(new Date(iso)) : "–";
}

export function short(id: string): string {
  return id.slice(0, 8);
}

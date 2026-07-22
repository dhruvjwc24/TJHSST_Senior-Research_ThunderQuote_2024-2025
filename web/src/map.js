import { geoAlbersUsa, geoPath } from "d3-geo";

function color(value) {
  if (!Number.isFinite(value) || value <= 0) return "#d9ddd8";
  const normalized = Math.max(0, Math.min(1, (value - 55) / 115));
  const start = [220, 235, 220];
  const end = [23, 75, 58];
  return `rgb(${start.map((channel, index) => Math.round(channel + (end[index] - channel) * normalized)).join(",")})`;
}

export function renderMap(
  container,
  geojson,
  { valueFor, labelFor, onSelect },
) {
  const width = Math.max(container.clientWidth || 760, 320);
  const height = Math.max(Math.min(width * 0.7, 650), 300);
  const projection = geoAlbersUsa().fitExtent(
    [
      [18, 18],
      [width - 18, height - 18],
    ],
    geojson,
  );
  const path = geoPath(projection);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "group");
  svg.setAttribute("aria-label", "Interactive geography map");
  for (const feature of geojson.features) {
    const label = labelFor(feature);
    const shape = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "path",
    );
    shape.setAttribute("d", path(feature) ?? "");
    shape.setAttribute("fill", color(valueFor(feature)));
    shape.setAttribute("tabindex", "0");
    shape.setAttribute("role", "button");
    shape.setAttribute("aria-label", label);
    const title = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "title",
    );
    title.textContent = label;
    shape.append(title);
    shape.addEventListener("click", () => onSelect(feature));
    shape.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onSelect(feature);
      }
    });
    svg.append(shape);
  }
  container.replaceChildren(svg);
}

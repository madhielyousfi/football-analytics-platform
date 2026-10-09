import { initials } from "@/lib/api";

export function Crest({ name, url, size = 23 }: { name: string; url?: string | null; size?: number }) {
  if (url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt={name} width={size} height={size} style={{ width: size, height: size, objectFit: "contain", flex: "none" }} loading="lazy" />;
  }
  return (
    <span className="grid flex-none place-items-center rounded-md bg-slate-800 text-[0.6rem] font-bold text-muted"
      style={{ width: size, height: size }}>{initials(name)}</span>
  );
}

export function FormBadge({ form }: { form?: string | null }) {
  if (!form) return <span className="text-faint text-xs">–</span>;
  return (
    <span className="inline-flex items-center gap-1">
      {form.split("").map((r, i) => (
        <span key={i} className="grid h-[23px] w-[23px] place-items-center rounded-full text-[0.65rem] font-extrabold"
          style={{ background: r === "W" ? "#22C55E" : r === "D" ? "#F59E0B" : "#EF4444", color: r === "L" ? "#fff" : "#080B12" }}>{r}</span>
      ))}
    </span>
  );
}

export function PageHeader({ eyebrow, title, sub, right }: { eyebrow: string; title: string; sub?: string; right?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 flex-1 basis-56">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="h-display break-words">{title}</h1>
        {sub && <p className="subtle">{sub}</p>}
      </div>
      {right && <div className="flex flex-wrap items-center gap-2">{right}</div>}
    </div>
  );
}

export function Kpi({ label, value, note, icon, tint }: { label: string; value: string; note?: string; icon: string; tint: "green" | "cyan" | "violet" | "amber" }) {
  const color = { green: "text-green-400", cyan: "text-cyan-300", violet: "text-violet-300", amber: "text-amber-300" }[tint];
  return (
    <div className="card min-h-[122px]">
      <div className="flex items-center justify-between text-xs font-semibold text-muted">
        <span>{label}</span>
        <span className="grid h-[29px] w-[29px] place-items-center rounded-[9px] bg-white/5">{icon}</span>
      </div>
      <p className={`mt-2 text-[1.75rem] font-extrabold tracking-tight ${color}`}>{value}</p>
      {note && <p className="mt-1 text-xs text-faint">{note}</p>}
    </div>
  );
}

export function Empty({ msg }: { msg: string }) {
  return <div className="card text-center text-sm text-muted">{msg}</div>;
}

export function SkeletonGrid() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-[122px]" />)}
    </div>
  );
}

import { Link } from "react-router-dom";

const steps = [
  { icon: "🔩", title: "Browse Designs", description: "Discover and inspect OKH hardware designs.", to: "/okh" },
  { icon: "⚡", title: "Run Match", description: "Match a design to manufacturing facilities.", to: "/match" },
  { icon: "🗺️", title: "Visualize", description: "Explore supply chain graphs and KPIs.", to: "/visualization" },
  { icon: "📄", title: "Export RFQ", description: "Generate request-for-quote documents.", to: "/rfq" },
] as const;

export function HomePage() {
  return (
    <div className="py-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-800 dark:text-slate-100">
          Open Hardware Matchmaker
        </h1>
        <p className="mt-3 text-lg text-slate-500 dark:text-slate-400">
          Discover designs · Match facilities · Visualize supply chains · Export RFQs
        </p>
      </div>

      <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map(({ icon, title, description, to }) => (
          <Link
            key={to}
            to={to}
            className="group flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md no-underline dark:border-slate-700 dark:bg-slate-900 dark:hover:shadow-slate-800"
          >
            <span className="text-3xl" aria-hidden="true">{icon}</span>
            <div>
              <p className="font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors dark:text-slate-100 dark:group-hover:text-indigo-400">{title}</p>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

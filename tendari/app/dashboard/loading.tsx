export default function DashboardLoading() {
  return (
    <div className="animate-pulse">
      <div className="h-7 w-48 rounded bg-deep-green/10" />
      <div className="mt-3 h-4 w-72 rounded bg-deep-green/10" />
      <div className="mt-8 grid gap-4 grid-cols-2 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="card">
            <div className="h-4 w-20 rounded bg-deep-green/10" />
            <div className="mt-3 h-7 w-16 rounded bg-deep-green/10" />
          </div>
        ))}
      </div>
      <div className="card mt-8 h-40" />
    </div>
  );
}

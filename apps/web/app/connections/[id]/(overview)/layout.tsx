import ConnectionSubNav from "@/components/ConnectionSubNav";

/**
 * Shared shell for the three connection-scoped tabs (workflows, alerts,
 * settings) - keeps their container width, and therefore ConnectionSubNav's
 * width, identical instead of each page picking its own max-w.
 */
export default async function ConnectionOverviewLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="max-w-3xl mx-auto mt-12 px-4">
      <ConnectionSubNav connectionId={id} />
      {children}
    </div>
  );
}

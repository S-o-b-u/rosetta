import { RosettaDesktop } from "@/components/desktop/RosettaDesktop";
import { MigrationProvider } from "@/lib/migration";

export default function Home() {
  return (
    <main className="min-h-screen bg-black">
      <MigrationProvider>
        <RosettaDesktop />
      </MigrationProvider>
    </main>
  );
}

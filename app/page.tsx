import Hero from '@/components/hero';
import BentoGrid from '@/components/bento-grid';

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-sky-500 selection:text-white">
      <Hero />
      <BentoGrid />
    </main>
  );
}

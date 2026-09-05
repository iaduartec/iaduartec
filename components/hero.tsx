'use client';

import React from 'react';
import { motion, useMotionValue, useMotionTemplate } from 'framer-motion';
import { ArrowRight, Server, Cable, ShieldCheck, Wifi } from 'lucide-react';

export default function Hero() {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  function onMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
    const { left, top } = currentTarget.getBoundingClientRect();
    mouseX.set(clientX - left);
    mouseY.set(clientY - top);
  }

  const background = useMotionTemplate`radial-gradient(650px circle at ${mouseX}px ${mouseY}px, rgba(14, 165, 233, 0.15), transparent 80%)`;

  return (
    <div
      className="relative flex min-h-[80vh] w-full flex-col items-center justify-center overflow-hidden bg-slate-950 px-4 py-20"
      onMouseMove={onMouseMove}
    >
      <motion.div
        className="pointer-events-none absolute inset-0 z-0"
        style={{ background }}
      />
      
      {/* Grid background */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)]" />

      <div className="relative z-10 flex w-full max-w-5xl flex-col items-center text-center">
        {/* Badge */}
        <div className="mb-8 flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/50 px-4 py-1.5 backdrop-blur-md">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          <span className="text-sm font-medium text-slate-300">Infraestructura IT & Redes · Burgos y provincia</span>
        </div>

        {/* H1 */}
        <h1 className="mb-6 max-w-4xl text-5xl font-bold tracking-tight text-white md:text-7xl">
          Conectamos y protegemos el <span className="bg-gradient-to-r from-sky-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">núcleo digital de tu empresa</span>
        </h1>

        {/* Párrafo */}
        <p className="mb-10 max-w-2xl text-xl text-slate-400">
          Ingeniería de redes, montaje y saneamiento de Racks, cableado estructurado Cat 6A/7, servidores locales y seguridad perimetral CCTV.
        </p>

        {/* CTAs */}
        <div className="mb-16 flex flex-wrap justify-center gap-4">
          <button className="flex items-center gap-2 rounded-lg bg-sky-500 px-8 py-3 font-semibold text-white shadow-lg shadow-sky-500/25 transition-transform hover:scale-105 active:scale-95">
            Solicitar Estudio Técnico
            <ArrowRight size={18} />
          </button>
          <button className="rounded-lg border border-slate-800 bg-slate-900/50 px-8 py-3 font-semibold text-slate-200 backdrop-blur-md transition-colors hover:bg-slate-800">
            Ver Instalaciones
          </button>
        </div>

        {/* Micro-chips */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {[
            { icon: Server, label: 'Racks Certificados' },
            { icon: Cable, label: 'Fibra Óptica' },
            { icon: ShieldCheck, label: 'CCTV IP' },
            { icon: Wifi, label: 'WiFi Corporativo' },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/30 px-4 py-3 text-slate-300 backdrop-blur-sm">
              <item.icon size={18} className="text-sky-500" />
              <span className="text-sm font-medium">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

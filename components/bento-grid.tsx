'use client';

import React from 'react';
import { motion, useMotionTemplate, useMotionValue } from 'framer-motion';
import { Cable, ShieldCheck, Server, Network, LucideIcon } from 'lucide-react';

interface BentoCardProps {
  title: string;
  badge: string;
  description: string;
  icon: LucideIcon;
  className?: string;
}

function BentoCard({ title, badge, description, icon: Icon, className = '' }: BentoCardProps) {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  function onMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
    const { left, top } = currentTarget.getBoundingClientRect();
    mouseX.set(clientX - left);
    mouseY.set(clientY - top);
  }

  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 p-6 transition-all hover:border-slate-700 ${className}`}
      onMouseMove={onMouseMove}
    >
      <motion.div
        className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition duration-300 group-hover:opacity-100"
        style={{
          background: useMotionTemplate`radial-gradient(400px circle at ${mouseX}px ${mouseY}px, rgba(56, 189, 248, 0.15), transparent 80%)`,
        }}
      />
      <div className="relative z-10">
        <div className="mb-4 flex items-center justify-between">
          <div className="rounded-lg bg-slate-800/80 p-2 text-sky-400">
            <Icon size={24} />
          </div>
          <span className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1 text-xs font-medium text-slate-300">
            {badge}
          </span>
        </div>
        <h3 className="mb-2 text-xl font-bold text-white">{title}</h3>
        <p className="text-slate-400">{description}</p>
      </div>
    </div>
  );
}

export default function BentoGrid() {
  const features = [
    {
      title: 'Infraestructura de Redes',
      badge: 'Cat 6A / 7',
      description: 'Diseño, montaje y certificación de redes de datos, cableado estructurado de alto rendimiento y fibra óptica para naves y oficinas.',
      icon: Cable,
      className: 'col-span-1 md:col-span-2',
    },
    {
      title: 'Seguridad y Vigilancia',
      badge: 'CCTV IP',
      description: 'Sistemas de videovigilancia IP inteligente, analítica de vídeo avanzada y control de accesos perimetral integrado.',
      icon: ShieldCheck,
      className: 'col-span-1',
    },
    {
      title: 'Gestión de Servidores',
      badge: 'On-Premise / Cloud',
      description: 'Implementación y mantenimiento de servidores locales, entornos de virtualización, cabinas NAS/SAN y políticas de copias de seguridad.',
      icon: Server,
      className: 'col-span-1',
    },
    {
      title: 'Conectividad Corporativa',
      badge: 'WiFi 6 / VLANs',
      description: 'Despliegue de redes inalámbricas WiFi unificadas, segmentación mediante VLANs y seguridad perimetral avanzada.',
      icon: Network,
      className: 'col-span-1 md:col-span-2',
    },
  ];

  return (
    <section className="mx-auto max-w-6xl px-4 py-20">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {features.map((feature, i) => (
          <BentoCard key={i} {...feature} />
        ))}
      </div>
    </section>
  );
}

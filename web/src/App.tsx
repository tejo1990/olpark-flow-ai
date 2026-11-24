import React, { useEffect, useState } from 'react';
import { Activity, BarChart3, Globe, MapPin, ShieldCheck, Sliders } from 'lucide-react';
import { TabVisitor } from './components/TabVisitor';
import { TabSimulator } from './components/TabSimulator';
import { TabBacktest } from './components/TabBacktest';
import { TabOpsAudit } from './components/TabOpsAudit';
import type { Lang, WebEventsBundle, WebModelBundle } from './types';

type TabKey = 'visitor' | 'simulator' | 'backtest' | 'ops';

export const App: React.FC = () => {
  const [lang, setLang] = useState<Lang>('ko');
  const [tab, setTab] = useState<TabKey>('visitor');
  const [model, setModel] = useState<WebModelBundle | null>(null);
  const [events, setEvents] = useState<WebEventsBundle | null>(null);
  const [liveParkingSum, setLiveParkingSum] = useState<number | null>(null);
  const [liveSource, setLiveSource] = useState<'live' | 'snapshot'>('snapshot');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [mRes, eRes] = await Promise.all([
          fetch('/data/web_model_bundle.json'),
          fetch('/data/web_events_bundle.json'),
        ]);
        if (!mRes.ok) throw new Error(`Model bundle HTTP ${mRes.status}`);
        const mJson = (await mRes.json()) as WebModelBundle;
        const eJson = eRes.ok ? ((await eRes.json()) as WebEventsBundle) : null;
        if (active) {
          setModel(mJson);
          setEvents(eJson);
        }
      } catch (err) {
        if (active) setError(String(err));
      }

      // Live real-time parking fetch with graceful fallback to verified snapshot
      try {
        const liveRes = await fetch('/api/realtime-parking');
        if (liveRes.ok) {
          const arr = await liveRes.json();
          const val = Array.isArray(arr) ? arr[0]?.parking_sum : arr?.parking_sum;
          if (typeof val === 'number' && active) {
            setLiveParkingSum(val);
            setLiveSource('live');
            return;
          }
        }
      } catch {
        // Fallback below
      }
      try {
        const snapRes = await fetch('/data/realtime_parking.json');
        if (snapRes.ok) {
          const snap = await snapRes.json();
          if (typeof snap?.parking_sum === 'number' && active) {
            setLiveParkingSum(snap.parking_sum);
            setLiveSource('snapshot');
          }
        }
      } catch {
        // Ignore
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const ko = lang === 'ko';
  const tabs: Array<{ key: TabKey; ko: string; en: string; icon: React.ReactNode }> = [
    { key: 'visitor', ko: '방문객 3D 도착 가이드', en: '3D Visitor Guide', icon: <MapPin className="h-4 w-4" /> },
    { key: 'simulator', ko: '공단 B2G · ESG 시뮬레이터', en: 'B2G ESG Simulator', icon: <Sliders className="h-4 w-4" /> },
    { key: 'backtest', ko: '2025 실측 AI 검증실', en: '2025 AI Backtest', icon: <BarChart3 className="h-4 w-4" /> },
    { key: 'ops', ko: '2028 무중단 · 품질 감사', en: '2028 Ops & DQ Audit', icon: <ShieldCheck className="h-4 w-4" /> },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Top Bar */}
      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 font-black text-white shadow-lg shadow-blue-500/20">
              OF
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white sm:text-base">
                Olpark Flow AI{' '}
                <span className="ml-1.5 hidden rounded-md bg-blue-500/15 px-2 py-0.5 text-[11px] font-medium text-blue-300 sm:inline">
                  2026 한국체육산업개발 공공데이터 경진대회
                </span>
              </h1>
              <p className="text-[11px] text-slate-400">
                {ko
                  ? '올림픽공원 공연·날씨·입출차 3D 혼잡 예측 & 게이트·ESG 분산 플랫폼'
                  : 'Olympic Park 3D Crowd/Parking AI Forecast & ESG Dispersion Twin'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Live Parking Pill */}
            <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              <span className="text-slate-400">{ko ? '현재 주차' : 'Live Park'}</span>
              <span className="font-mono font-bold text-white">
                {liveParkingSum !== null ? `${liveParkingSum.toLocaleString()}${ko ? '대' : ''}` : '...'}
              </span>
              <Activity className="h-3.5 w-3.5 text-emerald-400" />
            </div>

            {/* KR / EN Toggle */}
            <button
              onClick={() => setLang((l) => (l === 'ko' ? 'en' : 'ko'))}
              className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-blue-500 hover:text-white"
            >
              <Globe className="h-3.5 w-3.5 text-blue-400" />
              {lang === 'ko' ? 'EN' : '한국어'}
            </button>
          </div>
        </div>

        {/* 4-Tab Nav */}
        <div className="mx-auto max-w-7xl px-4 pb-2.5">
          <nav className="flex gap-1.5 overflow-x-auto">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition ${
                  tab === t.key
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/25'
                    : 'bg-slate-900/70 text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                }`}
              >
                {t.icon}
                {ko ? t.ko : t.en}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-5">
        {error ? (
          <div className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-6 text-sm text-rose-200">
            Data load error: {error}
          </div>
        ) : !model ? (
          <div className="flex h-64 items-center justify-center text-sm text-slate-400">
            Loading 2025 AI Model Bundle...
          </div>
        ) : (
          <>
            {tab === 'visitor' && <TabVisitor lang={lang} model={model} events={events} />}
            {tab === 'simulator' && <TabSimulator lang={lang} model={model} />}
            {tab === 'backtest' && <TabBacktest lang={lang} model={model} />}
            {tab === 'ops' && (
              <TabOpsAudit
                lang={lang}
                model={model}
                liveParkingSum={liveParkingSum}
                liveSource={liveSource}
              />
            )}
          </>
        )}
      </main>

      <footer className="mt-8 border-t border-slate-900 py-5 text-center text-[11px] text-slate-500">
        Olpark Flow AI · 2026 한국체육산업개발(주) 공공데이터 활용 경진대회 출품 프로토타입 · Zero-Cost Serverless (2028 Ready)
      </footer>
    </div>
  );
};

export default App;

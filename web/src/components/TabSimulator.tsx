import React, { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Building2, Leaf, Sliders, Sparkles, TrendingDown } from 'lucide-react';
import { OLYMPIC_PARK_VENUES } from '../data/parkGeometry';
import type { ConcertTierKey, Lang, WeatherKey, WebModelBundle } from '../types';

interface TabSimulatorProps {
  lang: Lang;
  model: WebModelBundle;
}

const CO2_KG_PER_CAR_MIN = 0.021; // Ministry of Environment idling factor (~1.26 kg/hr)
const PINE_TREE_KG_PER_YEAR = 6.6; // National Institute of Forest Science (30-year pine)

export const TabSimulator: React.FC<TabSimulatorProps> = ({ lang, model }) => {
  const ko = lang === 'ko';
  const [selectedVenues, setSelectedVenues] = useState<string[]>(['kspo_dome', 'handball']);
  const [weather, setWeather] = useState<WeatherKey>('rain');
  const [staggerMin, setStaggerMin] = useState<number>(30);
  const [transitShiftPct, setTransitShiftPct] = useState<number>(15);
  const [signageDivertPct, setSignageDivertPct] = useState<number>(20);

  const toggleVenue = (id: string) => {
    setSelectedVenues((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const totalAudience = useMemo(
    () =>
      OLYMPIC_PARK_VENUES.filter((v) => selectedVenues.includes(v.id)).reduce(
        (acc, v) => acc + v.capacity,
        0
      ),
    [selectedVenues]
  );

  // Map simulated audience smoothly onto trained Ensemble grid tiers
  const tier: ConcertTierKey =
    totalAudience === 0
      ? 'none'
      : totalAudience <= 4500
        ? 'small_3k'
        : totalAudience <= 11000
          ? 'medium_8k'
          : totalAudience <= 19000
            ? 'large_15k'
            : 'mega_25k';

  const baseCurve = model.prediction_grid.curves[`autumn|weekend|${tier}|${weather}`] ??
    Object.values(model.prediction_grid.curves)[0];

  // Apply B2G policy levers: staggered exit/entry smooths peak spikes; transit shift lowers total car demand
  const simData = useMemo(() => {
    const shiftFactor = 1 - transitShiftPct / 100;
    const smoothAlpha = staggerMin === 0 ? 0 : staggerMin === 30 ? 0.22 : 0.36;
    const raw = baseCurve.parking;

    return Array.from({ length: 24 }, (_, h) => {
      const before = raw[h];
      const prev = raw[Math.max(0, h - 1)];
      const next = raw[Math.min(23, h + 1)];
      const smoothed = before * (1 - smoothAlpha) + ((prev + next) / 2) * smoothAlpha;
      const after = Math.round(smoothed * shiftFactor);
      return {
        hour: `${String(h).padStart(2, '0')}시`,
        before,
        after,
      };
    });
  }, [baseCurve, staggerMin, transitShiftPct]);

  const peakBefore = Math.max(...simData.map((d) => d.before));
  const peakAfter = Math.max(...simData.map((d) => d.after));
  const peakDropPct = peakBefore > 0 ? Math.round(((peakBefore - peakAfter) / peakBefore) * 1000) / 10 : 0;

  // ESG Idling CO2 savings model anchored to 2024.07 empirical exit surge (1,836 exits 19~22h)
  const estExitVehicles = Math.round(
    (model.esg_baseline.avg_exits_19_22_on_peak_day || 1836) * (peakBefore / 2800)
  );
  const baseQueueMin = weather === 'rain' ? 22 : 15;
  const reducedQueueMin = Math.max(
    3,
    Math.round(baseQueueMin * (1 - (staggerMin / 120) - signageDivertPct / 160))
  );
  const co2BeforeKg = Math.round(estExitVehicles * 0.45 * baseQueueMin * CO2_KG_PER_CAR_MIN);
  const co2AfterKg = Math.round(
    estExitVehicles * (1 - transitShiftPct / 100) * 0.35 * reducedQueueMin * CO2_KG_PER_CAR_MIN
  );
  const co2SavedKg = Math.max(0, co2BeforeKg - co2AfterKg);
  const annualCo2SavedTons = ((co2SavedKg * 113) / 1000).toFixed(1); // 113 real 2025 concert days
  const pineTreesEq = Math.round((co2SavedKg * 113) / PINE_TREE_KG_PER_YEAR);

  return (
    <div className="space-y-5">
      {/* Top Scenario Builder */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/85 p-5 lg:col-span-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
              <Building2 className="h-4 w-4 text-blue-400" />
              {ko ? '1. 동시 대관 공연장 조합 선택 (B2G 심사 시나리오)' : '1. Simultaneous Multi-Venue Rental Config'}
            </h3>
            <span className="rounded-lg bg-blue-500/20 px-2.5 py-1 text-xs font-bold text-blue-300">
              {ko ? `총 수용 ${totalAudience.toLocaleString()}명` : `Total ${totalAudience.toLocaleString()} pax`}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {OLYMPIC_PARK_VENUES.map((v) => {
              const active = selectedVenues.includes(v.id);
              return (
                <button
                  key={v.id}
                  onClick={() => toggleVenue(v.id)}
                  className={`flex items-center justify-between rounded-xl border p-3 text-left text-xs transition ${
                    active
                      ? 'border-blue-500 bg-blue-600/20 text-white'
                      : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="font-semibold">{ko ? v.nameKo : v.nameEn}</div>
                    <div className="mt-0.5 text-[10px] opacity-75">{v.nearestGate}</div>
                  </div>
                  <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-[11px]">
                    {v.capacity.toLocaleString()}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/85 p-5 lg:col-span-6">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <Sliders className="h-4 w-4 text-emerald-400" />
            {ko ? '2. 공단 분산·ESG 개입 정책 레버' : '2. KSPO&CO Dispersion & ESG Policy Levers'}
          </h3>

          <div className="space-y-4 text-xs">
            <div>
              <div className="mb-1 flex justify-between">
                <span className="text-slate-300">{ko ? '동시 대관 시차 입장·퇴장 편성' : 'Staggered Show Start/Exit Offset'}</span>
                <span className="font-bold text-blue-300">{staggerMin}{ko ? '분' : ' min'}</span>
              </div>
              <div className="flex gap-2">
                {[0, 30, 60].map((m) => (
                  <button
                    key={m}
                    onClick={() => setStaggerMin(m)}
                    className={`flex-1 rounded-lg border py-1.5 font-medium transition ${
                      staggerMin === m
                        ? 'border-blue-500 bg-blue-600 text-white'
                        : 'border-slate-700 bg-slate-950 text-slate-300'
                    }`}
                  >
                    {m === 0 ? (ko ? '시차 없음 (동시)' : '0m (Simultaneous)') : `${m}${ko ? '분 시차' : 'm Offset'}`}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-1 flex justify-between">
                <span className="text-slate-300">{ko ? '사전 알림 기반 대중교통(5·8·9호선) 전환율' : 'Pre-Alert Subway Mode Shift'}</span>
                <span className="font-bold text-emerald-300">{transitShiftPct}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={30}
                step={5}
                value={transitShiftPct}
                onChange={(e) => setTransitShiftPct(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
            </div>

            <div>
              <div className="mb-1 flex justify-between">
                <span className="text-slate-300">{ko ? 'P11·P5 → P1A·P1B 가변 전광판 분산율' : 'Dynamic VMS Rerouting (P11/P5 -> P1A/P1B)'}</span>
                <span className="font-bold text-amber-300">{signageDivertPct}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={35}
                step={5}
                value={signageDivertPct}
                onChange={(e) => setSignageDivertPct(Number(e.target.value))}
                className="w-full accent-amber-500"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-slate-400">{ko ? '기상 스트레스 테스트' : 'Weather Stress Test'}</span>
              <div className="flex gap-2">
                {(['clear', 'rain'] as const).map((w) => (
                  <button
                    key={w}
                    onClick={() => setWeather(w)}
                    className={`rounded-lg border px-3 py-1 text-xs ${
                      weather === w
                        ? 'border-sky-500 bg-sky-600/30 text-sky-200'
                        : 'border-slate-700 bg-slate-950 text-slate-400'
                    }`}
                  >
                    {w === 'clear' ? (ko ? '맑음' : 'Clear') : (ko ? '우천(피크 가중)' : 'Rain Stress')}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Impact KPI Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-blue-500/30 bg-blue-950/20 p-4">
          <div className="flex items-center justify-between text-xs text-blue-300">
            <span>{ko ? '피크 주차부하 감축' : 'Peak Parking Load Cut'}</span>
            <TrendingDown className="h-4 w-4" />
          </div>
          <div className="mt-1.5 text-2xl font-bold text-white">-{peakDropPct}%</div>
          <div className="mt-1 text-[11px] text-slate-400">
            {peakBefore.toLocaleString()} → {peakAfter.toLocaleString()} {ko ? '대' : 'cars'}
          </div>
        </div>

        <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4">
          <div className="flex items-center justify-between text-xs text-amber-300">
            <span>{ko ? '출차 대기시간 단축' : 'Exit Queue Reduction'}</span>
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="mt-1.5 text-2xl font-bold text-white">
            {baseQueueMin} → {reducedQueueMin}
            <span className="ml-1 text-xs font-normal text-slate-300">{ko ? '분' : 'min'}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {ko ? `19~22시 추정 출차 ${estExitVehicles.toLocaleString()}대 기준` : `Based on ${estExitVehicles.toLocaleString()} evening exits`}
          </div>
        </div>

        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/25 p-4">
          <div className="flex items-center justify-between text-xs text-emerald-300">
            <span>{ko ? '공연 1회 공회전 CO₂ 절감' : 'Idling CO₂ Saved / Event'}</span>
            <Leaf className="h-4 w-4" />
          </div>
          <div className="mt-1.5 text-2xl font-bold text-emerald-200">
            -{co2SavedKg.toLocaleString()} <span className="text-xs font-normal">kg CO₂</span>
          </div>
          <div className="mt-1 text-[11px] text-emerald-300/80">
            {ko ? `환경부 공회전 계수 21g/분 적용` : 'MOE 21g CO₂/min idling factor'}
          </div>
        </div>

        <div className="rounded-2xl border border-teal-500/30 bg-teal-950/25 p-4">
          <div className="flex items-center justify-between text-xs text-teal-300">
            <span>{ko ? '연간 ESG 환산 (113 공연일)' : 'Annual ESG Impact (113 Days)'}</span>
            <Leaf className="h-4 w-4" />
          </div>
          <div className="mt-1.5 text-2xl font-bold text-teal-200">
            {annualCo2SavedTons} <span className="text-xs font-normal">tCO₂</span>
          </div>
          <div className="mt-1 text-[11px] text-teal-300/80">
            {ko ? `30년생 소나무 약 ${pineTreesEq.toLocaleString()}그루 식재 효과` : `≈ ${pineTreesEq.toLocaleString()} pine trees / yr`}
          </div>
        </div>
      </div>

      {/* Before vs After Chart */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-white">
            {ko ? '정책 개입 전(현행) vs 개입 후(시차·대중교통 분산) 24시간 주차 부하 비교' : 'Before vs After Policy Intervention (24h Parking Load)'}
          </h3>
          <span className="text-[11px] text-slate-400">
            {ko ? '2025 앙상블 모델 예측 기반 실시간 시뮬레이션' : 'Powered by trained 2025 RF+HGB Ensemble'}
          </span>
        </div>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={simData} margin={{ top: 10, right: 16, left: -6, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" tick={{ fill: '#94a3b8', fontSize: 11 }} interval={2} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '10px', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey="before"
                name={ko ? '개입 전 (현행 동시대관)' : 'Baseline (Unmanaged)'}
                stroke="#f43f5e"
                strokeWidth={2.5}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="after"
                name={ko ? '개입 후 (시차·분산 적용)' : 'With Dispersion Policy'}
                stroke="#10b981"
                strokeWidth={2.8}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

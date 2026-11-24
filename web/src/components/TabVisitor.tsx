import React, { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  AlertTriangle,
  Car,
  ChevronDown,
  ChevronUp,
  Clock,
  CloudRain,
  Compass,
  Info,
  SlidersHorizontal,
  Sun,
  Train,
  Users,
} from 'lucide-react';
import { ParkMap3D, computeZoneStates } from './ParkMap3D';
import { SUBWAY_STATIONS } from '../data/parkGeometry';
import type {
  ConcertTierKey,
  DayTypeKey,
  Lang,
  SeasonKey,
  WeatherKey,
  WebEventsBundle,
  WebModelBundle,
} from '../types';

interface TabVisitorProps {
  lang: Lang;
  model: WebModelBundle;
  events: WebEventsBundle | null;
}

interface ScenarioPreset {
  id: string;
  badge: string;
  ko: string;
  en: string;
  subKo: string;
  subEn: string;
  season: SeasonKey;
  dayType: DayTypeKey;
  concertTier: ConcertTierKey;
  weather: WeatherKey;
  hour: number;
}

const PRESETS: ScenarioPreset[] = [
  {
    id: 'kspo_concert',
    badge: '🎤',
    ko: 'KSPO DOME 콘서트',
    en: 'KSPO DOME Concert',
    subKo: '가을 주말 · 15,000명 · 맑음',
    subEn: 'Autumn Wknd · 15k · Clear',
    season: 'autumn',
    dayType: 'weekend',
    concertTier: 'large_15k',
    weather: 'clear',
    hour: 15,
  },
  {
    id: 'rainy_mega',
    badge: '🌧️',
    ko: '우천 동시대관 피크',
    en: 'Rainy Multi-Venue Peak',
    subKo: '가을 주말 · 25,000명+ · 우천',
    subEn: 'Autumn Wknd · 25k+ · Rain',
    season: 'autumn',
    dayType: 'weekend',
    concertTier: 'mega_25k',
    weather: 'rain',
    hour: 15,
  },
  {
    id: 'autumn_picnic',
    badge: '🌿',
    ko: '가을 피크닉 주말',
    en: 'Autumn Picnic Weekend',
    subKo: '가을 주말 · 비공연 · 맑음',
    subEn: 'Autumn Wknd · No Show · Clear',
    season: 'autumn',
    dayType: 'weekend',
    concertTier: 'none',
    weather: 'clear',
    hour: 14,
  },
  {
    id: 'normal_weekday',
    badge: '📅',
    ko: '일반 평일 나들이',
    en: 'Standard Weekday',
    subKo: '봄 평일 · 비공연 · 맑음',
    subEn: 'Spring Wkdy · No Show · Clear',
    season: 'spring',
    dayType: 'weekday',
    concertTier: 'none',
    weather: 'clear',
    hour: 13,
  },
];

export const TabVisitor: React.FC<TabVisitorProps> = ({ lang, model, events }) => {
  const [activePreset, setActivePreset] = useState<string>('kspo_concert');
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  const [season, setSeason] = useState<SeasonKey>('autumn');
  const [dayType, setDayType] = useState<DayTypeKey>('weekend');
  const [concertTier, setConcertTier] = useState<ConcertTierKey>('large_15k');
  const [weather, setWeather] = useState<WeatherKey>('clear');
  const [hour, setHour] = useState<number>(15);

  const applyPreset = (p: ScenarioPreset) => {
    setActivePreset(p.id);
    setSeason(p.season);
    setDayType(p.dayType);
    setConcertTier(p.concertTier);
    setWeather(p.weather);
    setHour(p.hour);
  };

  const curveKey = `${season}|${dayType}|${concertTier}|${weather}`;
  const curve = model.prediction_grid.curves[curveKey] ?? Object.values(model.prediction_grid.curves)[0];

  const chartData = useMemo(
    () =>
      Array.from({ length: 24 }, (_, h) => ({
        hour: h,
        label: `${String(h).padStart(2, '0')}시`,
        parking: curve.parking[h],
        visitors: curve.visitors[h],
      })),
    [curve]
  );

  const curParking = curve.parking[hour] ?? 0;
  const curVisitors = curve.visitors[hour] ?? 0;
  const peakParking = Math.max(...curve.parking);
  const peakHour = curve.parking.indexOf(peakParking);

  const cutoffHour = useMemo(() => {
    const threshold = Math.min(2200, Math.max(1500, Math.round(peakParking * 0.78)));
    for (let h = 9; h <= 20; h++) {
      if (curve.parking[h] >= threshold) return Math.max(9, h - 1);
    }
    return null;
  }, [curve, peakParking]);

  const zoneStates = useMemo(
    () => computeZoneStates(curParking, model.zones_11_empirical),
    [curParking, model.zones_11_empirical]
  );
  const worstZones = useMemo(
    () => [...zoneStates].sort((a, b) => b.loadPct - a.loadPct).slice(0, 3),
    [zoneStates]
  );
  const bestZones = useMemo(
    () => [...zoneStates].sort((a, b) => a.loadPct - b.loadPct).slice(0, 3),
    [zoneStates]
  );

  const ko = lang === 'ko';

  return (
    <div className="space-y-5">
      {/* Differentiation Banner (Why this exists beyond generic map apps) */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-blue-500/25 bg-blue-950/20 px-4 py-2.5 text-xs text-blue-200">
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 shrink-0 text-blue-400" />
          <span>
            {ko ? (
              <>
                <strong className="text-white">범용 지도앱과의 차이:</strong> 과거 단순 요일 평균이 아닌, 공단 독점{' '}
                <strong className="text-blue-300">공연관람객수(0~26,398명) 조건부 AI 예측</strong>과{' '}
                <strong className="text-emerald-300">내부 11개 구역(P1A~P11) 분산 안내</strong>를 제공합니다.
              </>
            ) : (
              <>
                <strong className="text-white">Beyond Generic Map Apps:</strong> Event-conditioned AI using KSPO&amp;CO{' '}
                <strong className="text-blue-300">concert attendance (0–26,398 pax)</strong> +{' '}
                <strong className="text-emerald-300">11-zone (P1A–P11) micro-dispersion</strong>.
              </>
            )}
          </span>
        </div>
        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-slate-200 transition hover:border-blue-500 hover:text-white"
        >
          <SlidersHorizontal className="h-3.5 w-3.5 text-blue-400" />
          {ko ? '상세 조건 설정' : 'Custom Controls'}
          {showAdvanced ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Streamlined Scenario Presets + Time Slider */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          {/* 4 One-Click Scenario Chips */}
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 lg:col-span-7">
            {PRESETS.map((p) => {
              const selected = activePreset === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => applyPreset(p)}
                  className={`rounded-xl border px-3 py-2.5 text-left transition ${
                    selected
                      ? 'border-blue-500 bg-blue-600/20 text-white shadow-md shadow-blue-600/15'
                      : 'border-slate-800 bg-slate-950/70 text-slate-300 hover:border-slate-700 hover:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold">
                    <span>{p.badge}</span>
                    <span className="truncate">{ko ? p.ko : p.en}</span>
                  </div>
                  <div className="mt-1 truncate text-[10px] text-slate-400">
                    {ko ? p.subKo : p.subEn}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Time Slider */}
          <div className="flex flex-col justify-center rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-2.5 lg:col-span-5">
            <div className="mb-1.5 flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 font-medium text-slate-300">
                <Clock className="h-3.5 w-3.5 text-blue-400" />
                {ko ? '도착·관람 시각 (3D 기둥 실시간 연동)' : 'Target Time (Live 3D Sync)'}
              </span>
              <span className="rounded-md bg-blue-600/20 px-2 py-0.5 font-mono text-sm font-bold text-blue-300">
                {String(hour).padStart(2, '0')}:00
              </span>
            </div>
            <input
              type="range"
              min={6}
              max={23}
              value={hour}
              onChange={(e) => setHour(Number(e.target.value))}
              className="w-full accent-blue-500"
            />
            <div className="mt-1 flex justify-between text-[10px] text-slate-500">
              <span>06:00</span>
              <span>12:00</span>
              <span>15:00 ({ko ? '피크' : 'Peak'})</span>
              <span>19:00</span>
              <span>23:00</span>
            </div>
          </div>
        </div>

        {/* Collapsible Advanced Controls */}
        {showAdvanced && (
          <div className="mt-3.5 grid grid-cols-2 gap-3 border-t border-slate-800 pt-3.5 sm:grid-cols-4">
            <div>
              <label className="mb-1 block text-[11px] font-medium text-slate-400">
                {ko ? '계절' : 'Season'}
              </label>
              <select
                value={season}
                onChange={(e) => {
                  setActivePreset('custom');
                  setSeason(e.target.value as SeasonKey);
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="spring">{ko ? '봄 (5월 성수기)' : 'Spring (May Peak)'}</option>
                <option value="summer">{ko ? '여름 (7월)' : 'Summer (Jul)'}</option>
                <option value="autumn">{ko ? '가을 (10월 최성수기)' : 'Autumn (Oct Peak)'}</option>
                <option value="winter">{ko ? '겨울 (1월 비수기)' : 'Winter (Jan Low)'}</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-slate-400">
                {ko ? '요일 구분' : 'Day Type'}
              </label>
              <select
                value={dayType}
                onChange={(e) => {
                  setActivePreset('custom');
                  setDayType(e.target.value as DayTypeKey);
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="weekday">{ko ? '평일' : 'Weekday'}</option>
                <option value="weekend">{ko ? '주말 (토·일)' : 'Weekend'}</option>
                <option value="holiday">{ko ? '공휴일' : 'Public Holiday'}</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-slate-400">
                {ko ? '공연·대관 규모' : 'Concert Scale'}
              </label>
              <select
                value={concertTier}
                onChange={(e) => {
                  setActivePreset('custom');
                  setConcertTier(e.target.value as ConcertTierKey);
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="none">{ko ? '공연 없음 (일반 방문)' : 'No Concert'}</option>
                <option value="small_3k">{ko ? '소규모 (~3,000명 · 올림픽홀)' : 'Small (~3k · Hall)'}</option>
                <option value="medium_8k">{ko ? '중규모 (~8,000명 · 핸드볼)' : 'Medium (~8k · Arena)'}</option>
                <option value="large_15k">{ko ? '대형 (~15,000명 · KSPO DOME)' : 'Large (~15k · KSPO DOME)'}</option>
                <option value="mega_25k">{ko ? '메가 동시대관 (~25,000명+)' : 'Mega Multi-Venue (25k+)'}</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-slate-400">
                {ko ? '기상 조건' : 'Weather'}
              </label>
              <div className="flex gap-1.5">
                <button
                  onClick={() => {
                    setActivePreset('custom');
                    setWeather('clear');
                  }}
                  className={`flex flex-1 items-center justify-center gap-1 rounded-lg border px-2 py-2 text-xs font-medium transition ${
                    weather === 'clear'
                      ? 'border-blue-500 bg-blue-600/20 text-blue-300'
                      : 'border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sun className="h-3.5 w-3.5" /> {ko ? '맑음' : 'Clear'}
                </button>
                <button
                  onClick={() => {
                    setActivePreset('custom');
                    setWeather('rain');
                  }}
                  className={`flex flex-1 items-center justify-center gap-1 rounded-lg border px-2 py-2 text-xs font-medium transition ${
                    weather === 'rain'
                      ? 'border-sky-500 bg-sky-600/20 text-sky-300'
                      : 'border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <CloudRain className="h-3.5 w-3.5" /> {ko ? '우천' : 'Rain'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Actionable Advice KPI Cards */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{ko ? `${hour}시 AI 예측 주차대수` : `Predicted Parking (${hour}:00)`}</span>
            <Car className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-1.5 text-2xl font-bold text-white">
            {curParking.toLocaleString()}
            <span className="ml-1 text-xs font-normal text-slate-400">{ko ? '대' : 'cars'}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {ko ? `금일 피크: ${peakHour}시 (${peakParking.toLocaleString()}대)` : `Day Peak: ${peakHour}:00 (${peakParking.toLocaleString()})`}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{ko ? `${hour}시 AI 예측 방문객` : `Predicted Visitors (${hour}:00)`}</span>
            <Users className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-1.5 text-2xl font-bold text-white">
            {curVisitors.toLocaleString()}
            <span className="ml-1 text-xs font-normal text-slate-400">{ko ? '명' : 'pax'}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {ko ? 'RF+HGB 앙상블 (R²=0.767)' : 'RF+HGB Ensemble (R²=0.767)'}
          </div>
        </div>

        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/25 p-4">
          <div className="flex items-center justify-between text-xs text-emerald-300">
            <span>{ko ? '안전 주차 마감 & 추천 게이트' : 'Safe Arrival Cutoff & Gate'}</span>
            <Compass className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-1.5 text-xl font-bold text-emerald-200">
            {cutoffHour
              ? ko
                ? `${cutoffHour}:00 이전 도착 권장`
                : `Arrive before ${cutoffHour}:00`
              : ko
                ? '전 시간대 비교적 원활'
                : 'Smooth most of the day'}
          </div>
          <div className="mt-1 text-[11px] text-emerald-300/80">
            {ko
              ? `분산 추천: ${bestZones.map((z) => z.zone).join(' · ')} (서1문/남4문)`
              : `Best lots: ${bestZones.map((z) => z.zone).join(' · ')} (West 1 / South 4)`}
          </div>
        </div>

        <div className="rounded-2xl border border-rose-500/30 bg-rose-950/25 p-4">
          <div className="flex items-center justify-between text-xs text-rose-300">
            <span>{ko ? '만차 주의 병목 구역' : 'High Bottleneck Zones'}</span>
            <AlertTriangle className="h-4 w-4 text-rose-400" />
          </div>
          <div className="mt-1.5 text-xl font-bold text-rose-200">
            {worstZones.map((z) => z.zone).join(' · ')}
          </div>
          <div className="mt-1 text-[11px] text-rose-300/80">
            {ko
              ? `최고 부하 ${worstZones[0]?.loadPct}% · 동2문 진입 회피 권장`
              : `Max load ${worstZones[0]?.loadPct}% · Avoid East Gate 2`}
          </div>
        </div>
      </div>

      {/* Main Grid: 3D Map + 24h Prediction Curve & Subway Dispersion */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <ParkMap3D
            lang={lang}
            predictedTotalParking={curParking}
            zonesEmpirical={model.zones_11_empirical}
          />
        </div>

        <div className="flex flex-col justify-between gap-4 xl:col-span-5">
          {/* 24h Curve */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">
                {ko ? '24시간 공연 조건부 혼잡 예측 (주차대수)' : '24h Event-Conditioned Parking Forecast'}
              </h3>
              <span className="rounded bg-blue-500/15 px-2 py-0.5 text-[11px] text-blue-300">
                Ensemble RF+HGB
              </span>
            </div>
            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 5, right: 12, left: -12, bottom: 0 }}>
                  <defs>
                    <linearGradient id="parkFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={3} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '10px',
                      fontSize: '12px',
                    }}
                  />
                  <ReferenceLine x={`${String(hour).padStart(2, '0')}시`} stroke="#f43f5e" strokeWidth={2} />
                  <Area
                    type="monotone"
                    dataKey="parking"
                    name={ko ? '예측 주차대수' : 'Predicted Cars'}
                    stroke="#3b82f6"
                    strokeWidth={2.5}
                    fill="url(#parkFill)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 3-Subway Station Dispersion Guide */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <h3 className="mb-2.5 flex items-center gap-1.5 text-sm font-semibold text-white">
              <Train className="h-4 w-4 text-sky-400" />
              {ko ? '공연 종료 귀가 분산 — 3개 지하철역 비교' : 'Post-Concert Subway Dispersion (3 Stations)'}
            </h3>
            <div className="space-y-2">
              {SUBWAY_STATIONS.map((st, idx) => (
                <div
                  key={st.id}
                  className={`rounded-xl border p-2.5 text-xs ${
                    idx === 1
                      ? 'border-emerald-500/35 bg-emerald-950/20'
                      : 'border-slate-800 bg-slate-950/60'
                  }`}
                >
                  <div className="flex items-center justify-between font-semibold">
                    <span className="text-slate-100">
                      {ko ? st.nameKo : st.nameEn}{' '}
                      <span className="ml-1 rounded bg-sky-500/20 px-1.5 py-0.5 text-[10px] text-sky-300">
                        {st.lines}
                      </span>
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {ko ? `KSPO 도보 ${st.walkToKspoMin}분` : `${st.walkToKspoMin}m walk`}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {ko ? st.exitPeakAdviceKo : st.exitPeakAdviceEn}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Focused Bottom Row: 2026 Real Concerts One-Click Scenario Strip */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-white">
            {ko
              ? '2026 올림픽공원 실제 공연 원클릭 시뮬레이션 (영문 공연정보 15149169 실데이터)'
              : '2026 Olympic Park Real Concerts — One-Click Scenario (Dataset 15149169)'}
          </h3>
          <span className="text-[11px] text-slate-400">
            {ko ? '공연 클릭 시 해당 규모·주말 피크 시나리오 즉시 반영' : 'Click any concert to apply its expected crowd tier'}
          </span>
        </div>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {(events?.concerts_2026_en ?? []).slice(0, 6).map((c) => (
            <button
              key={c.id}
              onClick={() => {
                const isFest = c.title.toLowerCase().includes('festival');
                setActivePreset(isFest ? 'rainy_mega' : 'kspo_concert');
                setConcertTier(isFest ? 'mega_25k' : 'large_15k');
                setSeason('autumn');
                setDayType('weekend');
                setWeather('clear');
                setHour(17);
              }}
              className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-left transition hover:border-blue-500/50 hover:bg-slate-900"
            >
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-blue-600/15 font-mono text-[11px] font-bold text-blue-300">
                {c.date.slice(5)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-semibold text-slate-100">{c.title}</div>
                <div className="mt-0.5 text-[11px] text-slate-400">
                  {c.date} · {ko ? `글로벌 조회 ${c.views.toLocaleString()}` : `${c.views.toLocaleString()} views`}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

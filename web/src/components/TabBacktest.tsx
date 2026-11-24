import React, { useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Award, BarChart3, CheckCircle2 } from 'lucide-react';
import type { Lang, WebModelBundle } from '../types';

interface TabBacktestProps {
  lang: Lang;
  model: WebModelBundle;
}

const MODEL_LABELS: Record<string, string> = {
  Baseline_HourWeekend: 'Baseline (시간×주말 평균)',
  Ridge: 'Ridge Regression (선형)',
  RandomForest: 'RandomForest (260 Trees)',
  HistGradientBoosting: 'HistGradientBoosting',
  Ensemble_RF_HGB: 'Ensemble (RF + HGB) ★',
};

export const TabBacktest: React.FC<TabBacktestProps> = ({ lang, model }) => {
  const ko = lang === 'ko';
  const cases = model.backtest.sample_days;
  const [selectedCaseId, setSelectedCaseId] = useState<string>(cases[0]?.id ?? '');
  const activeCase = cases.find((c) => c.id === selectedCaseId) ?? cases[0];

  const cvPark = model.benchmarks.parking_count.cv_5fold_day_grouped;
  const ootPark = model.benchmarks.parking_count.oot_oct_dec;
  const cvVis = model.benchmarks.visitor_count.cv_5fold_day_grouped;
  const topFeatures = model.benchmarks.parking_count.feature_importance.slice(0, 8);

  return (
    <div className="space-y-5">
      {/* Summary Header */}
      <div className="rounded-2xl border border-blue-500/30 bg-blue-950/20 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="flex items-center gap-2 text-base font-bold text-white">
              <Award className="h-5 w-5 text-blue-400" />
              {ko
                ? '2025 실측 데이터 무누수(Zero-Leakage) AI 백테스트 검증실'
                : '2025 Real-Data Zero-Leakage AI Backtest Lab'}
            </h2>
            <p className="mt-1 text-xs text-slate-300">
              {ko
                ? `정제 ${model.dataset_stats.rows.toLocaleString()}시간 (${model.dataset_stats.unique_days}일 · 공연일 ${model.dataset_stats.concert_days}일) 대상 동일 날짜 분리 5-Fold Day-Grouped CV 및 10~12월 미래 OOT Holdout 검증 결과`
                : `Validated on ${model.dataset_stats.rows.toLocaleString()} clean hourly rows (${model.dataset_stats.unique_days} days, ${model.dataset_stats.concert_days} concert days) via Day-Grouped 5-Fold CV & Oct-Dec Out-of-Time Holdout`}
            </p>
          </div>
          <div className="flex gap-2 text-xs">
            <span className="rounded-lg bg-emerald-500/20 px-3 py-1.5 font-bold text-emerald-300">
              Parking MAE -29.0% (R² 0.729)
            </span>
            <span className="rounded-lg bg-indigo-500/20 px-3 py-1.5 font-bold text-indigo-300">
              Visitor R² 0.767
            </span>
          </div>
        </div>
      </div>

      {/* Benchmark Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <h3 className="mb-3 text-sm font-semibold text-white">
          {ko ? '모델별 정량 성능 비교 (주차대수 · 방문객)' : 'Model Performance Benchmark Table'}
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2 pr-3">{ko ? '모델' : 'Model'}</th>
                <th className="px-3 py-2 text-right">{ko ? '주차 CV MAE' : 'Park CV MAE'}</th>
                <th className="px-3 py-2 text-right">{ko ? '주차 CV RMSE' : 'Park CV RMSE'}</th>
                <th className="px-3 py-2 text-right">{ko ? '주차 CV R²' : 'Park CV R²'}</th>
                <th className="px-3 py-2 text-right">{ko ? '주차 OOT R² (10~12월)' : 'Park OOT R²'}</th>
                <th className="pl-3 py-2 text-right">{ko ? '방문객 CV R²' : 'Visitor CV R²'}</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(cvPark).map((mKey) => {
                const isBest = mKey === 'Ensemble_RF_HGB';
                const p = cvPark[mKey];
                const o = ootPark[mKey];
                const v = cvVis[mKey];
                return (
                  <tr
                    key={mKey}
                    className={`border-b border-slate-800/60 ${
                      isBest ? 'bg-blue-600/15 font-semibold text-white' : 'text-slate-300'
                    }`}
                  >
                    <td className="py-2.5 pr-3">
                      <span className="flex items-center gap-1.5">
                        {isBest && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
                        {MODEL_LABELS[mKey] ?? mKey}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">{p.mae.toFixed(1)}</td>
                    <td className="px-3 py-2.5 text-right font-mono">{p.rmse.toFixed(1)}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-blue-300">{p.r2.toFixed(4)}</td>
                    <td className="px-3 py-2.5 text-right font-mono">{o?.r2.toFixed(4)}</td>
                    <td className="pl-3 py-2.5 text-right font-mono text-indigo-300">{v?.r2.toFixed(4)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Actual vs Predicted Day Overlay + Feature Importance */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 lg:col-span-7">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-white">
              {ko ? '실제 2025년 일자별 실측 vs AI 예측 오버레이' : '2025 Actual vs Predicted Hourly Overlay'}
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {cases.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelectedCaseId(c.id)}
                  className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition ${
                    activeCase?.id === c.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          {activeCase && (
            <>
              <div className="mb-3 flex flex-wrap gap-3 rounded-xl bg-slate-950/70 px-3 py-2 text-[11px] text-slate-300">
                <span>📅 {activeCase.date}</span>
                <span>🎤 {activeCase.concert_name}</span>
                <span>👥 {activeCase.max_audience.toLocaleString()}{ko ? '명' : ' pax'}</span>
                <span>🌧️ {activeCase.total_precip_mm} mm</span>
                <span className="font-bold text-emerald-300">Day MAE: {activeCase.day_mae}</span>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={activeCase.series} margin={{ top: 5, right: 12, left: -8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="hour" tickFormatter={(h) => `${h}시`} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '10px', fontSize: '12px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                    <Line
                      type="monotone"
                      dataKey="actual_parking"
                      name={ko ? '실측 주차대수' : 'Actual Parking'}
                      stroke="#f8fafc"
                      strokeWidth={2.4}
                      dot={{ r: 2.5 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="pred_parking"
                      name={ko ? 'AI 앙상블 예측' : 'AI Ensemble Pred'}
                      stroke="#3b82f6"
                      strokeWidth={2.2}
                      strokeDasharray="5 4"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 lg:col-span-5">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-white">
            <BarChart3 className="h-4 w-4 text-blue-400" />
            {ko ? '변수 중요도 Top 8 (Permutation R²)' : 'Top 8 Feature Importances (Permutation R²)'}
          </h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[...topFeatures].reverse()} layout="vertical" margin={{ top: 4, right: 16, left: 20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis type="category" dataKey="feature" width={115} tick={{ fill: '#cbd5e1', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '10px', fontSize: '12px' }}
                />
                <Bar dataKey="importance_r2" name="R² Drop" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 11-Zone Spatial Congestion Asymmetry Bar Chart */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-white">
            {ko ? '11개 주차구역(P1A~P11) 만차·혼잡 공간 편중 실측 (15164156, 699건)' : '11-Zone Spatial Asymmetry (15164156 Real Data)'}
          </h3>
          <span className="text-xs text-rose-300">
            {ko ? 'P11(85.0%) vs P1A(58.5%) — 26.5%p 공간 편중 실증' : 'P11 (85.0%) vs P1A (58.5%) — 26.5%p gap'}
          </span>
        </div>
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={model.zones_11_empirical} margin={{ top: 5, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="zone" tick={{ fill: '#e2e8f0', fontSize: 11 }} />
              <YAxis unit="%" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '10px', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
              <Bar dataKey="full_rate_pct" name={ko ? '만차율 (%)' : 'Full (%)'} fill="#f43f5e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="busy_or_full_pct" name={ko ? '혼잡+만차율 (%)' : 'Busy+Full (%)'} fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { AlertCircle, CheckCircle, Database, Server, ShieldCheck } from 'lucide-react';
import type { Lang, WebModelBundle } from '../types';

interface TabOpsAuditProps {
  lang: Lang;
  model: WebModelBundle;
  liveParkingSum: number | null;
  liveSource: 'live' | 'snapshot';
}

const FUSED_DATASETS = [
  { org: '한국체육산업개발(주)', name: '올림픽공원 실시간 주차현황 (15168686)', type: 'OpenAPI (JSON)', role: '실시간 총 주차대수 라이브 관제' },
  { org: '한국체육산업개발(주)', name: '2025 차량입출차·공연·날씨 연계 (15164822)', type: 'OpenAPI (XML 복원)', role: '7,803건 시계열 ML 학습·백테스트 코어' },
  { org: '한국체육산업개발(주)', name: '주차장 혼잡도 정보 (15164156)', type: 'CSV (699건)', role: 'P1A~P11 11개 구역 공간 편중 모델링' },
  { org: '한국체육산업개발(주)', name: '올림픽공원 입출차 정보 (15138735)', type: 'CSV (215,528건)', role: '분 단위 체류시간(중앙값 74분)·야간 출차 CO₂ 베이스라인' },
  { org: '한국체육산업개발(주)', name: '월별주차현황 (15131671)', type: 'CSV (2023~2025)', role: '3개년 계절성 보정 및 DQ-02 이상치 교차 검증' },
  { org: '한국체육산업개발(주)', name: '영문/국문 공연·대관·잔디시설 (4종)', type: 'CSV + OpenAPI', role: '글로벌 팬 한/영 전환·공연 피처·개방 구역 반영' },
  { org: '외부 융합 (기상·교통·환경)', name: '송파구 실측 기상 + 5·8·9호선 + 환경부 CO₂ 계수', type: 'OpenAPI / 공표치', role: '우천 스트레스·지하철 분산·공회전 탄소 환산' },
];

const EXTRA_DQ_FINDING = {
  id: 'DQ-04',
  severity: 'MEDIUM' as const,
  title: '유실물 API(KSClost, 15038496) HTML 게시판 덤프 및 최신성 결여 → 의도적 탑재 배제',
  detail:
    '2,500건 실사 결과 개별 품목 DB가 아니라 HWP 메타태그가 혼입된 HTML 공고 덤프이자 2024년 경찰서 이관 완료 글이며, 공연장 내부 유실물은 기획사 관할이고 기존 공식 홈페이지·경찰청 LOST112와 중복됨. 품질 기준 미달 데이터는 무리하게 넣지 않고 서비스에서 배제한 뒤 정형 개방을 제언함.',
};

const NEW_DATA_PROPOSALS = [
  {
    no: '제언 1',
    title: 'API_CPM_009 JSON 직렬화 CDATA 누락 수정 및 8~9월·11~12월 결손 보정',
    impact: '행안부 공공데이터 품질인증 최우수 연속 방어 & 민간 개발자 즉시 JSON 활용 가능',
  },
  {
    no: '제언 2',
    title: '실시간 주차현황 API의 구역별(P1A~P11) 잔여면수 세분화 개방',
    impact: '현재 합계(parking_sum) 1개 값만 제공 → 11개 구역별 실시간 잔여면 개방 시 내비게이션 실시간 분산 가능',
  },
  {
    no: '제언 3',
    title: 'KOPIS/티켓 예매처 연계 공연장별·시간대별 예상 입장인원 익명 사전 개방',
    impact: '공연 D-7 시점 사전 혼잡 예보 정확도(R²) 0.73 → 0.85+ 도약 가능',
  },
  {
    no: '제언 4',
    title: '실감형 3D 공연장(15127487) 웹 표준 경량화(Draco GLB ≤5MB + PBR MetalRough + 좌석 블록 ID)',
    impact: '현재 53~75MB·3,878만 정점 CAD 원본은 웹 브라우저 크래시 유발 → 경량화 개방 시 모바일 3D 좌석 시야 생태계 즉시 개화',
  },
  {
    no: '제언 5',
    title: '유실물 API(KSClost) 정형 컬럼 분리(품목·습득구역·보관상태) 및 경찰청 LOST112 실시간 연계',
    impact: 'HTML 게시판 덤프 대신 정형 JSON 제공 시 중복 민원 해소 및 외국인·관람객 실시간 분실물 검색 생태계 연계 가능',
  },
];

export const TabOpsAudit: React.FC<TabOpsAuditProps> = ({ lang, model, liveParkingSum, liveSource }) => {
  const ko = lang === 'ko';
  const audit = model.data_quality_audit;
  const allFindings = audit.findings.some((f) => f.id === 'DQ-04')
    ? audit.findings
    : [...audit.findings, EXTRA_DQ_FINDING];

  return (
    <div className="space-y-5">
      {/* 2028 Zero-Cost Readiness Banner */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-emerald-500/35 bg-emerald-950/20 p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-300">
            <ShieldCheck className="h-4 w-4" />
            {ko ? '서약서 제6항: 2028년 무중단 운영' : '2028 Zero-Cost Sustainability'}
          </div>
          <div className="mt-2 text-xl font-bold text-white">{ko ? '월 유지비 ₩0 (서버리스)' : '₩0 / Month Serverless'}</div>
          <p className="mt-1 text-[11px] text-slate-300">
            {ko
              ? 'Cloudflare Pages 무료 정적 호스팅 + 58KB 클라이언트 추론 번들 + API 장애 시 자동 스냅샷 Fallback'
              : 'Cloudflare Pages Free + 58KB client-side ML bundle + automatic snapshot fallback'}
          </p>
        </div>

        <div className="rounded-2xl border border-blue-500/35 bg-blue-950/20 p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-blue-300">
            <Server className="h-4 w-4" />
            {ko ? '실시간 주차 API 연동 상태' : 'Live Parking API Status'}
          </div>
          <div className="mt-2 flex items-baseline gap-2 text-xl font-bold text-white">
            {liveParkingSum !== null ? `${liveParkingSum.toLocaleString()}대` : 'N/A'}
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                liveSource === 'live'
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : 'bg-amber-500/20 text-amber-300'
              }`}
            >
              {liveSource === 'live' ? 'LIVE API' : 'SNAPSHOT FALLBACK'}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-300">
            ksponco.or.kr/online/main/parkingorsApi.do (60s Edge Cache)
          </p>
        </div>

        <div className="rounded-2xl border border-amber-500/35 bg-amber-950/20 p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-amber-300">
            <AlertCircle className="h-4 w-4" />
            {ko ? '원천 데이터 품질 감사 (DQ Gate)' : 'Upstream Data Quality Audit'}
          </div>
          <div className="mt-2 text-xl font-bold text-white">
            {ko ? `${allFindings.length}건 적발 · 검증 반영` : `${allFindings.length} Issues Audited`}
          </div>
          <p className="mt-1 text-[11px] text-slate-300">
            {ko
              ? `원본 ${audit.raw_rows_loaded.toLocaleString()}행 → 이상치 ${audit.anomalous_rows_excluded.toLocaleString()}행 격리 → 정제 ${audit.clean_rows_used.toLocaleString()}행`
              : `Raw ${audit.raw_rows_loaded.toLocaleString()} -> Quarantined ${audit.anomalous_rows_excluded.toLocaleString()} -> Clean ${audit.clean_rows_used.toLocaleString()}`}
          </p>
        </div>
      </div>

      {/* Data Quality Findings */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
          <AlertCircle className="h-4 w-4 text-amber-400" />
          {ko ? '실데이터 전수 감사에서 발견한 원천 품질 이슈 (DQ-01 ~ DQ-04)' : 'Empirical Upstream Data Quality Audit Findings (DQ-01 ~ DQ-04)'}
        </h3>
        <div className="space-y-3">
          {allFindings.map((f) => (
            <div key={f.id} className="rounded-xl border border-slate-800 bg-slate-950/70 p-3.5">
              <div className="flex items-center gap-2">
                <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] font-bold text-slate-200">
                  {f.id}
                </span>
                <span
                  className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                    f.severity === 'HIGH'
                      ? 'bg-rose-500/20 text-rose-300'
                      : 'bg-amber-500/20 text-amber-300'
                  }`}
                >
                  {f.severity}
                </span>
                <span className="text-xs font-semibold text-white">{f.title}</span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{f.detail}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Fused Datasets Table + New Open Data Proposals */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 lg:col-span-7">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <Database className="h-4 w-4 text-blue-400" />
            {ko ? '융합 활용 공공데이터 명세 (내부 9종 + 외부 3종)' : 'Fused Public Dataset Specification'}
          </h3>
          <div className="space-y-2 text-xs">
            {FUSED_DATASETS.map((d, i) => (
              <div key={i} className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <span className="font-semibold text-slate-100">{d.name}</span>
                  <span className="rounded bg-blue-500/15 px-2 py-0.5 text-[10px] text-blue-300">
                    {d.type}
                  </span>
                </div>
                <div className="mt-1 text-[11px] text-slate-400">
                  {d.org} · {d.role}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 lg:col-span-5">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            {ko ? '향후 추가 개방·품질개선 실무 제언 (기획서 5번 환류)' : 'Actionable New Open-Data Proposals for KSPO&CO'}
          </h3>
          <div className="space-y-2.5 text-xs">
            {NEW_DATA_PROPOSALS.map((p) => (
              <div key={p.no} className="rounded-xl border border-emerald-500/20 bg-emerald-950/15 p-3">
                <div className="font-semibold text-emerald-200">
                  [{p.no}] {p.title}
                </div>
                <p className="mt-1 text-[11px] text-slate-300">{p.impact}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Real-world Olympic Park (Songpa-gu, Seoul) geospatial layout for 3D MapLibre Twin
export interface VenueMeta {
  id: string;
  nameKo: string;
  nameEn: string;
  capacity: number;
  heightM: number;
  center: [number, number]; // [lng, lat]
  radiusLng: number;
  radiusLat: number;
  nearestGate: string;
  color: string;
}

export interface ParkingZoneMeta {
  zone: string;
  gateKo: string;
  gateEn: string;
  areaKo: string;
  areaEn: string;
  center: [number, number];
  sizeLng: number;
  sizeLat: number;
  capacityEst: number;
  walkToKspoMin: number;
  isOverflowTarget: boolean;
}

export interface SubwayMeta {
  id: string;
  nameKo: string;
  nameEn: string;
  lines: string;
  center: [number, number];
  walkToKspoMin: number;
  exitPeakAdviceKo: string;
  exitPeakAdviceEn: string;
}

export const OLYMPIC_PARK_VENUES: VenueMeta[] = [
  {
    id: 'kspo_dome',
    nameKo: 'KSPO DOME (체조경기장)',
    nameEn: 'KSPO DOME',
    capacity: 15000,
    heightM: 38,
    center: [127.1273, 37.5193],
    radiusLng: 0.00095,
    radiusLat: 0.00072,
    nearestGate: '동2문 (P5·P6)',
    color: '#3b82f6',
  },
  {
    id: 'handball',
    nameKo: '티켓링크 라이브 아레나 (핸드볼)',
    nameEn: 'SK Handball Arena',
    capacity: 5000,
    heightM: 28,
    center: [127.1267, 37.5169],
    radiusLng: 0.00068,
    radiusLat: 0.00052,
    nearestGate: '동2문 (P6·P8)',
    color: '#6366f1',
  },
  {
    id: 'olympic_hall',
    nameKo: '올림픽홀',
    nameEn: 'Olympic Hall',
    capacity: 3000,
    heightM: 22,
    center: [127.1277, 37.5152],
    radiusLng: 0.00052,
    radiusLat: 0.00042,
    nearestGate: '남2문 (P8·P9)',
    color: '#8b5cf6',
  },
  {
    id: 'woori_art',
    nameKo: '우리금융아트홀',
    nameEn: 'Woori Art Hall',
    capacity: 1184,
    heightM: 20,
    center: [127.1251, 37.5218],
    radiusLng: 0.00045,
    radiusLat: 0.00038,
    nearestGate: '북2문 (P4·P5)',
    color: '#0ea5e9',
  },
  {
    id: 'lawn_88',
    nameKo: '88잔디마당 (야외 페스티벌)',
    nameEn: '88 Lawn Plaza',
    capacity: 10000,
    heightM: 6,
    center: [127.1232, 37.5196],
    radiusLng: 0.00105,
    radiusLat: 0.00078,
    nearestGate: '남2문 / 북2문',
    color: '#10b981',
  },
  {
    id: 'peace_plaza',
    nameKo: '평화의광장',
    nameEn: 'Peace Plaza',
    capacity: 6000,
    heightM: 8,
    center: [127.1157, 37.5180],
    radiusLng: 0.00085,
    radiusLat: 0.00055,
    nearestGate: '서1문 (P1A·P1B)',
    color: '#14b8a6',
  },
];

// All 11 real parking zones recorded in 15164156_parking_congestion.csv
export const PARKING_ZONES: ParkingZoneMeta[] = [
  { zone: 'P1A', gateKo: '서1문·평화의광장', gateEn: 'West Gate 1 (Peace)', areaKo: '평화의광장 북측', areaEn: 'Peace Plaza North', center: [127.1152, 37.5193], sizeLng: 0.00045, sizeLat: 0.00032, capacityEst: 420, walkToKspoMin: 14, isOverflowTarget: true },
  { zone: 'P1B', gateKo: '서1문·평화의광장', gateEn: 'West Gate 1 (Peace)', areaKo: '평화의광장 남측', areaEn: 'Peace Plaza South', center: [127.1165, 37.5166], sizeLng: 0.00045, sizeLat: 0.00032, capacityEst: 380, walkToKspoMin: 13, isOverflowTarget: true },
  { zone: 'P2', gateKo: '남4문·소마미술관', gateEn: 'South Gate 4 (SOMA)', areaKo: '소마미술관 인접', areaEn: 'Near SOMA Museum', center: [127.1188, 37.5153], sizeLng: 0.00044, sizeLat: 0.00030, capacityEst: 340, walkToKspoMin: 11, isOverflowTarget: true },
  { zone: 'P4', gateKo: '북2문·체조북측', gateEn: 'North Gate 2', areaKo: '우리금융아트홀 북측', areaEn: 'North of Woori Hall', center: [127.1243, 37.5236], sizeLng: 0.00042, sizeLat: 0.00030, capacityEst: 280, walkToKspoMin: 6, isOverflowTarget: false },
  { zone: 'P5', gateKo: '동2문·KSPO DOME', gateEn: 'East Gate 2 (Dome)', areaKo: 'KSPO DOME 북동측', areaEn: 'KSPO DOME NE', center: [127.1292, 37.5208], sizeLng: 0.00042, sizeLat: 0.00032, capacityEst: 310, walkToKspoMin: 3, isOverflowTarget: false },
  { zone: 'P6', gateKo: '동2문·핸드볼', gateEn: 'East Gate 2 (Arena)', areaKo: '체조·핸드볼 사이', areaEn: 'Between Dome & Arena', center: [127.1294, 37.5180], sizeLng: 0.00042, sizeLat: 0.00032, capacityEst: 320, walkToKspoMin: 3, isOverflowTarget: false },
  { zone: 'P7', gateKo: '북2문·올림픽수영장', gateEn: 'North Gate 2 (Pool)', areaKo: '올림픽수영장 인접', areaEn: 'Olympic Pool Lot', center: [127.1266, 37.5227], sizeLng: 0.00040, sizeLat: 0.00028, capacityEst: 260, walkToKspoMin: 5, isOverflowTarget: false },
  { zone: 'P8', gateKo: '남2문·올림픽홀', gateEn: 'South Gate 2 (Hall)', areaKo: '올림픽홀 인접', areaEn: 'Olympic Hall Lot', center: [127.1286, 37.5150], sizeLng: 0.00042, sizeLat: 0.00030, capacityEst: 300, walkToKspoMin: 6, isOverflowTarget: false },
  { zone: 'P9', gateKo: '남2문·장미광장', gateEn: 'South Gate 2 (Rose)', areaKo: '장미광장 남측', areaEn: 'Rose Plaza South', center: [127.1255, 37.5144], sizeLng: 0.00040, sizeLat: 0.00028, capacityEst: 240, walkToKspoMin: 8, isOverflowTarget: false },
  { zone: 'P10', gateKo: '남2문·테니스장', gateEn: 'South Gate 2 (Tennis)', areaKo: '테니스경기장 인접', areaEn: 'Tennis Court Lot', center: [127.1230, 37.5149], sizeLng: 0.00040, sizeLat: 0.00028, capacityEst: 220, walkToKspoMin: 9, isOverflowTarget: false },
  { zone: 'P11', gateKo: '동2문·지하/중앙', gateEn: 'East Gate 2 (Core)', areaKo: 'KSPO DOME 최인접', areaEn: 'KSPO DOME Core Lot', center: [127.1254, 37.5184], sizeLng: 0.00042, sizeLat: 0.00030, capacityEst: 260, walkToKspoMin: 2, isOverflowTarget: false },
];

export const SUBWAY_STATIONS: SubwayMeta[] = [
  {
    id: 'olympic_park_st',
    nameKo: '올림픽공원역',
    nameEn: 'Olympic Park Stn.',
    lines: '5·9호선',
    center: [127.1310, 37.5166],
    walkToKspoMin: 7,
    exitPeakAdviceKo: '공연 종료 직후 3번 출구 병목 심함 → 9호선 급행 대기 15~25분',
    exitPeakAdviceEn: 'Severe bottleneck at Exit 3 right after shows (15-25 min wait)',
  },
  {
    id: 'hanseong_baekje_st',
    nameKo: '한성백제역',
    nameEn: 'Hanseong Baekje Stn.',
    lines: '9호선',
    center: [127.1162, 37.5161],
    walkToKspoMin: 16,
    exitPeakAdviceKo: '평화의광장 경유 도보 분산 시 9호선 착석 탑승 확률 높음 (강력 추천)',
    exitPeakAdviceEn: 'Best dispersion route via Peace Plaza — much easier Line 9 boarding',
  },
  {
    id: 'mongchontoseong_st',
    nameKo: '몽촌토성역',
    nameEn: 'Mongchontoseong Stn.',
    lines: '8호선',
    center: [127.1124, 37.5174],
    walkToKspoMin: 18,
    exitPeakAdviceKo: '잠실·강남·성남 방면 8호선 환승 분산 최적 (주차 P1A/P1B 연계)',
    exitPeakAdviceEn: 'Optimal Line 8 dispersion toward Jamsil/Seongnam',
  },
];

export function makeRectPolygon(center: [number, number], halfLng: number, halfLat: number): number[][][] {
  const [x, y] = center;
  return [
    [
      [x - halfLng, y - halfLat],
      [x + halfLng, y - halfLat],
      [x + halfLng, y + halfLat],
      [x - halfLng, y + halfLat],
      [x - halfLng, y - halfLat],
    ],
  ];
}

export function makeCirclePolygon(center: [number, number], rLng: number, rLat: number, sides = 24): number[][][] {
  const [cx, cy] = center;
  const ring: number[][] = [];
  for (let i = 0; i <= sides; i++) {
    const a = (i / sides) * Math.PI * 2;
    ring.push([cx + Math.cos(a) * rLng, cy + Math.sin(a) * rLat]);
  }
  return [ring];
}
